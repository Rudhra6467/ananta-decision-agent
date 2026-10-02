// Speaking answers.
// "Natural" (default): Gemini's human-sounding voice, made on the Jarvis service one sentence at a time (all sentences in parallel),
//   played in order. Each sentence calls onPart(i) the moment its audio starts, so highlights move exactly with the voice.
// "Phone": the phone's built-in voice (instant, used automatically if the natural voice is unavailable).
import * as SecureStore from "expo-secure-store";
import * as Speech from "expo-speech";
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import { api, server, token } from "./api";

let voiceId: string | undefined;
let phoneVoiceName = "default";
let picked = false;
export let rate = 0.9;
export let engine: "natural" | "phone" = "natural";
export let voice = "Calm";
export const VOICES = ["Calm", "Friendly", "Deep", "Bright"];
export const RATES = [0.8, 0.9, 1.0, 1.15, 1.3];

const PREFERRED = ["Ava", "Zoe", "Evan", "Nathan", "Joelle", "Noelle", "Samantha", "Allison", "Susan", "Tom", "Serena", "Daniel"];

export async function init() {
  if (picked) return;
  picked = true;
  try {
    const [r, e, v] = await Promise.all(["tts_rate", "tts_engine", "tts_voice"].map((k) => SecureStore.getItemAsync(k)));
    if (r) rate = Number(r) || rate;
    if (e === "phone" || e === "natural") engine = e;
    if (v && VOICES.includes(v)) voice = v;
  } catch { /* */ }
  try {
    const vs = (await Speech.getAvailableVoicesAsync()).filter((v) => v.language?.startsWith("en"));
    const score = (v: Speech.Voice) =>
      (String(v.quality) === "Enhanced" ? 100 : 0) + (/premium/i.test(v.name) || /premium/i.test(v.identifier) ? 200 : 0) +
      (v.language === "en-US" ? 10 : v.language === "en-GB" || v.language === "en-IN" ? 8 : 0) +
      (PREFERRED.findIndex((n) => v.name.startsWith(n)) >= 0 ? 20 - PREFERRED.findIndex((n) => v.name.startsWith(n)) : 0) -
      (/compact|eloquence|novelty|bells|bubbles|zarvox|whisper|bad news|good news|organ|trinoids|jester|superstar|grandma|grandpa|rocko|shelley|flo|reed|eddy|sandy/i.test(v.name) ? 500 : 0);
    const best = vs.sort((a, b) => score(b) - score(a))[0];
    if (best) { voiceId = best.identifier; phoneVoiceName = `${best.name} (${best.quality})`; }
  } catch { /* */ }
}

export const voiceLabel = () => (engine === "natural" ? `Natural · ${voice}` : `Phone · ${phoneVoiceName}`);

async function save(k: string, v: string) { try { await SecureStore.setItemAsync(k, v); } catch { /* */ } }
export async function setRate(r: number) { rate = r; player?.setPlaybackRate(r, "high"); await save("tts_rate", String(r)); }
export async function setEngine(e: "natural" | "phone") { engine = e; await save("tts_engine", e); }
export async function setVoice(v: string) { voice = v; await save("tts_voice", v); }

// ---- phone voice -----------------------------------------------------------------------------
// expo-speech's 1.0 is already brisk on iOS; scale so 1.0 here sounds like a normal talking pace.
const phoneRate = () => rate * 0.92;
function phoneSay(text: string, done: () => void) {
  Speech.speak(text, { voice: voiceId, rate: phoneRate(), pitch: 1.0, onDone: done, onStopped: done, onError: done });
}

// ---- natural voice -----------------------------------------------------------------------------
let player: AudioPlayer | null = null;
let seq = 0;
let lastNaturalFail = 0;

function getPlayer(): AudioPlayer {
  if (!player) player = createAudioPlayer(null);
  return player;
}

// Play one clip; resolves "ok" when it ends, "fail" if it never starts, "stopped" if replaced.
function playClip(uri: string, headers: Record<string, string>, my: number, onStart: () => void): Promise<"ok" | "fail" | "stopped"> {
  return new Promise((res) => {
    const p = getPlayer();
    let started = false, finished = false;
    const end = (r: "ok" | "fail" | "stopped") => { if (finished) return; finished = true; sub.remove(); clearTimeout(t); clearInterval(watch); res(r); };
    const sub = p.addListener("playbackStatusUpdate", (s: any) => {
      if (my !== seq) return end("stopped");
      if (s.playing && !started) { started = true; onStart(); }
      if (s.didJustFinish) end("ok");
    });
    const t = setTimeout(() => { if (!started) end("fail"); }, 15000);
    const watch = setInterval(() => { if (my !== seq) { p.pause(); end("stopped"); } }, 150);
    p.replace({ uri, headers });
    p.setPlaybackRate(rate, "high");
    p.play();
  });
}

async function naturalParts(parts: string[], onPart: (i: number) => void, my: number): Promise<number> {
  // returns the index of the first sentence NOT spoken (parts.length when all were spoken)
  const r = await api<{ ids: string[] }>("/v3/voice/prepare", { sentences: parts, voice });
  if (my !== seq) return parts.length;
  const [base, tok] = [await server(), await token()];
  const headers: Record<string, string> = tok ? { Authorization: `Bearer ${tok}` } : {};
  try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
  for (let i = 0; i < parts.length; i++) {
    if (my !== seq) return parts.length;
    const res = await playClip(`${base}/v3/voice/clip/${r.ids[i]}`, headers, my, () => onPart(i));
    if (res === "stopped") return parts.length;
    if (res === "fail") return i;
  }
  return parts.length;
}

// ---- public -----------------------------------------------------------------------------------
export function stop() {
  seq++;
  Speech.stop();
  try { player?.pause(); } catch { /* */ }
}

export const say = (text: string, done?: () => void) => sayParts([text], () => {}, done);

// Speak sentence by sentence, calling onPart(i) as each one starts (used to point at things while talking).
export function sayParts(parts: string[], onPart: (i: number) => void, done?: () => void) {
  stop();
  const my = seq;
  const finish = () => { if (my === seq) done?.(); };
  const phoneFrom = (i: number) => {
    if (my !== seq) return;
    if (i >= parts.length) return finish();
    onPart(i);
    Speech.speak(parts[i], {
      voice: voiceId, rate: phoneRate(), pitch: 1.0,
      onDone: () => phoneFrom(i + 1),
      onStopped: () => { /* stop() already moved seq on */ },
      onError: () => phoneFrom(i + 1),
    });
  };
  const useNatural = engine === "natural" && Date.now() - lastNaturalFail > 120000;
  if (!useNatural) return phoneFrom(0);
  naturalParts(parts, onPart, my)
    .then((next) => { if (next < parts.length) { lastNaturalFail = Date.now(); phoneFrom(next); } else finish(); })
    .catch(() => { lastNaturalFail = Date.now(); phoneFrom(0); });
}

// Speak and wait; resolves early when stopped (used by the tour; the Skip button calls stop()).
export function sayAsync(text: string): Promise<void> {
  return new Promise((res) => {
    let done = false, w: any = null;
    const end = () => { if (!done) { done = true; clearInterval(w); res(); } };
    sayParts([text], () => {}, end);
    const my = seq;
    w = setInterval(() => { if (my !== seq) end(); }, 200);
  });
}

// Make the first sentences of the next things to say ahead of time (the tour uses this).
export function warm(texts: string[]) {
  if (engine !== "natural" || !texts.length) return;
  api("/v3/voice/prepare", { sentences: texts.slice(0, 24), voice }).catch(() => {});
}
