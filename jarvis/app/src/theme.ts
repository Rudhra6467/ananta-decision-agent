// One calm palette (brokerage style): neutral surfaces, one blue accent, green/red only for money going up/down.
export const C = {
  bg: "#F5F6F8", card: "#FFFFFF", card2: "#F0F2F5", line: "#E4E7EC", text: "#101828", dim: "#667085", faint: "#98A2B3",
  accent: "#2952CC", accentSoft: "#E8EEFC",
  good: "#078A52", goodSoft: "#E6F4EC", bad: "#C8332B", badSoft: "#FBEAE9", warn: "#B54708", warnSoft: "#FEF4E6",
  ok: "#2952CC", ema20: "#2952CC", ema50: "#98A2B3",
};
// Ratings are words, not colours; only a soft tint so the list stays quiet.
export const ratingColor: Record<string, string> = { STRONG: C.good, OK: C.dim, WEAK: C.warn, OUT: C.bad };
export const ratingWord: Record<string, string> = { STRONG: "Strong", OK: "Steady", WEAK: "Weak", OUT: "Out" };
export const coinColor: Record<string, string> = {}; // kept for old imports: every coin uses the text colour
export const pnlColor = (x?: number | null) => (x == null || Math.abs(x) < 0.005 ? C.dim : x > 0 ? C.good : C.bad);
export const COIN_NAME: Record<string, string> = {
  BTC: "Bitcoin", ETH: "Ethereum", SOL: "Solana", ADA: "Cardano", DOGE: "Dogecoin", AVAX: "Avalanche",
  BCH: "Bitcoin Cash", LINK: "Chainlink", LTC: "Litecoin", XRP: "XRP",
};
