// The only way Ananta moves the app. Each action reports whether it really happened, so Ananta never claims a move it did not make.
import { router } from "expo-router";
import { api } from "./api";
import { getScreen, goTab } from "./context";
import { clearSpot, focusSpot, requestSheet, scroll } from "./spotlight";
import { setMarket } from "./market";

export type UiAction = { do: "go_to" | "open" | "back" | "scroll" | "market"; target?: string; dir?: "up" | "down" | "top" | "bottom"; label?: string };
export type UiResult = { action: UiAction; ok: boolean; landed?: string; error?: string };

const TABS: Record<string, { path: string; tab?: string; sub?: string }> = {
  home: { path: "/(tabs)/today" }, markets: { path: "/(tabs)/watchlists" },
  "markets:markets": { path: "/(tabs)/watchlists", tab: "markets" }, "ananta:now": { path: "/(tabs)/ask", tab: "now" },   // Oct 16: section voice
  // Oct 15: the Books tab folded into Home (the account's trades) and Markets › Ananta market (the rest)
  books: { path: "/(tabs)/today" }, portfolio: { path: "/(tabs)/watchlists", tab: "ananta", sub: "portfolio" },
  "portfolio:explorer": { path: "/(tabs)/watchlists", tab: "ananta", sub: "explorer" }, "portfolio:mine": { path: "/(tabs)/watchlists", tab: "ananta", sub: "mine" },
  "portfolio:lab": { path: "/(tabs)/watchlists", tab: "ananta", sub: "lab" }, ananta: { path: "/(tabs)/ask" },
  evidence: { path: "/lab", tab: "collected" }, "evidence:forwarded": { path: "/lab", tab: "forwarded" },
  cockpit: { path: "/(tabs)/cockpit" }, mandate: { path: "/mandate" }, testlab: { path: "/testlab" },
  jarvis: { path: "/jarvis" }, missed: { path: "/missed" },
  // 25 Oct (flags 96/97, India voice navigation): My flags, the nightly reconstruction, More by its own name
  flags: { path: "/flags" }, reconstruction: { path: "/reconstruction" }, more: { path: "/(tabs)/cockpit" },
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function expected(t: string): (s: any) => boolean {
  if (t.startsWith("coin:")) return (s) => s?.screen === "coin" && s?.coin === t.slice(5);
  if (t.startsWith("trade:")) return (s) => s?.screen === "trade" && s?.id === t.slice(6);
  if (t.startsWith("jtrade:")) return (s) => s?.screen === "jtrade" && s?.id === t.slice(7);
  if (t.startsWith("sheet:") || t.startsWith("market:")) return (s) => s?.screen === "home";
  if (t === "more") return (s) => s?.screen === "cockpit";
  const [screen, tab] = t.split(":");
  const name = screen === "portfolio" && tab === "explorer" ? "explorer_trades" : screen === "portfolio" && tab === "mine" ? "manual_book"
    : screen === "portfolio" && tab === "lab" ? "ananta_market" : screen === "books" ? "home" : screen;
  return (s) => s?.screen === name || (screen === "evidence" && s?.screen === "evidence");
}

async function confirm(t: string): Promise<boolean> {
  const ok = expected(t);
  for (let i = 0; i < 20; i++) {                       // up to 2 s for the screen to report itself
    if (ok(getScreen())) return true;
    await sleep(100);
  }
  return false;
}

export async function run(actions: UiAction[] = []): Promise<UiResult[]> {
  const out: UiResult[] = [];
  for (const a of actions) {
    try {
      if (a.do === "scroll") {
        const ok = scroll(a.dir ?? "down");
        out.push({ action: a, ok, landed: getScreen()?.label, error: ok ? undefined : "this screen does not scroll" });
        continue;
      }
      if (a.do === "back") {
        if (router.canGoBack()) router.back(); else goTab("/(tabs)/today");
        await sleep(400);
        out.push({ action: a, ok: true, landed: getScreen()?.label });
        continue;
      }
      const t = a.target ?? "";
      if (a.do === "market" || t.startsWith("market:")) {           // "switch to crypto" / "switch to India": the app reloads that market's Home
        const m = t.split(":")[1] === "india" ? "india" : "crypto";
        await setMarket(m);
        goTab({ pathname: "/(tabs)/today", params: { t: String(Date.now()) } } as any);
        const ok = await confirm(t);
        out.push({ action: a, ok, landed: getScreen()?.label, error: ok ? undefined : "the market did not switch" });
        continue;
      }
      if (t.startsWith("sheet:")) {                                 // India Home's boxes and cards: go Home, then open the sheet
        if (getScreen()?.screen !== "home") goTab({ pathname: "/(tabs)/today", params: { t: String(Date.now()) } } as any);
        const ok = await confirm(t);
        if (ok) { await sleep(300); requestSheet(t.slice(6)); }
        out.push({ action: a, ok, landed: getScreen()?.label, error: ok ? undefined : "Home did not open" });
        continue;
      }
      if (t.startsWith("coin:")) router.push(`/coin/${t.slice(5)}`);
      else if (t.startsWith("trade:")) router.push(`/trade/${t.slice(6)}`);
      else if (t.startsWith("jtrade:")) router.push(`/jtrade/${t.slice(7)}`);
      else if (TABS[t]) {
        const d = TABS[t];
        (d.path.startsWith("/(tabs)") ? goTab : router.navigate)(d.tab ? ({ pathname: d.path, params: { tab: d.tab, ...(d.sub ? { sub: d.sub } : {}), t: String(Date.now()) } } as any) : (d.path as any));
      } else {
        out.push({ action: a, ok: false, error: `unknown place ${t}` });
        continue;
      }
      const ok = await confirm(t);
      out.push({ action: a, ok, landed: getScreen()?.label, error: ok ? undefined : "the screen did not open" });
    } catch (e: any) {
      out.push({ action: a, ok: false, error: e?.message ?? String(e) });
    }
  }
  return out;
}

// Request #73 (Oct 20): tell the service what the screen really did for an answer (each move: target, ok, where it landed; the
// spots it was to light), so "it says one thing and the app shows another" is measured, not guessed. Fire-and-forget: never awaited.
export function report(answerId: string | undefined, res: UiResult[], points: { spot: string }[] = []) {
  if (!answerId || !res.length) return;
  const results = res.map((x) => ({ target: x.action.target ?? `${x.action.do}${x.action.dir ? `:${x.action.dir}` : ""}`, ok: x.ok, landed: x.landed ?? "" }));
  api("/v3/voice/ui_result", { answer_id: answerId, results, spots: (points ?? []).map((p) => p.spot) }, 8000, true).catch(() => {});
}

export const sentences = (t: string) => (t || "").split(/(?<=[.!?])\s+/).map((x) => x.trim()).filter(Boolean);

// Point at things in time with the words: spoken (voice: waits until the voice has finished or was stopped)
// or paced by reading speed (text).
export async function pointAlong(answer: string, points: { spot: string; sentence: number }[] = [],
  speak?: (parts: string[], onPart: (i: number) => void) => Promise<unknown> | void) {
  const parts = sentences(answer);
  const at = (i: number) => points.find((p) => p.sentence === i)?.spot;
  if (speak) {
    // Each highlight belongs to its sentence: when the voice reaches a sentence with nothing to point at, the previous item
    // stops glowing (it used to stay lit while the next items in a list were being read out).
    let lit: string | null = null;
    try {
      await speak(parts, (i) => {
        const s = at(i);
        if (s && s !== lit) { lit = s; focusSpot(s); } else if (!s && lit) { lit = null; clearSpot(); }
      });
    } finally { if (points.length) setTimeout(clearSpot, 1500); }
    return;
  }
  if (!points.length) return;
  for (let i = 0; i < parts.length; i++) {
    const s = at(i);
    if (s) await focusSpot(s); else clearSpot();
    await new Promise((r) => setTimeout(r, Math.max(1600, parts[i].split(/\s+/).length * 280)));
  }
  setTimeout(clearSpot, 2500);
}

// Guided tour: move, point and talk, step by step. Stop / Skip come from the caption bar.
export type TourStep = { ui?: UiAction; spot?: string; say: string };
export async function playTour(steps: TourStep[], speakFn: (text: string) => Promise<unknown>, keepGoing: () => boolean = () => true) {
  const { setTour, takeTourCommand } = await import("./context");
  takeTourCommand();
  for (let i = 0; i < steps.length; i++) {
    if (!keepGoing()) break;                                   // voice mode was interrupted or ended
    const st = steps[i];
    setTour({ active: true, i: i + 1, n: steps.length, text: st.say });
    if (st.ui) await run([st.ui]);
    if (st.spot) await focusSpot(st.spot);
    const pending = takeTourCommand();                         // Skip / Stop pressed while the screen was moving
    if (pending === "stop" || !keepGoing()) break;
    if (pending === "next") continue;
    await speakFn(st.say);
    const c = takeTourCommand();
    if (c === "stop") break;
  }
  clearSpot();
  setTour({ active: false, i: 0, n: 0, text: "" });
}
