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
export async function setRate(r: number) { rate = r; try { current?.setPlaybackRate(r, "high"); } catch { /* */ } await save("tts_rate", String(r)); }
export async function setEngine(e: "natural" | "phone") { engine = e; await save("tts_engine", e); }
export async function setVoice(v: string) { voice = v; await save("tts_voice", v); }

// ---- phone voice -----------------------------------------------------------------------------
// expo-speech's 1.0 is already brisk on iOS; scale so 1.0 here sounds like a normal talking pace.
const phoneRate = () => rate * 0.92;
function phoneSay(text: string, done: () => void) {
  Speech.speak(text, { voice: voiceId, rate: phoneRate(), pitch: 1.0, onDone: done, onStopped: done, onError: done });
}

// ---- natural voice -----------------------------------------------------------------------------
// One player per sentence; the next sentence loads while the current one plays (no gaps). A sentence always ends:
// on "finished", or when its time is up (watchdog), so Ananta can never get stuck "speaking" and stop listening.
let seq = 0;
let lastNaturalFail = 0;
let current: AudioPlayer | null = null;
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function load(uri: string, headers: Record<string, string>): AudioPlayer {
  const p = createAudioPlayer({ uri, headers });
  try { p.setPlaybackRate(rate, "high"); } catch { /* */ }
  return p;
}

// resolves "ok" when it ends, "fail" if it never starts (8 s), "stopped" if Ananta was interrupted
async function playOne(p: AudioPlayer, my: number, onStart: () => void): Promise<"ok" | "fail" | "stopped"> {
  current = p;
  let finished = false;
  const sub = p.addListener("playbackStatusUpdate", (st: any) => { if (st.didJustFinish) finished = true; });
  try {
    try { p.setPlaybackRate(rate, "high"); } catch { /* */ }
    p.play();
    const t0 = Date.now();
    let started = 0;
    while (true) {
      await sleep(120);
      if (my !== seq) { try { p.pause(); } catch { /* */ } return "stopped"; }
      if (!started && (p.playing || p.currentTime > 0.05)) { started = Date.now(); onStart(); }
      if (!started) {
        if (Date.now() - t0 > 8000) return "fail";
        if (p.isLoaded && !p.playing && Date.now() - t0 > 600) { try { p.play(); } catch { /* */ } }
        continue;
      }
      const dur = p.duration || 0;
      if (finished) return "ok";
      if (dur > 0 && p.currentTime >= dur - 0.12) return "ok";
      if (!p.playing && dur > 0 && p.currentTime >= dur - 0.4) return "ok";
      const limit = dur > 0 ? (dur / Math.max(0.5, rate)) * 1000 + 2500 : 30000;
      if (Date.now() - started > limit) return "ok";                     // watchdog: never hang
    }
  } finally {
    sub.remove();
    try { p.remove(); } catch { /* */ }
    if (current === p) current = null;
  }
}

async function naturalParts(parts: string[], onPart: (i: number) => void, my: number): Promise<number> {
  // returns the index of the first sentence NOT spoken (parts.length when all were spoken)
  const r = await api<{ ids: string[] }>("/v3/voice/prepare", { sentences: parts, voice });
  if (my !== seq) return parts.length;
  const [base, tok] = [await server(), await token()];
  const headers: Record<string, string> = tok ? { Authorization: `Bearer ${tok}` } : {};
  try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
  const url = (i: number) => `${base}/v3/voice/clip/${r.ids[i]}`;
  let next: AudioPlayer | null = load(url(0), headers);
  for (let i = 0; i < parts.length; i++) {
    const p = next!;
    next = i + 1 < parts.length ? load(url(i + 1), headers) : null;     // the next sentence loads while this one plays
    const res = await playOne(p, my, () => onPart(i));
    if (res !== "ok") {
      try { next?.remove(); } catch { /* */ }
      return res === "stopped" ? parts.length : i;
    }
  }
  return parts.length;
}

// ---- public -----------------------------------------------------------------------------------
export function stop() {
  seq++;
  Speech.stop();
  try { current?.pause(); } catch { /* */ }
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
