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
// both markets open the same four tabs; the market decides which backend the screens read (src/api.ts routeFor)
export const homeOf = (_m: Market | null) => "/(tabs)/today";
export const MARKET_NAME: Record<Market, string> = { crypto: "Crypto", india: "Indian market" };

// The words each market uses on the same screens (first pass, 23 Oct). Crypto's are the originals; India's say the Indian thing.
export type Words = { coin: string; coins: string; Coins: string; exchange: string; account_title: string; account_say: string; account_ccy: "USD" | "CAD" | "INR"; next_decision: string;
  next_line: string; dial_open_why: string; dial_closed_why: string; wake: string; market_name: string; trend_short: string; rule_who: string; dial_label: string; dial_for: string;
  dial_reads: string; dial_open_market: string; dial_closed_market: string; dial_feeds: string; marked_at: string; lab_note: string; lab_title: string; whole_market_sub: string;
  symbol_hint: string; ready_verb_open: string; ready_verb_closed: string };
const WORDS: Record<Market, Words> = {
  crypto: { coin: "coin", coins: "coins", Coins: "Coins", exchange: "NDAX", account_title: "The account · $500 NDAX book · paper, real NDAX prices",
    next_line: "next decision at the daily close", trend_short: "1h", rule_who: "Bitcoin", dial_label: "Trend dial · crypto", dial_for: "the trend dial, Ananta's market rule for crypto",
    dial_reads: "Bitcoin's daily close decides whether buying is allowed.", dial_open_market: "Bitcoin is above its 50- and 200-day averages.",
    dial_closed_market: "Bitcoin closed below its averages: cash is the position until it crosses back.", dial_feeds: "Feeds the account's core and the edge sleeve",
    marked_at: "Marked at the NDAX bid", lab_note: "The lab's paper books are in US$ and live under Details › Lab. They never touch the account.", lab_title: "The lab's paper books · US$",
    whole_market_sub: "every coin Ananta watches", symbol_hint: "Search any coin (e.g. SUI, PEPE)", ready_verb_open: "Buying allowed", ready_verb_closed: "No new buys",
    account_say: "the 500 dollar NDAX book, paper money at real NDAX prices, in Canadian dollars", account_ccy: "CAD", next_decision: "The next decision comes at the daily close",
    dial_open_why: "Dial open: buys only what crosses its averages. Next decision at the close.", dial_closed_why: "Dial closed: no new buys, cash is the position. Next decision at the close.",
    wake: "I wake when a coin enters a zone or a setup fires.", market_name: "Crypto" },
  india: { coin: "stock", coins: "stocks", Coins: "Stocks", exchange: "NSE", account_title: "The account · ₹60,000 India book · paper, real NSE prices",
    next_line: "next decisions at the open (09:15 IST)", trend_short: "day", rule_who: "Nifty", dial_label: "Guardrails · India", dial_for: "the guardrails, Ananta's survival rule for India: 5% in a day stops the day, 22% below the peak pauses new entries",
    dial_reads: "The guardrails decide whether entries are allowed; the Nifty trend is the situation each family reads.", dial_open_market: "No guardrail has fired: every family decides after the close.",
    dial_closed_market: "A guardrail has fired: no new entries until it lifts.", dial_feeds: "Guards the ₹60,000 line and the stock book",
    marked_at: "Marked at the NSE close", lab_note: "The stock book is the lab at research scale (₹50,000 a trade) under Details › Lab. It never touches the account.", lab_title: "The stock paper book · ₹50,000 a trade",
    whole_market_sub: "the liquid 250 Ananta decides on", symbol_hint: "Search any stock (e.g. INFY, HDFCBANK)", ready_verb_open: "Entries allowed", ready_verb_closed: "No new entries",
    account_say: "the sixty thousand rupee India book, paper money at real NSE prices, in rupees", account_ccy: "INR", next_decision: "The next decisions come at the open, nine fifteen IST",
    dial_open_why: "No guardrail has fired: the index line and the stock book trade on paper. Next decisions at the open (09:15 IST).", dial_closed_why: "A guardrail has fired: no new entries until it lifts.",
    wake: "I decide once a session, after the close, on the liquid 250.", market_name: "Indian market" },
};
export const W = (): Words => WORDS[current ?? "crypto"];
