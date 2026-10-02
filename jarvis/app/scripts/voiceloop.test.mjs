// Plain-Node tests for the voice loop:  node --experimental-strip-types scripts/voiceloop.test.mjs
import assert from "node:assert/strict";
import { VoiceLoop, LIMITS } from "../src/voiceloop.ts";

const tick = () => new Promise((r) => setImmediate(r));
const flush = async (n = 20) => { for (let i = 0; i < n; i++) await tick(); };

function rig(opts = {}) {
  const log = [];
  let clock = 0;
  const st = { recording: false, hearing: false, speaking: false, startCalls: 0, failStarts: opts.failStarts ?? 0 };
  let answer = null, speakDone = null;
  const fx = {
    micStart: async (force) => { st.startCalls++; await tick(); if (st.failStarts > 0) { st.failStarts--; return false; } st.recording = true; log.push(`mic:start${force ? "!" : ""}`); return true; },
    micStop: async () => { st.recording = false; log.push("mic:stop"); },
    micSend: () => { log.push("mic:send"); },
    micBusy: () => st.recording,
    micHearing: () => st.hearing,
    ask: (b64) => new Promise((res) => { log.push(`ask:${b64}`); answer = res; }),
    respond: (r, current) => new Promise((res) => { st.speaking = true; log.push(`speak:${r.answer ?? r.error}`); speakDone = () => { st.speaking = false; res(); }; }),
    stopSpeaking: () => { log.push("voice:stop"); if (speakDone) { const d = speakDone; speakDone = null; d(); } },
    onPhase: (p) => log.push(`phase:${p}`),
    onNote: (m) => log.push(`note:${m}`),
    now: () => clock,
    sleep: async () => { await tick(); },
  };
  const loop = new VoiceLoop(fx);
  return { loop, log, st, adv: (ms) => { clock += ms; }, answer: (r) => answer(r), finishSpeaking: () => speakDone && speakDone() };
}

// 1. Extra taps on the wave button do nothing; it listens once.
{
  const t = rig(); t.loop.start(); t.loop.start(); t.loop.start(); await flush();
  assert.equal(t.loop.phase, "listening"); assert.equal(t.st.startCalls, 1);
}

// 2. Normal turn: listening -> thinking -> speaking -> listening again.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const p = t.loop.onAudio("q1"); await flush();
  assert.equal(t.loop.phase, "thinking");
  t.answer({ heard: "how is btc", answer: "BTC is up." }); await flush();
  assert.equal(t.loop.phase, "speaking");
  t.finishSpeaking(); await p; await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(t.st.recording, "mic restarted after speaking");
}

// 3. Tap while speaking: stops the voice and listens right away (the old dead end).
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const p = t.loop.onAudio("q1"); await flush();
  t.answer({ heard: "x", answer: "Long answer." }); await flush();
  assert.equal(t.loop.phase, "speaking");
  t.loop.tap(); t.loop.tap(); t.loop.tap(); await p; await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(t.st.recording);
  assert.ok(t.log.includes("voice:stop"));
}

// 4. Tap while thinking: the late answer is NOT spoken; it is listening.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const p = t.loop.onAudio("q1"); await flush();
  t.loop.tap(); await flush();
  assert.equal(t.loop.phase, "listening");
  t.answer({ heard: "x", answer: "Late answer." }); await p; await flush();
  assert.ok(!t.log.some((l) => l.startsWith("speak:")), "late answer must not be spoken");
  assert.equal(t.loop.phase, "listening");
}

// 5. End while thinking: the answer arrives later and nothing happens; extra taps on the orb are harmless.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const p = t.loop.onAudio("q1"); await flush();
  t.loop.end(); t.loop.tap(); t.loop.tap();
  t.answer({ heard: "x", answer: "Too late." }); await p; await flush();
  assert.equal(t.loop.phase, "off"); assert.ok(!t.log.some((l) => l.startsWith("speak:")));
  assert.ok(!t.st.recording);
}

// 6. Audio arriving after voice was ended is dropped.
{
  const t = rig(); t.loop.start(); await flush(); t.loop.end();
  await t.loop.onAudio("stray"); await flush();
  assert.ok(!t.log.includes("ask:stray"));
}

// 7. Tap while he is talking sends what was said; tap while quiet restarts the mic.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.hearing = true; t.loop.tap(); assert.ok(t.log.includes("mic:send"));
  t.st.hearing = false; const before = t.st.startCalls; t.loop.tap(); await flush();
  assert.equal(t.st.startCalls, before + 1); assert.ok(t.log.includes("mic:start!"));
}

// 8. Mic fails to start twice: it retries and gets there.
{
  const t = rig({ failStarts: 2 }); t.loop.start(); await flush(40);
  assert.equal(t.loop.phase, "listening"); assert.ok(t.st.recording); assert.equal(t.st.startCalls, 3);
}

// 9. Watchdog: a mic that silently stopped recording is restarted after ~2.5 s.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false;
  t.loop.tick(); t.adv(1000); t.loop.tick(); t.adv(1600); t.loop.tick(); await flush();
  assert.ok(t.st.recording, "watchdog restarted the mic");
}

// 10. Watchdog: a question that never comes back is dropped after the limit; then it listens.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const p = t.loop.onAudio("q1"); await flush();
  t.adv(LIMITS.thinkingMs + 1); t.loop.tick(); await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(t.log.some((l) => l.startsWith("note:That took too long")));
  t.answer({ answer: "very late" }); await p; await flush();
  assert.ok(!t.log.some((l) => l.startsWith("speak:")));
}

// 11. Nothing was said (empty transcript): straight back to listening, nothing spoken.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const p = t.loop.onAudio("q1"); await flush();
  t.answer({ heard: "" }); await p; await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(!t.log.some((l) => l.startsWith("speak:")));
}

// 12. A voice sample while live: pauses listening, plays, resumes listening.
{
  const t = rig(); t.loop.start(); await flush();
  let played = false;
  await t.loop.aside(async () => { assert.ok(!t.st.recording, "mic paused during the sample"); played = true; }); await flush();
  assert.ok(played); assert.equal(t.loop.phase, "listening"); assert.ok(t.st.recording);
}

// 13. Errors are spoken (so he knows), then it listens again.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const p = t.loop.onAudio("q1"); await flush();
  t.answer({ error: "network down" }); await flush();
  assert.equal(t.loop.phase, "speaking"); t.finishSpeaking(); await p; await flush();
  assert.equal(t.loop.phase, "listening");
}

// 14. Back from the background while listening: the mic is restarted; while speaking: nothing changes.
{
  const t = rig(); t.loop.start(); await flush();
  t.st.recording = false; const before = t.st.startCalls; t.loop.resume(); await flush();
  assert.equal(t.st.startCalls, before + 1); assert.ok(t.st.recording);
  t.st.recording = false; const p = t.loop.onAudio("q"); await flush(); t.answer({ answer: "Hi." }); await flush();
  const n = t.st.startCalls; t.loop.resume(); await flush();
  assert.equal(t.st.startCalls, n, "no mic restart while speaking"); t.finishSpeaking(); await p;
}

// 15. Rapid mixed taps never leave it stuck: after any sequence it ends up listening with the mic on.
{
  const t = rig(); t.loop.start(); await flush();
  for (let k = 0; k < 5; k++) {
    t.st.recording = false; const p = t.loop.onAudio("q" + k); await flush(2);
    t.loop.tap(); t.loop.tap();
    t.answer({ answer: "A" + k }); await flush(2); t.loop.tap(); await p; await flush();
  }
  assert.equal(t.loop.phase, "listening"); assert.ok(t.st.recording);
  assert.ok(!t.log.some((l) => l.startsWith("speak:")), "answers to cancelled questions are never spoken");
}

console.log("voice loop: all 15 checks passed");
