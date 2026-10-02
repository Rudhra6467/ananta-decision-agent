// Speaking answers, in ONE voice.
//
// Natural voice (default): the Jarvis service turns the whole answer into one audio file (Kokoro on the Mac) and tells us
// when each sentence starts. We download it, play it, and call onPart(i) as playback reaches sentence i, so highlights
// move exactly with the voice. One file = one voice: an answer can never switch voices halfway.
// Phone voice: used for the whole answer only when the natural voice can't be reached (and the screen says so).
//
// Every speak() ALWAYS settles: "done" when it finished, "stopped" when stop() cut it off. Nothing can be left
// waiting forever, which is what used to leave voice mode stuck after a tap.
import * as SecureStore from "expo-secure-store";
import * as Speech from "expo-speech";
import { createAudioPlayer, setAudioModeAsync, type AudioPlayer } from "expo-audio";
import { File, Paths } from "expo-file-system";
import { api, server, token } from "./api";

export type SpeakResult = "done" | "stopped";

let voiceId: string | undefined;
let phoneVoiceName = "default";
let picked = false;
export let rate = 0.9;
export let engine: "natural" | "phone" = "natural";
export let voice = "Calm";
export const VOICES = ["Calm", "Friendly", "Deep", "British", "Bright"];
export const RATES = [0.8, 0.9, 1.0, 1.15, 1.3];

// what actually spoke last time (shown under the orb)
export let lastEngine: "natural" | "phone" | null = null;
export let lastNote = "";

const PREFERRED = ["Ava", "Zoe", "Evan", "Nathan", "Joelle", "Noelle", "Samantha", "Allison", "Susan", "Tom", "Serena", "Daniel"];

export async function init() {
  if (picked) return;
  picked = true;
  try {
    const [r, e, v] = await Promise.all(["tts_rate", "tts_engine", "tts_voice"].map((k) => SecureStore.getItemAsync(k)));
    if (r && RATES.includes(Number(r))) rate = Number(r);
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
    if (best) { voiceId = best.identifier; phoneVoiceName = best.name; }
  } catch { /* */ }
}

export const voiceLabel = () => (engine === "natural" ? `Natural · ${voice}` : `Phone · ${phoneVoiceName}`);

async function save(k: string, v: string) { try { await SecureStore.setItemAsync(k, v); } catch { /* */ } }
export async function setRate(r: number) { rate = r; await save("tts_rate", String(r)); }       // applies from the next answer
export async function setEngine(e: "natural" | "phone") { engine = e; naturalDownUntil = 0; await save("tts_engine", e); }
export async function setVoice(v: string) { voice = v; await save("tts_voice", v); }

// The same sentence split the Jarvis service uses (so the audio it prepared ahead matches exactly).
export const sentences = (t: string) => (t || "").split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean);

// What the service needs to prepare the natural voice ahead of time (sent with each voice question).
export const prepHint = () => (engine === "natural" ? { voice, speed: rate } : undefined);

// ---- one active utterance at a time ----------------------------------------------------------
let seq = 0;
let active: { id: number; settle: (r: SpeakResult) => void } | null = null;
let current: AudioPlayer | null = null;
let naturalDownUntil = 0;              // after a failure, use the phone voice for a short while (no waiting on a dead server)
const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

export function isSpeaking() { return active !== null; }

// Cut off whatever is speaking. Its speak() promise settles with "stopped".
export function stop() {
  seq++;
  try { Speech.stop(); } catch { /* */ }
  try { current?.pause(); } catch { /* */ }
  const a = active;
  active = null;
  a?.settle("stopped");
}

// ---- natural voice: one file per answer --------------------------------------------------------
type Meta = { id: string; offsets: number[]; duration: number };

async function fetchMeta(parts: string[], id?: string): Promise<Meta> {
  if (id) return api<Meta>(`/v3/voice/answer/${id}`, undefined, 30000);       // already being made since the answer was written
  return api<Meta>("/v3/voice/answer", { sentences: parts, voice, speed: rate }, 30000);
}

async function download(id: string): Promise<File> {
  const [base, tok] = [await server(), await token()];
  const f = new File(Paths.cache, `ananta-voice-${id}.mp3`);
  try { if (f.exists) return f; } catch { /* */ }
  return File.downloadFileAsync(`${base}/v3/voice/answer/${id}/audio`, f,
    { headers: tok ? { Authorization: `Bearer ${tok}` } : {}, idempotent: true });
}

// "ok" | "stopped" | "failed" (could not start: caller falls back to the phone voice for the whole answer)
async function playNatural(parts: string[], onPart: (i: number) => void, my: number, id?: string): Promise<"ok" | "stopped" | "failed"> {
  let meta: Meta, file: File;
  try {
    if (id) [meta, file] = await Promise.all([fetchMeta(parts, id), download(id)]);   // both at once: saves a round trip
    else { meta = await fetchMeta(parts); file = await download(meta.id); }
    if (my !== seq) return "stopped";
  } catch {
    return "failed";
  }
  try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
  if (my !== seq) return "stopped";
  const p = createAudioPlayer({ uri: file.uri });
  current = p;
  let finished = false;
  const sub = p.addListener("playbackStatusUpdate", (st: any) => { if (st?.didJustFinish) finished = true; });
  try {
    p.play();
    const t0 = Date.now();
    let started = 0, part = -1;
    const offs = meta.offsets?.length ? meta.offsets : [0];
    while (true) {
      await sleep(80);
      if (my !== seq) { try { p.pause(); } catch { /* */ } return "stopped"; }
      const t = p.currentTime || 0;
      if (!started) {
        if (p.playing || t > 0.02) started = Date.now();
        else if (Date.now() - t0 > 6000) return "failed";
        else { if (p.isLoaded && Date.now() - t0 > 500) { try { p.play(); } catch { /* */ } } continue; }
      }
      // highlight: the sentence whose start the playback has reached
      let k = 0;
      for (let i = 0; i < offs.length; i++) if (t + 0.05 >= offs[i]) k = i;
      if (k > part) { for (let i = part + 1; i <= k; i++) onPart(i); part = k; }
      const dur = meta.duration || p.duration || 0;
      if (finished) return "ok";
      if (dur > 0 && t >= dur - 0.08) return "ok";
      if (dur > 0 && !p.playing && t >= dur - 0.4) return "ok";
      if (Date.now() - started > (dur > 0 ? dur * 1000 + 2500 : 60000)) return "ok";     // watchdog: never hang
    }
  } finally {
    sub.remove();
    try { p.remove(); } catch { /* */ }
    if (current === p) current = null;
    try { file.delete(); } catch { /* */ }
  }
}

// ---- phone voice -------------------------------------------------------------------------------
// expo-speech's 1.0 is brisk on iOS; scale so 1.0 here sounds like a normal talking pace.
function playPhone(parts: string[], onPart: (i: number) => void, my: number): Promise<"ok" | "stopped"> {
  return new Promise((res) => {
    let settled = false;
    const end = (r: "ok" | "stopped") => { if (!settled) { settled = true; clearInterval(w); res(r); } };
    const w = setInterval(() => { if (my !== seq) end("stopped"); }, 200);
    const next = (i: number) => {
      if (my !== seq) return end("stopped");
      if (i >= parts.length) return end("ok");
      onPart(i);
      Speech.speak(parts[i], {
        voice: voiceId, rate: rate * 0.92, pitch: 1.0,
        onDone: () => next(i + 1),
        onStopped: () => end("stopped"),
        onError: () => next(i + 1),
      });
    };
    setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }).catch(() => {}).finally(() => next(0));
  });
}

// ---- public ------------------------------------------------------------------------------------
// Speak these sentences; onPart(i) fires as sentence i starts. Always settles.
export function speak(parts: string[], onPart: (i: number) => void = () => {}, id?: string): Promise<SpeakResult> {
  stop();
  const my = ++seq;
  parts = parts.map((x) => x.trim()).filter(Boolean);
  return new Promise<SpeakResult>((resolve) => {
    let settled = false;
    const settle = (r: SpeakResult) => { if (settled) return; settled = true; if (active?.id === my) active = null; resolve(r); };
    active = { id: my, settle };
    if (!parts.length) return settle("done");
    (async () => {
      const wantNatural = engine === "natural" && Date.now() > naturalDownUntil;
      if (wantNatural) {
        const r = await playNatural(parts, onPart, my, id);
        if (r === "ok") { lastEngine = "natural"; lastNote = ""; return settle("done"); }
        if (r === "stopped" || my !== seq) return settle("stopped");
        naturalDownUntil = Date.now() + 60000;              // the Mac's voice didn't answer: phone voice for a minute
        lastNote = "The natural voice didn't answer, so the phone voice spoke.";
      }
      const r2 = await playPhone(parts, onPart, my);
      lastEngine = "phone";
      settle(r2 === "ok" ? "done" : "stopped");
    })().catch(() => settle("done"));
  });
}

export const speakText = (text: string) => speak(sentences(text));

// Older callback style (kept for screens that use it).
export function sayParts(parts: string[], onPart: (i: number) => void, done?: () => void) {
  speak(parts, onPart).then(() => done?.());
}
export const say = (text: string, done?: () => void) => sayParts(sentences(text), () => {}, done);
export const sayAsync = (text: string) => speakText(text).then(() => undefined);

// Make the tour's audio ahead of time, step by step (each step is one file).
export function warm(texts: string[]) {
  if (engine !== "natural" || Date.now() < naturalDownUntil) return;
  texts.slice(0, 24).forEach((t) => api("/v3/voice/answer", { sentences: sentences(t), voice, speed: rate, wait: false }).catch(() => {}));
}
