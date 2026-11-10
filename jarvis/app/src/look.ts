// The "new look" switch (Madhav, 31 Oct 2026: "Time to give it a proper, premium and precise look"; gates 1 and 2 passed the same night).
// The redesign lives in app/new/ (its own address, /new/...) beside the classic tabs; this device remembers the choice; classic stays the default until the new look
// is better on every screen it replaces. Nothing in the classic app changes while the switch is off.
import * as SecureStore from "expo-secure-store";
import { useEffect, useState } from "react";
import { Platform } from "react-native";

export type Look = "classic" | "new";
const KEY = "ananta_look";
// 8 Nov 2026 (the TestFlight build): the iPhone app starts in the new look, the one Madhav uses; the website keeps classic as its default
// 10 Nov 2026 (the redesign, "one look at the end"): the owner sees the redesign on every device; the classic tabs stay only for guests
let current: Look = "new";
let loaded = false;
const subs = new Set<() => void>();

export async function loadLook(): Promise<Look> {
  if (loaded) return current;
  current = "new";
  loaded = true;
  return current;
}
export const getLook = () => current;
export async function setLook(l: Look) {
  current = l;
  loaded = true;
  try { await SecureStore.setItemAsync(KEY, l); } catch { /* */ }
  subs.forEach((f) => f());
}
export function useLook(): Look {
  const [l, setL] = useState<Look>(current);
  useEffect(() => {
    const f = () => setL(current);
    subs.add(f);
    loadLook().then(() => setL(current));
    return () => { subs.delete(f); };
  }, []);
  return l;
}
export const newHome = "/new/home";
