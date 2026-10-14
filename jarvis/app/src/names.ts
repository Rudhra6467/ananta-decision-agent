// Plain words (plan 2.3): internal codes (E4, H07, T3, P02...) never reach a screen. The service rewrites its sentences; for the
// few places a screen shows an identifier it was sent, nm() gives the display name from the one dictionary (/v3/names).
import { api } from "./api";

let N: Record<string, string> = {
  E1: "Pullback in an uptrend", E2: "Breakout after a quiet period", E3: "Bounce at support", E4: "Momentum continuation",
  E5: "Squeeze breakout", E6: "Deep dip", T3: "Trend portfolio", T30: "30-coin tier", H07: "Short dip trade", V02: "Bitcoin 50-day rule",
};
let loaded = false;

let tried = 0;
export async function loadNames() {
  if (loaded || Date.now() - tried < 30000) return;     // at most one try every 30 s until it works
  tried = Date.now();
  try {
    const r = await api<{ names: Record<string, string> }>("/v3/names");
    N = { ...N, ...(r?.names ?? {}) };
    loaded = true;
  } catch {}
}

const KIND: Record<string, string> = { E: "Setup", H: "Idea", V: "Checked rule", P: "Risk rule", T: "Tier" };

export function nm(code?: string | null): string {
  if (code == null || code === "") return "";
  if (!loaded) loadNames();                             // first use after sign-in fetches the full dictionary
  const c = String(code);
  if (N[c]) return N[c].replace(/\s*\([^)]*\)\s*$/, "");
  let m = c.match(/^explorer:(\w+)$/i);
  if (m) return `Explorer: ${nm(m[1])}`;
  m = c.match(/^TK(\d+)$/);
  if (m) return `Repair ticket ${m[1]}`;
  m = c.match(/^([EHVPT])(\d{1,2})$/);
  if (m) return `${KIND[m[1]]} ${Number(m[2])}`;
  return c;
}
