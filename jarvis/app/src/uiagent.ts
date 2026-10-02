// The only way Ananta moves the app. Each action reports whether it really happened, so Ananta never claims a move it did not make.
import { router } from "expo-router";
import { getScreen } from "./context";

export type UiAction = { do: "go_to" | "open" | "back"; target?: string; label?: string };
export type UiResult = { action: UiAction; ok: boolean; landed?: string; error?: string };

const TABS: Record<string, { path: string; tab?: string }> = {
  home: { path: "/(tabs)/today" }, markets: { path: "/(tabs)/markets" },
  portfolio: { path: "/(tabs)/portfolio", tab: "portfolio" }, "portfolio:explorer": { path: "/(tabs)/portfolio", tab: "explorer" },
  "portfolio:mine": { path: "/(tabs)/portfolio", tab: "mine" }, ananta: { path: "/(tabs)/ask" },
  evidence: { path: "/(tabs)/evidence", tab: "collected" }, "evidence:forwarded": { path: "/(tabs)/evidence", tab: "forwarded" },
  cockpit: { path: "/(tabs)/cockpit" }, mandate: { path: "/mandate" }, testlab: { path: "/testlab" },
};

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function expected(t: string): (s: any) => boolean {
  if (t.startsWith("coin:")) return (s) => s?.screen === "coin" && s?.coin === t.slice(5);
  if (t.startsWith("trade:")) return (s) => s?.screen === "trade" && s?.id === t.slice(6);
  const [screen, tab] = t.split(":");
  const name = screen === "portfolio" && tab === "explorer" ? "explorer_trades" : screen === "portfolio" && tab === "mine" ? "manual_book" : screen;
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
      if (a.do === "back") {
        if (router.canGoBack()) router.back(); else router.navigate("/(tabs)/today");
        await sleep(400);
        out.push({ action: a, ok: true, landed: getScreen()?.label });
        continue;
      }
      const t = a.target ?? "";
      if (t.startsWith("coin:")) router.push(`/coin/${t.slice(5)}`);
      else if (t.startsWith("trade:")) router.push(`/trade/${t.slice(6)}`);
      else if (TABS[t]) {
        const d = TABS[t];
        router.navigate(d.tab ? ({ pathname: d.path, params: { tab: d.tab, t: String(Date.now()) } } as any) : (d.path as any));
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
