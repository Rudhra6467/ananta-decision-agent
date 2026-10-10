// Two palettes as tokens (plan 2.4a, D7). Light: the calm brokerage look. Bat Mode: a charcoal base, slightly lighter cards,
// muted grays and a soft yellow accent. Every screen reads its colours from C at render time, so switching the theme swaps the
// values inside C and redraws the app (see app/_layout.tsx). tests/test_app_theme.py checks contrast (4.5:1 for text).
import * as SecureStore from "expo-secure-store";
import { useEffect, useState } from "react";

const LIGHT = {
  bg: "#F5F6F8", card: "#FFFFFF", card2: "#F0F2F5", line: "#E4E7EC", text: "#101828", dim: "#5D6679", faint: "#98A2B3",
  accent: "#2952CC", accentSoft: "#E8EEFC",
  good: "#06804C", goodSoft: "#E6F4EC", bad: "#C8332B", badSoft: "#FBEAE9", warn: "#B54708", warnSoft: "#FEF4E6",
  goodDeep: "#05603A", badDeep: "#912018", warnDeep: "#7A2E0E",
  // "ink": the dark pills and caption bars (tour, toast, listening); onInk: text on ink or on any filled colour
  ink: "#101828", onInk: "#FFFFFF", inkDim: "#C9D3F5", inkBtn: "#33405E",
  ok: "#2952CC", ema20: "#2952CC", ema50: "#98A2B3", level: "#5B7083", level2: "#8A6D3B",
  shades: ["#2952CC", "#4A6FD6", "#6B8BDF", "#8CA6E8", "#ADC1F0", "#C6D4F5", "#D7E1F8", "#E3EAFA", "#EDF2FC", "#F3F6FD"],
  bar: "dark" as "dark" | "light",
};
export type Palette = typeof LIGHT;

const BAT: Palette = {
  bg: "#141518", card: "#1D1F23", card2: "#26292E", line: "#33363C", text: "#ECEAE6", dim: "#A9ACB2", faint: "#7E828A",
  accent: "#F2CF66", accentSoft: "#3A331C",
  good: "#5CCB92", goodSoft: "#183126", bad: "#F2796F", badSoft: "#3A1F1F", warn: "#F2A65A", warnSoft: "#3A2A18",
  goodDeep: "#8FE0B6", badDeep: "#F7A8A1", warnDeep: "#F7C48F",
  ink: "#ECEAE6", onInk: "#141518", inkDim: "#4B4F57", inkBtn: "#CBC8C2",
  ok: "#F2CF66", ema20: "#F2CF66", ema50: "#7E828A", level: "#8C96A3", level2: "#B59A62",
  shades: ["#F2CF66", "#D9BA5E", "#BFA457", "#A68F4F", "#8C7A47", "#73653F", "#5E5437", "#4A4430", "#3A3628", "#2E2B22"],
  bar: "light",
};

export type ThemeName = "light" | "bat";
export const PALETTES: Record<ThemeName, Palette> = { light: LIGHT, bat: BAT };
export const C: Palette = { ...LIGHT, shades: [...LIGHT.shades] };

const KEY = "ananta_theme";
let current: ThemeName = "light";
let version = 0;
const subs = new Set<() => void>();

function apply(n: ThemeName) {
  Object.assign(C, PALETTES[n], { shades: [...PALETTES[n].shades] });
  current = n;
  version += 1;
  subs.forEach((f) => f());
}

// The device remembers the choice; it is read before the first screen is drawn, so there is no flash of the wrong theme.
export const deviceTheme = (): ThemeName | null => {
  try { const s = (SecureStore as any).getItem?.(KEY); return s === "bat" || s === "light" ? s : null; } catch { return null; }
};
{ const s = deviceTheme(); if (s) apply(s); }

export const themeName = () => current;
export function setTheme(n: ThemeName, save = true) {
  if (save) SecureStore.setItemAsync(KEY, n).catch(() => {});
  if (n !== current) apply(n);
}
// the root redraws the app when this changes
export function useThemeVersion() {
  const [v, setV] = useState(version);
  useEffect(() => { const f = () => setV(version); subs.add(f); return () => { subs.delete(f); }; }, []);
  return v;
}

// A table of colours built at the top of a file (a style sheet, a status → colour map) would keep the colours of the theme it
// was built in. live() rebuilds it on first use after each theme change, so it always matches the current theme.
export function live<T extends object>(make: () => T): T {
  let v = -1;
  let cache: T;
  const get = (): any => { if (v !== version) { cache = make(); v = version; } return cache; };
  return new Proxy({} as T, {
    get: (_t, k) => get()[k],
    has: (_t, k) => k in get(),
    ownKeys: () => Reflect.ownKeys(get()),
    getOwnPropertyDescriptor: (_t, k) => { const d = Object.getOwnPropertyDescriptor(get(), k); return d ? { ...d, configurable: true } : undefined; },
  });
}

// Ratings are words, not colours; only a soft tint so the list stays quiet.
export const ratingColor: Record<string, string> = {
  get STRONG() { return C.good; }, get OK() { return C.dim; }, get WEAK() { return C.warn; }, get OUT() { return C.bad; },
};
export const ratingWord: Record<string, string> = { STRONG: "Strong", OK: "Steady", WEAK: "Weak", OUT: "Out" };
export const coinColor: Record<string, string> = {}; // kept for old imports: every coin uses the text colour
export const pnlColor = (x?: number | null) => (x == null || Math.abs(x) < 0.005 ? C.dim : x > 0 ? C.good : C.bad);
export const COIN_NAME: Record<string, string> = {
  BTC: "Bitcoin", ETH: "Ethereum", SOL: "Solana", ADA: "Cardano", DOGE: "Dogecoin", AVAX: "Avalanche",
  BCH: "Bitcoin Cash", LINK: "Chainlink", LTC: "Litecoin", XRP: "XRP",
};

// The public front page (src/landing.tsx): black and gold, the Bat palette fixed so every visitor sees the same page.
export const LANDING = {
  bg: "#08090B", surface: "#121418", surface2: "#1A1D22", line: "#262930", line2: "#3A3D44", text: "#F2F0EA", dim: "#9A9DA4", faint: "#6E727A",
  gold: "#F2CF66", goldSoft: "#2B2614", onGold: "#141518", good: "#5CCB92", bad: "#F2796F", phone: "#1B1D21", phoneLine: "#34373D",
};
