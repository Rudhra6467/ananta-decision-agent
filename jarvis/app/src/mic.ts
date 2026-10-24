// Microphone with automatic end-of-speech detection that adapts to the room.
// It first listens ~0.4 s to learn the background level, then treats "clearly louder than the room" as speech. The turn ends
// after ~1 s of quiet, where quiet is measured against YOUR voice, not only the room (Madhav, Oct 11: it kept "hearing" for long
// after he finished when the room got louder): well below the loudest part of what you said, or a steady hum with none of
// speech's ups and downs. Hard limit 20 s per turn. Used by dictation and by voice mode.
//
// Every start / stop runs one after another (a small queue), so quick taps or overlapping restarts can never
// tangle the recorder. start() is safe to call while it is already listening.
//
// Voice mode is one conversation (Madhav, repair #74, Oct 20: his first word was lost when he talked as soon as the orb said
// "listening"): open() once when voice starts (the permission is asked once, not every turn), close() when it ends.
//  - Website: src/webmic.js keeps ONE microphone stream open for the whole conversation; each turn only arms it (instant),
//    the room level is learned on the first turn only, and the audio starts 400 ms before he starts talking.
//  - iPhone app: expo-audio as before, but the permission is asked once per conversation and the learned room level is kept
//    (no 400 ms re-learning at the start of every turn after the first).
import { useEffect, useRef, useState } from "react";
import { Platform } from "react-native";
import {
  AudioQuality, IOSOutputFormat, RecordingPresets, requestRecordingPermissionsAsync, setAudioModeAsync,
  useAudioRecorder, useAudioRecorderState,
} from "expo-audio";
import { createWebMic, webMicSupported } from "./webmic";

const WAV = {
  ...RecordingPresets.HIGH_QUALITY,
  extension: ".wav", sampleRate: 16000, numberOfChannels: 1, bitRate: 256000, isMeteringEnabled: true,
  ios: { extension: ".wav", outputFormat: IOSOutputFormat.LINEARPCM, audioQuality: AudioQuality.HIGH, sampleRate: 16000,
    linearPCMBitDepth: 16, linearPCMIsBigEndian: false, linearPCMIsFloat: false },
  android: { ...RecordingPresets.HIGH_QUALITY.android, sampleRate: 16000, numberOfChannels: 1 },
} as any;

export type MicStatus = "idle" | "listening" | "hearing" | "sending";
const CALIBRATE_MS = 400, END_SILENCE_MS = 2000, MAX_TURN_MS = 30000, NO_SPEECH_MS = 15000, DEAD_MS = 3000;
const BELOW_PEAK_DB = 18, STEADY_DB = 5, STEADY_N = 22, MIN_TURN_MS = 1200;   // quiet = 18 dB under your voice for 2.0 s, or 2.2 s of flat hum (request 92, 24 Oct)
// Not re-learning the room each turn: a loud stretch over within 250 ms of the start is the tail of Ananta's voice, not speech
// (the whole recording is kept either way; only "hearing you" waits). Same as src/webmic.js.
const GUARD_MS = 250;
const clampFloor = (f: number) => Math.max(-75, Math.min(-35, f));

// What the last recording really is: WAV on the phone and on the website's voice mode (src/webmic.js); the old browser
// recorder (only if the browser lacks Web Audio) records WebM (Chrome) or MP4 (Safari).
let lastMime = "audio/wav";
export const micMime = () => lastMime;

// One turn's timing, sent with /v3/voice/turn so the repair shop can measure the gap between his voice and the mic.
export type ClientTiming = {
  tts_end_to_live_ms: number | null; onset_ms: number | null; speech_ms: number | null; end_silence_ms: number | null;
  preroll_ms: number | null; bytes: number | null; arm_to_live_ms: number | null; capture: string; platform: string;
};
type TurnTiming = { onsetMs: number | null; speechMs: number | null; endSilenceMs: number | null; prerollMs: number | null;
  bytes: number | null; armToLiveMs: number | null; capture: string };

export type MicApi = {
  status: MicStatus;
  level: number;
  open: () => Promise<boolean>;                 // voice mode starts (call it straight from the tap): permission + mic, once
  close: () => Promise<void>;                   // voice mode ended: let the microphone go
  start: (force?: boolean, wanted?: () => boolean) => Promise<boolean>;
  send: () => void;
  cancel: () => Promise<void>;
  state: () => MicStatus;
  busy: () => boolean;
  hearing: () => boolean;
  clientTiming: (ttsEndToLiveMs?: number | null) => ClientTiming | null;
};

const toTiming = (t: TurnTiming | null, gap: number | null | undefined): ClientTiming | null => t ? {
  tts_end_to_live_ms: gap ?? null, onset_ms: t.onsetMs, speech_ms: t.speechMs, end_silence_ms: t.endSilenceMs, preroll_ms: t.prerollMs,
  bytes: t.bytes, arm_to_live_ms: t.armToLiveMs, capture: t.capture, platform: Platform.OS,
} : null;

async function toBase64(uri: string): Promise<string> {
  const blob = await (await fetch(uri)).blob();
  lastMime = (blob.type || "audio/wav").split(";")[0];
  return await new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onerror = () => rej(new Error("could not read the recording"));
    fr.onloadend = () => res(String(fr.result).split(",")[1] ?? "");
    fr.readAsDataURL(blob);
  });
}

// run mic operations one at a time
function useSerial() {
  const queue = useRef<Promise<any>>(Promise.resolve());
  const serial = <T,>(fn: () => Promise<T>): Promise<T> => {
    const p = queue.current.then(fn, fn);
    queue.current = p.catch(() => {});
    return p;
  };
  return { queue, serial };
}

// ---- iPhone app (and any browser without Web Audio): expo-audio's recorder, one recording per turn ----
function useRecorderMic(onTurn: (b64: string) => void, onNoSpeech?: () => void): MicApi {
  const rec = useAudioRecorder(WAV);
  const st = useAudioRecorderState(rec, 100);
  const [status, setStatusS] = useState<MicStatus>("idle");
  const statusRef = useRef<MicStatus>("idle");
  const recordingRef = useRef(false);
  const v = useRef({ start: 0, floor: -60, samples: [] as number[], spoke: false, lastLoud: 0, loudRun: 0, done: true, heardAny: false, gen: 0,
    peak: -160, spokeAt: 0, win: [] as number[], calibrated: false, armMs: 0 as number });
  // a voice conversation: permission asked once; the room level learned on its first turn is kept for the next ones
  const sess = useRef({ on: false, perm: false, floor: null as number | null });
  const timing = useRef<TurnTiming | null>(null);
  const cb = useRef(onTurn), cbNo = useRef(onNoSpeech);
  cb.current = onTurn;
  cbNo.current = onNoSpeech;
  const { queue, serial } = useSerial();
  const setStatus = (s: MicStatus) => { statusRef.current = s; setStatusS(s); };
  recordingRef.current = !!st.isRecording;

  const keepRoom = () => { if (sess.current.on && v.current.calibrated) sess.current.floor = clampFloor(v.current.floor); };
  const noteTiming = (b64Len: number | null) => {
    const x = v.current, end = Date.now();
    timing.current = { onsetMs: x.spoke ? x.spokeAt - x.start : null, speechMs: x.spoke ? x.lastLoud - x.spokeAt : null,
      endSilenceMs: x.spoke ? end - x.lastLoud : null, prerollMs: x.spoke ? x.spokeAt - x.start : null,   // the whole recording is sent
      bytes: b64Len != null ? Math.floor((b64Len * 3) / 4) : null, armToLiveMs: x.armMs, capture: "expo-audio" };
  };

  const open = async (): Promise<boolean> => {
    let granted = false;
    try { granted = (await requestRecordingPermissionsAsync()).granted; } catch { granted = false; }
    if (granted && !sess.current.on) sess.current = { on: true, perm: true, floor: null };
    return granted;
  };
  const close = (): Promise<void> => {
    sess.current = { on: false, perm: false, floor: null };
    return Promise.resolve();
  };

  // wanted(): checked right before recording starts (this runs queued, maybe later): a start nobody wants any more
  // (voice ended, question already sent) never records.
  const start = (force = false, wanted: () => boolean = () => true): Promise<boolean> => serial(async () => {
    if (!wanted()) return false;
    const t0 = Date.now();
    if (!sess.current.perm) {                                              // dictation: ask each time; voice mode asked once in open()
      const p = await requestRecordingPermissionsAsync();
      if (!p.granted || !wanted()) return false;
    }
    const live = statusRef.current === "listening" || statusRef.current === "hearing";
    if (live && !force && !v.current.done) return true;                    // already listening: nothing to do
    for (let attempt = 0; attempt < 3; attempt++) {                        // right after speaking, iOS may still be switching audio
      try {
        try { await rec.stop(); } catch { /* not recording */ }
        if (!wanted()) { setStatus("idle"); return false; }
        await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
        await rec.prepareToRecordAsync();
        if (!wanted()) {
          try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
          setStatus("idle");
          return false;
        }
        rec.record();
        keepRoom();
        const room = sess.current.on ? sess.current.floor : null;           // after the first turn: no re-learning of the room
        v.current = { start: Date.now(), floor: room ?? -60, samples: [], spoke: false, lastLoud: 0, loudRun: 0, done: false, heardAny: false, gen: v.current.gen + 1,
          peak: -160, spokeAt: 0, win: [], calibrated: room !== null, armMs: Date.now() - t0 };
        setStatus("listening");
        return true;
      } catch {
        await new Promise((r) => setTimeout(r, 350));
      }
    }
    setStatus("idle");
    return false;
  });

  // stop the current recording: send = deliver what was said (onTurn), else throw it away
  const finish = (send: boolean): Promise<void> => {
    if (v.current.done) return queue.current.then(() => undefined);
    const gen = v.current.gen;
    v.current.done = true;
    keepRoom();
    setStatus(send ? "sending" : "idle");
    return serial(async () => {
      if (gen !== v.current.gen) return;                                   // a newer recording already started
      try { await rec.stop(); } catch { /* */ }
      try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
      if (!send) { setStatus("idle"); return; }
      try {
        const uri = rec.uri;
        const b64 = uri ? await toBase64(uri) : "";
        noteTiming(b64 ? b64.length : null);
        setStatus("idle");
        if (b64) cb.current(b64); else cbNo.current?.();
      } catch {
        setStatus("idle");
        cbNo.current?.();
      }
    });
  };

  useEffect(() => {
    const s = statusRef.current;
    if ((s !== "listening" && s !== "hearing") || v.current.done) return;
    const m = st.metering ?? -160;
    const now = Date.now(), x = v.current;
    const age = now - x.start;
    if (m > -159) x.heardAny = true;
    if (age > DEAD_MS && !x.heardAny) { finish(false).then(() => cbNo.current?.()); return; }   // recorder gives no sound at all: restart
    if (!x.calibrated && age < CALIBRATE_MS) { if (m > -160) x.samples.push(m); return; }
    if (x.samples.length) {
      const sorted = [...x.samples].sort((a, b) => a - b);
      x.floor = clampFloor(sorted[Math.floor(sorted.length / 2)]);   // a loud start (end of Ananta's voice) can't set the bar too high
      x.samples = [];
      x.calibrated = true;
    }
    const thr = Math.min(x.floor + 10, -30);
    if (x.spoke) x.peak = Math.max(x.peak, m);
    const bar = x.spoke ? Math.max(thr, x.peak - BELOW_PEAK_DB) : thr;     // after you start: "loud" means close to your own voice
    x.win.push(m);
    if (x.win.length > STEADY_N) x.win.shift();
    if (m > bar) {
      x.loudRun += 1;
      x.lastLoud = now;
      if (x.loudRun >= 2 && !x.spoke && age > GUARD_MS) { x.spoke = true; x.spokeAt = now; x.peak = m; setStatus("hearing"); }
    } else {
      x.loudRun = 0;
      if (!x.spoke) x.floor = 0.97 * x.floor + 0.03 * m;          // follow slow changes in room noise
    }
    if (x.spoke && now - x.lastLoud > END_SILENCE_MS) { finish(true); return; }
    if (x.spoke && now - x.spokeAt > MIN_TURN_MS && x.win.length >= STEADY_N &&                 // a flat hum (fan, TV) is not speech
        Math.max(...x.win) - Math.min(...x.win) < STEADY_DB) { finish(true); return; }
    if (age > MAX_TURN_MS) { const spoke = x.spoke; finish(spoke).then(() => { if (!spoke) cbNo.current?.(); }); return; }
    if (!x.spoke && age > NO_SPEECH_MS) { finish(false).then(() => cbNo.current?.()); }
  }, [st.metering, st.durationMillis]);

  useEffect(() => () => { try { rec.stop(); } catch { /* */ } }, []);

  // stop and throw away, ALWAYS (even if nothing is recording yet or a start is queued before it)
  const cancel = (): Promise<void> => {
    if (!v.current.done) keepRoom();
    v.current.done = true;
    setStatus("idle");
    return serial(async () => {
      try { await rec.stop(); } catch { /* not recording */ }
      try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
      v.current.done = true;
      setStatus("idle");
    });
  };

  return {
    status, level: st.metering ?? -160,
    open, close, start, send: () => { finish(true); }, cancel,
    state: () => statusRef.current,
    // read live (not from a render) by the voice loop
    busy: () => statusRef.current === "sending" || statusRef.current === "hearing" || (statusRef.current === "listening" && !v.current.done && recordingRef.current),
    hearing: () => statusRef.current === "hearing",
    clientTiming: (gap) => toTiming(timing.current, gap),
  };
}

// ---- website: one microphone session for the whole conversation (src/webmic.js) ----
function useWebSessionMic(onTurn: (b64: string) => void, onNoSpeech?: () => void): MicApi {
  const sessRef = useRef<ReturnType<typeof createWebMic> | null>(null);
  if (!sessRef.current) sessRef.current = createWebMic();
  const sess = sessRef.current;
  const [status, setStatusS] = useState<MicStatus>("idle");
  const [level, setLevel] = useState(-160);
  const statusRef = useRef<MicStatus>("idle");
  const v = useRef({ done: true, gen: 0 });
  const want = useRef(false);                     // voice mode: keep the stream open between turns
  const timing = useRef<TurnTiming | null>(null);
  const cb = useRef(onTurn), cbNo = useRef(onNoSpeech);
  cb.current = onTurn;
  cbNo.current = onNoSpeech;
  const { queue, serial } = useSerial();
  const setStatus = (s: MicStatus) => { statusRef.current = s; setStatusS(s); };
  const letGo = () => { if (!want.current) sess.close(); };          // dictation: the mic goes as soon as the turn is over

  // NOT queued: it must make the AudioContext inside the tap that started voice mode (Safari)
  const open = (): Promise<boolean> => {
    want.current = true;
    return sess.open().then((ok) => { if (!ok) want.current = false; return ok; });
  };
  const close = (): Promise<void> => {
    want.current = false;
    v.current.done = true;
    sess.disarm(false);
    setStatus("idle");
    return serial(async () => { if (!want.current) sess.close(); });
  };

  const start = (force = false, wanted: () => boolean = () => true): Promise<boolean> => serial(async () => {
    if (!wanted()) return false;
    const live = statusRef.current === "listening" || statusRef.current === "hearing";
    if (live && !force && !v.current.done && sess.live) return true;     // already listening: nothing to do
    if (!sess.isOpen) {                                                  // dictation, or the stream broke (iOS took the mic)
      const ok = await sess.open();
      if (!ok || !wanted()) { letGo(); setStatus("idle"); return false; }
    }
    if (!wanted()) return false;
    const gen = v.current.gen + 1;
    v.current = { done: true, gen };
    const mine = () => gen === v.current.gen && !v.current.done;
    const ok = await sess.arm({
      onLevel: (db: number) => { if (mine()) setLevel(db); },
      onSpeech: () => { if (mine()) setStatus("hearing"); },
      onEnd: (reason: string) => {
        if (!mine()) return;
        if (reason === "silence" || reason === "flat" || reason === "max") finish(true);
        else finish(false).then(() => cbNo.current?.());               // no speech, or no sound at all (restarts the mic)
      },
    });
    if (!ok || !wanted() || gen !== v.current.gen) {
      if (ok && gen === v.current.gen) sess.disarm(false);
      if (gen === v.current.gen) setStatus("idle");
      letGo();
      return false;
    }
    v.current.done = false;
    setStatus("listening");
    return true;
  });

  // stop the current turn: send = deliver what was said (onTurn), else throw it away
  const finish = (send: boolean): Promise<void> => {
    if (v.current.done) return queue.current.then(() => undefined);
    const gen = v.current.gen;
    v.current.done = true;
    setStatus(send ? "sending" : "idle");
    let out: ReturnType<typeof sess.disarm> = null;
    try { out = sess.disarm(send); } catch { out = null; }               // instant: nothing more is kept from here
    const t = sess.timing;
    if (t) timing.current = { onsetMs: t.onsetMs, speechMs: t.speechMs, endSilenceMs: t.endSilenceMs, prerollMs: t.prerollMs,
      bytes: t.bytes, armToLiveMs: t.armToLiveMs, capture: t.capture };
    return serial(async () => {
      letGo();
      if (gen !== v.current.gen) return;                                 // a newer turn already started
      setStatus("idle");
      if (!send) return;
      lastMime = "audio/wav";
      if (out && out.b64) cb.current(out.b64); else cbNo.current?.();
    });
  };

  // stop and throw away, ALWAYS (even if nothing is armed yet or a start is queued before it)
  const cancel = (): Promise<void> => {
    v.current.done = true;
    sess.disarm(false);
    setStatus("idle");
    return serial(async () => {
      sess.disarm(false);
      v.current.done = true;
      setStatus("idle");
      letGo();
    });
  };

  useEffect(() => () => { want.current = false; sess.close(); }, []);

  return {
    status, level: status === "idle" ? -160 : level,
    open, close, start, send: () => { finish(true); }, cancel,
    state: () => statusRef.current,
    busy: () => statusRef.current === "sending" || statusRef.current === "hearing" || (statusRef.current === "listening" && !v.current.done && sess.live),
    hearing: () => statusRef.current === "hearing",
    clientTiming: (gap) => toTiming(timing.current, gap),
  };
}

// Chosen once per bundle (the platform never changes while the app runs), so the hooks inside are always the same ones.
export const useMic: (onTurn: (b64: string) => void, onNoSpeech?: () => void) => MicApi =
  Platform.OS === "web" && webMicSupported() ? useWebSessionMic : useRecorderMic;
