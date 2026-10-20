#!/usr/bin/env python3
"""Headless-Chromium test for the website microphone (jarvis/app/src/webmic.js), repair #74 (Oct 20).

    python3 jarvis/app/scripts/webmic_browser_test.py            (needs Python playwright + its Chromium)

Serves jarvis/app over http://127.0.0.1 (AudioWorklet needs a secure context; localhost is one), opens
scripts/webmic_harness.html, whose getUserMedia returns a stream from an AudioContext the harness controls (room noise, plus a
speech-like burst it starts the very instant arm() is called: he talks the instant the orb says "listening", or earlier).
Checks: the WAV holds the burst from its first millisecond (within 30 ms), the turn ends about 1 s after he stops, nothing of
"Ananta's voice" played while disarmed gets in, no getUserMedia per turn, the ScriptProcessor fallback, and prints arm -> live
for webmic against the old per-turn path (getUserMedia + MediaRecorder, as expo-audio 57.0.5 did on the web).
"""
from __future__ import annotations

import functools
import http.server
import json
import os
import socketserver
import sys
import threading
from pathlib import Path

APP = Path(__file__).resolve().parents[1]
if not os.environ.get("PLAYWRIGHT_BROWSERS_PATH") and Path("/opt/pw-browsers").is_dir():
    os.environ["PLAYWRIGHT_BROWSERS_PATH"] = "/opt/pw-browsers"

from playwright.sync_api import sync_playwright  # noqa: E402


class _Quiet(http.server.SimpleHTTPRequestHandler):
    def log_message(self, *a):  # noqa: D401 - keep the output readable
        pass

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()


def _serve() -> socketserver.TCPServer:
    httpd = socketserver.ThreadingTCPServer(("127.0.0.1", 0), functools.partial(_Quiet, directory=str(APP)))
    httpd.daemon_threads = True
    threading.Thread(target=httpd.serve_forever, daemon=True).start()
    return httpd


def main() -> int:
    httpd = _serve()
    url = f"http://127.0.0.1:{httpd.server_address[1]}/scripts/webmic_harness.html"
    with sync_playwright() as p:
        browser = p.chromium.launch(headless=True, args=[
            "--use-fake-ui-for-media-stream", "--use-fake-device-for-media-stream", "--autoplay-policy=no-user-gesture-required"])
        ctx = browser.new_context(permissions=["microphone"])
        page = ctx.new_page()
        errors: list[str] = []
        page.on("pageerror", lambda e: errors.append(str(e)))
        page.on("console", lambda m: errors.append(m.text) if m.type == "error" else None)
        page.set_default_timeout(180_000)
        page.goto(url)
        page.wait_for_function("window.harnessReady === true")
        res = page.evaluate("runAll()")
        browser.close()
    httpd.shutdown()

    w, old = res["webmic"], res["old"]
    fails: list[str] = []

    def check(ok: bool, what: str):
        print(("  ok   " if ok else "  FAIL ") + what)
        if not ok:
            fails.append(what)

    print("webmic in headless Chromium:")
    check(bool(w.get("opened")), f"session opened in {w.get('openMs')} ms (capture: {w.get('capture')}, {w.get('rate')} Hz)")
    if not w.get("opened"):
        print(json.dumps(res, indent=1))
        return 1
    check(w["capture"] == "worklet", "AudioWorklet capture in Chromium")
    for key, label in (("turn1_first_speakAtArm", "turn 1 (room being learned), he talks the instant arm() is called"),
                       ("turn2_speakAtArm", "turn 2 (room kept), he talks the instant arm() is called"),
                       ("turn3_speakAtLive", "turn 3, he talks the instant the orb says listening")):
        t = w[key]
        b = t["burst"]
        check(t["ok"] and t["reason"] == "silence", f"{label}: ended by 1 s of quiet ({t['reason']})")
        # at arm(): the WAV starts where he does; at "listening": he starts after the WAV does (arm -> live + the fake mic's own delay)
        check((b["startMs"] <= 30 or key == "turn3_speakAtLive") and t["clipMs"] <= 30,
              f"  his first word is in the WAV: burst at {b['startMs']} ms, {b['durMs']} of 1500 ms kept (clipped {t['clipMs']} ms)")
        check(950 <= t["tailMs"] <= 1250, f"  turn ended {t['tailMs']} ms after he stopped (about 1 s)")
        check(t["wav"] == {"rate": 16000, "channels": 1, "bits": 16}, f"  16 kHz mono 16-bit WAV, {t['bytes']} bytes")
    check(w["turn2_speakAtArm"]["onsetMs"] == 0, f"turn 2: speech found at {w['turn2_speakAtArm']['onsetMs']} ms (no 400 ms of re-learning the room)")
    t4 = w["turn4_speakLater"]
    check(t4["prerollMs"] == 400 and 370 <= t4["burst"]["startMs"] <= 530,
          f"turn 4 (he talks 1.2 s later): pre-roll {t4['prerollMs']} ms, his first word at {t4['burst']['startMs']} ms in the WAV")
    t5a = w["turn5a_tailOnly"]
    check(t5a["ok"] and not t5a["heardSpeech"] and t5a["endReason"] is None,
          f"turn 5a (armed during the last 180 ms of 'Ananta's voice', he says nothing): its tail is not taken for speech "
          f"({t5a['tailInWavMs']} ms of tail captured, no turn)")
    t5 = w["turn5b_afterAnanta"]
    tail5 = t5["soundInFirst200Ms"]
    his5 = t5["burstAfter200"]["durMs"]
    check(t5["ok"] and t5["reason"] == "silence" and abs(his5 - 1500) <= 30 and tail5 <= 60,
          f"turn 5b (armed the moment 'Ananta' stopped, he talks 250 ms later): all of him kept ({his5} of 1500 ms); "
          f"{tail5} ms of Ananta's tail at the start of the WAV (the fake mic's own transport delay; nothing from before arm)")
    check(w["getUserMediaCallsPerTurn"] == 0, f"no getUserMedia per turn ({w['getUserMediaCallsTotal']} call in total, at open)")
    check(w["armToLiveMedian"] is not None and w["armToLiveMedian"] < 60, f"arm -> live (patched mic): median {w['armToLiveMedian']} ms {w['armToLiveMs']}")
    fb = w["fallback"]
    check(fb.get("capture") == "scriptprocessor" and fb.get("clipMs", 99) <= 30 and fb["second"]["clipMs"] <= 30,
          f"ScriptProcessor fallback: clipped {fb.get('clipMs')} / {fb['second'].get('clipMs')} ms, arm -> live {fb.get('armToLiveMs')} ms")
    check(not errors, "no page errors" + (f": {errors[:3]}" if errors else ""))

    print("\narm -> live (sound really being captured), median of each run:")
    print(f"  old path (permission getUserMedia + getUserMedia + enumerateDevices + analyser + new MediaRecorder, per turn):")
    print(f"    patched mic          {old['patchedMicLiveMedian']:>7} ms   {old['patchedMicLiveMs']}")
    print(f"    Chromium's own mic   {old['chromiumMicLiveMedian']:>7} ms   {old['chromiumMicLiveMs']}")
    print(f"  webmic (one stream per conversation, arm only):")
    print(f"    patched mic          {w['armToLiveMedian']:>7} ms   {w['armToLiveMs']}")
    print(f"    Chromium's own mic   {w['chromiumMicArmToLiveMedian']:>7} ms   {w['chromiumMicArmToLiveMs']}   (open once: {w['chromiumMicOpenMs']} ms)")
    print("\nfirst word lost when he talks the instant the orb says listening:")
    for key, label in (("clip", "this machine's getUserMedia"), ("clipSlowGum", "an assumed iPhone-like 300 ms per getUserMedia")):
        oc = old.get(key, {})
        if "burst" in oc:
            print(f"  old path, {label}: {oc['clipMs']} ms of 1500 lost (recorder live after {oc['liveMs']} ms, {oc['mime']})")
        else:
            print(f"  old path, {label}: could not decode the recording ({oc.get('error')})")
    sg = w["slowGum"]
    print(f"  webmic, this machine: {w['turn3_speakAtLive']['clipMs']} ms lost (and {w['turn2_speakAtArm']['clipMs']} ms when he talks "
          f"even before the mic is live, at arm())")
    print(f"  webmic, 300 ms per getUserMedia: paid once at open ({sg['openMs']} ms); turns: arm -> live "
          f"{sg['turn1']['armToLiveMs']} / {sg['turn2']['armToLiveMs']} ms, lost {sg['turn1']['clipMs']} / {sg['turn2']['clipMs']} ms")
    check(sg["turn1"]["clipMs"] <= 30 and sg["turn2"]["clipMs"] <= 30 and (sg["turn2"]["armToLiveMs"] or 999) < 60,
          "with a slow getUserMedia, webmic turns still start at once and lose nothing")
    if res.get("notes"):
        print("notes:", res["notes"])
    print(f"\nwebmic browser test: {'FAILED ' + str(len(fails)) if fails else 'all checks passed'}")
    return 1 if fails else 0


if __name__ == "__main__":
    sys.exit(main())
