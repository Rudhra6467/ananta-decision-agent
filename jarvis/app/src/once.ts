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
