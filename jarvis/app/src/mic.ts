// Microphone with automatic end-of-speech detection that adapts to the room.
// It first listens ~0.4 s to learn the background level, then treats "clearly louder than the room" as speech and
// ends the turn after ~1.1 s back at room level. Hard limit 25 s per turn. Used by dictation and by voice mode.
//
// Every start / stop runs one after another (a small queue), so quick taps or overlapping restarts can never
// tangle the recorder. start() is safe to call while it is already listening.
import { useEffect, useRef, useState } from "react";
import {
  AudioQuality, IOSOutputFormat, RecordingPresets, requestRecordingPermissionsAsync, setAudioModeAsync,
  useAudioRecorder, useAudioRecorderState,
} from "expo-audio";

const WAV = {
  ...RecordingPresets.HIGH_QUALITY,
  extension: ".wav", sampleRate: 16000, numberOfChannels: 1, bitRate: 256000, isMeteringEnabled: true,
  ios: { extension: ".wav", outputFormat: IOSOutputFormat.LINEARPCM, audioQuality: AudioQuality.HIGH, sampleRate: 16000,
    linearPCMBitDepth: 16, linearPCMIsBigEndian: false, linearPCMIsFloat: false },
  android: { ...RecordingPresets.HIGH_QUALITY.android, sampleRate: 16000, numberOfChannels: 1 },
} as any;

export type MicStatus = "idle" | "listening" | "hearing" | "sending";
const CALIBRATE_MS = 400, END_SILENCE_MS = 1100, MAX_TURN_MS = 25000, NO_SPEECH_MS = 15000, DEAD_MS = 3000;

// What the last recording really is: WAV on the phone; on the website the browser records WebM (Chrome) or MP4 (Safari).
let lastMime = "audio/wav";
export const micMime = () => lastMime;

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

export function useMic(onTurn: (b64: string) => void, onNoSpeech?: () => void) {
  const rec = useAudioRecorder(WAV);
  const st = useAudioRecorderState(rec, 100);
  const [status, setStatusS] = useState<MicStatus>("idle");
  const statusRef = useRef<MicStatus>("idle");
  const recordingRef = useRef(false);
  const v = useRef({ start: 0, floor: -60, samples: [] as number[], spoke: false, lastLoud: 0, loudRun: 0, done: true, heardAny: false, gen: 0 });
  const cb = useRef(onTurn), cbNo = useRef(onNoSpeech);
  cb.current = onTurn;
  cbNo.current = onNoSpeech;
  const queue = useRef<Promise<any>>(Promise.resolve());
  const setStatus = (s: MicStatus) => { statusRef.current = s; setStatusS(s); };
  recordingRef.current = !!st.isRecording;

  // run mic operations one at a time
  const serial = <T,>(fn: () => Promise<T>): Promise<T> => {
    const p = queue.current.then(fn, fn);
    queue.current = p.catch(() => {});
    return p;
  };

  // wanted(): checked right before recording starts (this runs queued, maybe later): a start nobody wants any more
  // (voice ended, question already sent) never records.
  const start = (force = false, wanted: () => boolean = () => true): Promise<boolean> => serial(async () => {
    if (!wanted()) return false;
    const p = await requestRecordingPermissionsAsync();
    if (!p.granted || !wanted()) return false;
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
        v.current = { start: Date.now(), floor: -60, samples: [], spoke: false, lastLoud: 0, loudRun: 0, done: false, heardAny: false, gen: v.current.gen + 1 };
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
    setStatus(send ? "sending" : "idle");
    return serial(async () => {
      if (gen !== v.current.gen) return;                                   // a newer recording already started
      try { await rec.stop(); } catch { /* */ }
      try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
      if (!send) { setStatus("idle"); return; }
      try {
        const uri = rec.uri;
        const b64 = uri ? await toBase64(uri) : "";
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
    if (age < CALIBRATE_MS) { if (m > -160) x.samples.push(m); return; }
    if (x.samples.length) {
      const sorted = [...x.samples].sort((a, b) => a - b);
      x.floor = Math.max(-75, Math.min(-35, sorted[Math.floor(sorted.length / 2)]));   // a loud start (end of Ananta's voice) can't set the bar too high
      x.samples = [];
    }
    const thr = Math.min(x.floor + 10, -30);
    if (m > thr) {
      x.loudRun += 1;
      x.lastLoud = now;
      if (x.loudRun >= 2 && !x.spoke) { x.spoke = true; setStatus("hearing"); }
    } else {
      x.loudRun = 0;
      if (!x.spoke) x.floor = 0.97 * x.floor + 0.03 * m;          // follow slow changes in room noise
    }
    if (x.spoke && now - x.lastLoud > END_SILENCE_MS) { finish(true); return; }
    if (age > MAX_TURN_MS) { const spoke = x.spoke; finish(spoke).then(() => { if (!spoke) cbNo.current?.(); }); return; }
    if (!x.spoke && age > NO_SPEECH_MS) { finish(false).then(() => cbNo.current?.()); }
  }, [st.metering, st.durationMillis]);

  useEffect(() => () => { try { rec.stop(); } catch { /* */ } }, []);

  // stop and throw away, ALWAYS (even if nothing is recording yet or a start is queued before it)
  const cancel = (): Promise<void> => {
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
    start, send: () => { finish(true); }, cancel,
    state: () => statusRef.current,
    // read live (not from a render) by the voice loop
    busy: () => statusRef.current === "sending" || statusRef.current === "hearing" || (statusRef.current === "listening" && !v.current.done && recordingRef.current),
    hearing: () => statusRef.current === "hearing",
  };
}
