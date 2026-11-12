// Madhav, 3 Nov 2026: the suggested-question bar under the chat shows once after login and is gone for good once he types, talks or picks
// one; and while he types, the bottom bar (with its raised orb) steps out of the way so the typing box is never covered.
import { useEffect, useState } from "react";

const KEY = "ananta.starters.done";

export const startersDone = (): boolean => { try { return window.localStorage.getItem(KEY) === "1"; } catch { return false; } };
export const markStartersDone = (): void => { try { window.localStorage.setItem(KEY, "1"); } catch { /* private window */ } };
export const resetStarters = (): void => { try { window.localStorage.removeItem(KEY); } catch { /* private window */ } };

let typing = false;
const subs = new Set<(v: boolean) => void>();
export const setTyping = (v: boolean): void => { if (v !== typing) { typing = v; subs.forEach((f) => f(v)); } };
export function useTyping(): boolean {
  const [v, setV] = useState(typing);
  useEffect(() => { subs.add(setV); return () => { subs.delete(setV); }; }, []);
  return v;
}

// 12 Nov 2026 (Madhav, a screenshot of the voice screen: "there is no chat option and also couldn't access all the options"): the floating
// bar sat on top of the voice screen's own orb, its state and its "type instead" button. While the big voice screen is showing, the bar
// steps aside the same way it does for typing; it is back the moment he ends voice, opens the conversation or leaves Ask.
let stage = false;
const stageSubs = new Set<(v: boolean) => void>();
export const setVoiceStage = (v: boolean): void => { if (v !== stage) { stage = v; stageSubs.forEach((f) => f(v)); } };
export function useVoiceStage(): boolean {
  const [v, setV] = useState(stage);
  useEffect(() => { stageSubs.add(setV); return () => { stageSubs.delete(setV); }; }, []);
  return v;
}

// The room the floating bar takes at the bottom of a place: the bar (64), the orb standing above it (26) and a little air. A screen that
// keeps something at its bottom edge (Ask's typing box) leaves this much under it, plus the phone's own bottom inset.
export const BAR_ROOM = 64 + 26 + 10;

// 7 Nov 2026 (Madhav): the orb on the bar takes you to Ask; pressed again while already on Ask, it starts the voice. The press is handed
// on synchronously (the microphone must be opened inside the tap itself for Safari), to whoever is listening: the Ask screen.
const orbSubs = new Set<() => void>();
export const onOrbPress = (f: () => void): (() => void) => { orbSubs.add(f); return () => { orbSubs.delete(f); }; };
export const pressOrb = (): boolean => { orbSubs.forEach((f) => f()); return orbSubs.size > 0; };
