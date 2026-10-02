// Microphone with automatic end-of-speech detection that adapts to the room.
// It first listens ~0.4 s to learn the background level, then treats "clearly louder than the room" as speech and
// ends the turn after ~1.1 s back at room level. Hard limit 25 s per turn. Used by dictation and by voice mode.
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
const CALIBRATE_MS = 400, END_SILENCE_MS = 1100, MAX_TURN_MS = 25000, NO_SPEECH_MS = 15000;

async function toBase64(uri: string): Promise<string> {
  const blob = await (await fetch(uri)).blob();
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
  const v = useRef({ start: 0, floor: -60, samples: [] as number[], spoke: false, lastLoud: 0, loudRun: 0, done: false });
  const cb = useRef(onTurn), cbNo = useRef(onNoSpeech);
  cb.current = onTurn;
  cbNo.current = onNoSpeech;
  const setStatus = (s: MicStatus) => { statusRef.current = s; setStatusS(s); };

  const start = async (): Promise<boolean> => {
    const p = await requestRecordingPermissionsAsync();
    if (!p.granted) return false;
    for (let attempt = 0; attempt < 3; attempt++) {          // right after speaking, iOS can still be switching the audio over: retry
      try {
        try { await rec.stop(); } catch { /* not recording */ }
        await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
        await rec.prepareToRecordAsync();
        rec.record();
        v.current = { start: Date.now(), floor: -60, samples: [], spoke: false, lastLoud: 0, loudRun: 0, done: false };
        setStatus("listening");
        return true;
      } catch {
        await new Promise((r) => setTimeout(r, 400));
      }
    }
    setStatus("idle");
    return false;
  };

  const finish = async (send: boolean) => {
    if (v.current.done) return;
    v.current.done = true;
    setStatus(send ? "sending" : "idle");
    try { await rec.stop(); } catch { /* */ }
    try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
    if (!send) { setStatus("idle"); return; }
    try {
      const uri = rec.uri;
      const b64 = uri ? await toBase64(uri) : "";
      setStatus("idle");
      if (b64) cb.current(b64);
    } catch {
      setStatus("idle");
    }
  };

  useEffect(() => {
    const s = statusRef.current;
    if ((s !== "listening" && s !== "hearing") || v.current.done) return;
    const m = st.metering ?? -160;
    const now = Date.now(), x = v.current;
    const age = now - x.start;
    if (age < CALIBRATE_MS) { if (m > -160) x.samples.push(m); return; }
    if (x.samples.length) {
      const sorted = [...x.samples].sort((a, b) => a - b);
      x.floor = Math.max(-75, Math.min(-35, sorted[Math.floor(sorted.length / 2)]));   // a loud start (e.g. the end of Ananta's voice) can't set the bar too high
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
    if (age > MAX_TURN_MS) { finish(x.spoke); if (!x.spoke) cbNo.current?.(); return; }
    if (!x.spoke && age > NO_SPEECH_MS) { finish(false); cbNo.current?.(); }
  }, [st.metering, st.durationMillis]);

  useEffect(() => () => { try { rec.stop(); } catch { /* */ } }, []);

  return {
    status, level: st.metering ?? -160,
    start, send: () => finish(true), cancel: () => finish(false),
  };
}
