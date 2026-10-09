// Ananta's voice on the website (plan 2.7). Browsers (Safari above all) only let a page play sound after a tap, and only on an
// audio element that was started inside that tap. So: ONE shared audio element, "unlocked" by the first tap anywhere on the
// page (a silent clip, plus an empty phrase for the browser voice); every answer then plays through that same element.
// The phone app never uses this file's player (expo-audio does the work there).
import { Platform } from "react-native";

const web = Platform.OS === "web" && typeof window !== "undefined";
let el: HTMLAudioElement | null = null;
let unlocked = false;
// 0.1 s of silence (a valid tiny WAV) to unlock the element
const SILENT = "data:audio/wav;base64,UklGRiQAAABXQVZFZm10IBAAAAABAAEAQB8AAIA+AAACABAAZGF0YQAAAAA=";

export const isWeb = web;
export const audioUnlocked = () => unlocked;

function element(): HTMLAudioElement {
  if (!el) {
    el = new Audio();
    el.preload = "auto";
    (el as any).playsInline = true;
  }
  return el;
}

export function unlockAudio() {
  if (!web || unlocked) return;
  const a = element();
  try {
    a.muted = true;
    a.src = SILENT;
    const p = a.play();
    const done = () => { a.muted = false; unlocked = true; };
    if (p && typeof p.then === "function") p.then(() => { a.pause(); done(); }).catch(() => { a.muted = false; });
    else done();
  } catch { /* the next tap tries again */ }
  try {                                                   // Safari's built-in voice also wants its first phrase inside a tap
    const u = new SpeechSynthesisUtterance(" ");
    u.volume = 0;
    window.speechSynthesis?.speak(u);
  } catch { /* no browser voice */ }
}

if (web) {
  const onTap = () => { unlockAudio(); if (unlocked) { ["pointerdown", "touchend", "keydown"].forEach((e) => document.removeEventListener(e, onTap, true)); } };
  ["pointerdown", "touchend", "keydown"].forEach((e) => document.addEventListener(e, onTap, true));
}

// The few calls tts.ts makes on a player, backed by the shared element.
export function webPlayer(uri: string) {
  const a = element();
  a.muted = false;
  a.src = uri;
  const subs: ((st: any) => void)[] = [];
  const ended = () => subs.forEach((f) => f({ didJustFinish: true }));
  a.addEventListener("ended", ended);
  return {
    play: () => { a.play()?.catch?.(() => {}); },
    pause: () => { try { a.pause(); } catch { /* */ } },
    get currentTime() { return a.currentTime || 0; },
    get duration() { return Number.isFinite(a.duration) ? a.duration : 0; },
    get playing() { return !a.paused && !a.ended; },
    get isLoaded() { return a.readyState >= 2; },
    addListener: (_ev: string, f: (st: any) => void) => { subs.push(f); return { remove: () => { const i = subs.indexOf(f); if (i >= 0) subs.splice(i, 1); } }; },
    remove: () => { a.removeEventListener("ended", ended); try { a.pause(); } catch { /* */ } },
  };
}

// Download an answer's audio with the sign-in, as a local blob address the shared element can play.
export async function fetchBlobUri(url: string, tok: string | null): Promise<{ uri: string; delete: () => void; exists: boolean }> {
  const r = await fetch(url, { headers: tok ? { Authorization: `Bearer ${tok}` } : {} });
  if (!r.ok) throw new Error(`audio ${r.status}`);
  const uri = URL.createObjectURL(await r.blob());
  return { uri, exists: true, delete: () => { try { URL.revokeObjectURL(uri); } catch { /* */ } } };
}
