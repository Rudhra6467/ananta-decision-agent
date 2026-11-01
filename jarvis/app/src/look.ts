// The "new look" switch (Madhav, 31 Oct 2026: "Time to give it a proper, premium and precise look"; gates 1 and 2 passed the same night).
// The redesign lives in app/(new)/ beside the classic tabs; this device remembers the choice; classic stays the default until the new look
// is better on every screen it replaces. Nothing in the classic app changes while the switch is off.
import * as SecureStore from "expo-secure-store";
import { useEffect, useState } from "react";

export type Look = "classic" | "new";
const KEY = "ananta_look";
let current: Look = "classic";
let loaded = false;
const subs = new Set<() => void>();

export async function loadLook(): Promise<Look> {
  if (loaded) return current;
  try { const v = await SecureStore.getItemAsync(KEY); if (v === "new" || v === "classic") current = v; } catch { /* */ }
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
export const newHome = "/(new)/today";
