// One app, one login, one place (Madhav, 22 Oct): after sign-in the owner picks a market, and the app loads that market's pack —
// its screens, its backend, its Ask and its voice. Crypto keeps everything it has; India reads the India service through
// /india on the same server (api.livetrading247.com/india -> the India service on the Mac), with the same sign-in token.
// The two backends never share data; the app is the one place. The choice lives on this device; "Switch market" changes it.
import { useEffect, useState } from "react";
import * as SecureStore from "expo-secure-store";

export type Market = "crypto" | "india";
const KEY = "ananta_market";
let current: Market | null = null;
let loaded = false;
const subs = new Set<() => void>();

export async function loadMarket(): Promise<Market | null> {
  if (loaded) return current;
  try {
    const v = await SecureStore.getItemAsync(KEY);
    current = v === "india" || v === "crypto" ? v : null;
  } catch { current = null; }
  loaded = true;
  return current;
}
export const getMarket = () => current;
export async function setMarket(m: Market) {
  current = m;
  loaded = true;
  try { await SecureStore.setItemAsync(KEY, m); } catch { /* the choice still holds for this session */ }
  subs.forEach((f) => f());
}
export async function clearMarket() {
  current = null;
  try { await SecureStore.deleteItemAsync(KEY); } catch { /* nothing to clear */ }
  subs.forEach((f) => f());
}
export function useMarket(): Market | null {
  const [, bump] = useState(0);
  useEffect(() => { const f = () => bump((n) => n + 1); subs.add(f); loadMarket().then(f); return () => { subs.delete(f); }; }, []);
  return current;
}
// where each market's home is; a route under /india belongs to the India pack
export const homeOf = (m: Market | null) => (m === "india" ? "/india/today" : "/(tabs)/today");
export const MARKET_NAME: Record<Market, string> = { crypto: "Crypto", india: "Indian market" };
