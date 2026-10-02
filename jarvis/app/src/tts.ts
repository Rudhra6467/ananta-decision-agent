// Speaking answers: picks the most natural English voice on the phone (Premium / Enhanced first) and a speed the owner sets.
import * as SecureStore from "expo-secure-store";
import * as Speech from "expo-speech";

let voiceId: string | undefined;
let voiceName = "default";
let picked = false;
export let rate = 1.0;

const PREFERRED = ["Ava", "Zoe", "Evan", "Nathan", "Joelle", "Noelle", "Samantha", "Allison", "Susan", "Tom", "Serena", "Daniel"];

export async function init() {
  if (picked) return;
  picked = true;
  try {
    const r = await SecureStore.getItemAsync("tts_rate");
    if (r) rate = Number(r) || 1.0;
  } catch { /* */ }
  try {
    const vs = (await Speech.getAvailableVoicesAsync()).filter((v) => v.language?.startsWith("en"));
    const score = (v: Speech.Voice) =>
      (String(v.quality) === "Enhanced" ? 100 : 0) + (/premium/i.test(v.name) || /premium/i.test(v.identifier) ? 200 : 0) +
      (v.language === "en-US" ? 10 : v.language === "en-GB" || v.language === "en-IN" ? 8 : 0) +
      (PREFERRED.findIndex((n) => v.name.startsWith(n)) >= 0 ? 20 - PREFERRED.findIndex((n) => v.name.startsWith(n)) : 0) -
      (/compact|eloquence|novelty|bells|bubbles|zarvox|whisper|bad news|good news|organ|trinoids|jester|superstar|grandma|grandpa|rocko|shelley|flo|reed|eddy|sandy/i.test(v.name) ? 500 : 0);
    const best = vs.sort((a, b) => score(b) - score(a))[0];
    if (best) { voiceId = best.identifier; voiceName = `${best.name} (${best.quality})`; }
  } catch { /* */ }
}

export const voiceLabel = () => voiceName;

export async function setRate(r: number) {
  rate = r;
  try { await SecureStore.setItemAsync("tts_rate", String(r)); } catch { /* */ }
}

export function say(text: string, done?: () => void) {
  Speech.stop();
  Speech.speak(text, { voice: voiceId, rate, pitch: 1.0, onDone: done, onStopped: done, onError: done });
}

export const stop = () => Speech.stop();

// Speak sentence by sentence, calling onPart(i) as each one starts (used to point at things while talking).
let seq = 0;
export function sayParts(parts: string[], onPart: (i: number) => void, done?: () => void) {
  Speech.stop();
  const my = ++seq;
  const next = (i: number) => {
    if (my !== seq) return;                                 // interrupted or replaced
    if (i >= parts.length) { done?.(); return; }
    onPart(i);
    Speech.speak(parts[i], {
      voice: voiceId, rate, pitch: 1.0,
      onDone: () => next(i + 1),
      onStopped: () => { if (my === seq) { seq++; done?.(); } },
      onError: () => next(i + 1),
    });
  };
  next(0);
}
