// Home's parts (plan 3.1), shared by Madhav's Home and a visitor's: the value card with its Brief button, The market as
// slides (coins with a + , then the market rule chart), findings in simple words with details on tap, and the
// "Start trading and set up Ananta" empty state.
import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { api } from "./api";
import { ExplainSheet, showToast } from "./blocks";
import { LineChart, Spark } from "./charts";
import { askAbout, goTab } from "./context";
import { C, COIN_NAME, pnlColor } from "./theme";
import { Btn, Card, Divider, T, pct, price, usd } from "./ui";
import { useData } from "./useData";

export function hello(name?: string, sir?: boolean) {
  const h = new Date().getHours();                       // the phone's own clock: local time for everyone
  const part = h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
  return sir ? `${part}, sir` : `${part}${name ? `, ${name}` : ""}`;
}

// ---- value card with the Brief button ----
export function ValueCard({ label, value, change, sub, series, start }: {
  label: string; value: number | null; change?: number | null; sub?: string; series?: number[]; start?: number;
}) {
  const [brief, setBrief] = useState(false);
  return (
    <Card>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={{ color: C.dim, fontSize: 13, flex: 1 }}>{label}</Text>
        <Pressable onPress={() => setBrief(true)} hitSlop={8} accessibilityRole="button" accessibilityLabel="Brief"
          style={{ flexDirection: "row", alignItems: "center", gap: 4, borderRadius: 999, borderWidth: 1, borderColor: C.line, paddingHorizontal: 10, paddingVertical: 4 }}>
          <Text style={{ color: C.accent, fontSize: 12 }}>✦</Text>
          <Text style={{ color: C.accent, fontWeight: "700", fontSize: 13 }}>Brief</Text>
        </Pressable>
      </View>
      <View style={{ flexDirection: "row", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
        <Text style={{ color: C.text, fontSize: 32, fontWeight: "700", letterSpacing: -0.6 }}>{value == null ? "…" : usd(value, 0)}</Text>
        {change != null ? <Text style={{ color: pnlColor(change), fontSize: 15, fontWeight: "600" }}>{change >= 0 ? "+" : "-"}${Math.abs(change).toFixed(0)} since start</Text> : null}
      </View>
      {sub ? <T dim small>{sub}</T> : null}
      {series && series.length > 2 ? (
        <View style={{ marginTop: 8 }}>
          <LineChart height={64} showAxis={false} series={[{ data: series, color: C.accent, fill: true }]}
            refs={start != null ? [{ value: start, color: C.dim, label: "Start" }] : []} />
        </View>
      ) : null}
      <ExplainSheet open={brief} onClose={() => setBrief(false)} title="Which brief?">
        <BriefChoice title="Market brief" sub="What the market is doing now and what Ananta is watching"
          q="Give me the market brief: what is the market doing and what are you watching?" close={() => setBrief(false)} />
        <BriefChoice title="Portfolio brief" sub="Your money, your open trades and what changed"
          q="Give me my portfolio brief: how is my money doing, my open trades, and what changed?" close={() => setBrief(false)} />
      </ExplainSheet>
    </Card>
  );
}

function BriefChoice({ title, sub, q, close }: { title: string; sub: string; q: string; close: () => void }) {
  return (
    <Pressable onPress={() => { close(); goTab({ pathname: "/(tabs)/ask", params: { q, t: String(Date.now()) } } as any); }}
      style={({ pressed }) => ({ borderWidth: 1, borderColor: C.line, borderRadius: 12, padding: 14, gap: 2, opacity: pressed ? 0.7 : 1 })}>
      <Text style={{ color: C.text, fontWeight: "700", fontSize: 16 }}>{title} ›</Text>
      <Text style={{ color: C.dim, fontSize: 13 }}>{sub}</Text>
    </Pressable>
  );
}

// ---- The market, as slides ----
export function MarketSlides({ coins, market, more = true }: { coins: any[]; market?: any; more?: boolean }) {
  // two slides, one shown at a time (a sideways swipe here would fight the tabs' own swipe): the coins, then the market rule
  const [page, setPage] = useState(0);
  const hasRule = !!market && !market.error;
  return (
    <View style={{ gap: 8 }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 16, flex: 1 }}>The market</Text>
        {hasRule ? (
          <View style={{ flexDirection: "row", backgroundColor: C.card2, borderRadius: 999, padding: 2 }}>
            {["Coins", "Market rule"].map((l, i) => (
              <Pressable key={l} onPress={() => setPage(i)} accessibilityRole="tab" accessibilityState={{ selected: page === i }}
                style={{ borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4, backgroundColor: page === i ? C.card : "transparent" }}>
                <Text style={{ color: page === i ? C.accent : C.dim, fontSize: 12, fontWeight: "700" }}>{l}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}
      </View>
      {page === 0 || !hasRule ? <CoinsSlide coins={coins} more={more} /> : <MarketRule mk={market} />}
      {hasRule ? (
        <View style={{ flexDirection: "row", justifyContent: "center", gap: 6 }}>
          {[0, 1].map((i) => <Pressable key={i} onPress={() => setPage(i)} hitSlop={8}><View style={{ width: 6, height: 6, borderRadius: 3, backgroundColor: page === i ? C.accent : C.line }} /></Pressable>)}
        </View>
      ) : null}
    </View>
  );
}

function CoinsSlide({ coins, more }: { coins: any[]; more: boolean }) {
  const shown = coins.slice(0, 6);
  return (
    <Card>
      {shown.length === 0 ? <T dim>No coins yet. Pick the coins you care about in Watchlists.</T> : null}
      {shown.map((c, i) => (
        <View key={c.coin}>
          {i ? <Divider /> : null}
          <CoinLine c={c} />
        </View>
      ))}
      {more && coins.length > 0 ? (
        <Text onPress={() => router.push("/coins")} style={{ color: C.accent, fontWeight: "700", textAlign: "center", paddingTop: 6 }}>Load more ›</Text>
      ) : null}
    </Card>
  );
}

// one coin: tap for its trading page, + to watch it or trade it
export function CoinLine({ c }: { c: any }) {
  const [plus, setPlus] = useState(false);
  const name = c.name ?? COIN_NAME[c.coin] ?? c.coin;
  return (
    <>
      <Pressable onPress={() => router.push(`/coin/${c.coin}`)} delayLongPress={350}
        onLongPress={() => askAbout({ screen: "coin", coin: c.coin, label: `${name}` }, `What is happening with ${name}?`)}
        style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10, opacity: pressed ? 0.6 : 1 })}>
        <View style={{ flex: 1 }}>
          <Text style={{ color: C.text, fontSize: 15, fontWeight: "700" }}>{name}</Text>
          <Text style={{ color: C.dim, fontSize: 12 }}>{c.coin}{c.trend_1h ? ` · 1h ${String(c.trend_1h).toLowerCase()}` : ""}</Text>
        </View>
        {c.spark?.length ? <Spark data={c.spark} color={pnlColor(c.day_pct)} /> : null}
        <View style={{ alignItems: "flex-end", minWidth: 82 }}>
          <Text style={{ color: C.text, fontSize: 14, fontWeight: "600" }}>{price(c.price)}</Text>
          <Text style={{ color: pnlColor(c.day_pct), fontSize: 12, fontWeight: "600" }}>{pct(c.day_pct)}</Text>
        </View>
        <Pressable onPress={() => setPlus(true)} hitSlop={8} accessibilityLabel={`Watch or trade ${name}`}
          style={{ width: 30, height: 30, borderRadius: 15, borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" }}>
          <Text style={{ color: C.accent, fontSize: 18, fontWeight: "700", marginTop: -2 }}>+</Text>
        </Pressable>
      </Pressable>
      <PlusSheet coin={c.coin} name={name} open={plus} onClose={() => setPlus(false)} />
    </>
  );
}

const MODES: [string, string, string][] = [
  ["tell", "Tell me", "Ananta lets you know when it fires"],
  ["ask", "Ask me first", "Ananta sends a request; nothing is bought without your yes"],
  ["auto", "Auto", "Ananta takes the paper trade and tells you"],
];

export function PlusSheet({ coin, name, open, onClose }: { coin: string; name: string; open: boolean; onClose: () => void }) {
  const [watch, setWatch] = useState(false);
  const add = async (mode: string) => {
    try {
      await api("/v3/watches/mine", { coins: [coin], mode });
      showToast(`Watching ${name} ✓`);
      onClose();
      setWatch(false);
    } catch (e: any) { showToast(e?.message ?? "Could not add the watch"); }
  };
  return (
    <ExplainSheet open={open} onClose={() => { setWatch(false); onClose(); }} title={name}>
      {!watch ? (
        <>
          <Btn label="Add to watch" onPress={() => setWatch(true)} />
          <Btn label="Trade manually" kind="secondary" onPress={() => { onClose(); router.push({ pathname: "/coin/[sym]", params: { sym: coin, trade: "buy" } } as any); }} />
        </>
      ) : (
        <>
          <T dim>Ananta watches {name} for a pullback into a supported zone (the best-supported setup so far). When it comes:</T>
          {MODES.map(([k, l, s]) => (
            <Pressable key={k} onPress={() => add(k)} style={({ pressed }) => ({ borderWidth: 1, borderColor: k === "ask" ? C.accent : C.line,
              backgroundColor: k === "ask" ? C.accentSoft : C.card, borderRadius: 12, padding: 12, gap: 2, opacity: pressed ? 0.7 : 1 })}>
              <Text style={{ color: k === "ask" ? C.accent : C.text, fontWeight: "700", fontSize: 15 }}>{l}{k === "ask" ? "  ·  suggested" : ""}</Text>
              <Text style={{ color: C.dim, fontSize: 13 }}>{s}</Text>
            </Pressable>
          ))}
        </>
      )}
    </ExplainSheet>
  );
}

// the market rule: Bitcoin against its 50-day average
export function MarketRule({ mk }: { mk: any }) {
  const allowed = mk.regime === "ALLOWED";
  const crossing = (allowed && mk.live_side === "below") || (!allowed && mk.live_side === "above");
  return (
    <Card onPress={() => router.push("/coin/BTC")}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <T dim small>The market rule</T>
        <View style={{ backgroundColor: allowed ? C.goodSoft : C.warnSoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 }}>
          <Text style={{ color: allowed ? C.goodDeep : C.warnDeep, fontWeight: "700", fontSize: 12 }}>{allowed ? "BUYING ALLOWED" : "CAREFUL"}</Text>
        </View>
      </View>
      <Text style={{ color: C.text, fontSize: 16, fontWeight: "600", lineHeight: 22 }}>
        Bitcoin is {Math.abs(mk.vs_pct).toFixed(0)}% {mk.vs_pct >= 0 ? "above" : "below"} its 50-day average. {allowed ? "Buying is allowed." : "Ananta stays careful."}
      </Text>
      {crossing ? <T small style={{ color: C.warn }}>Bitcoin crossed the line today: the daily close decides.</T> : null}
      <LineChart height={110} series={[{ data: mk.closes, color: C.text, width: 1.6, label: "Bitcoin" }, { data: mk.ema, color: C.accent, dashed: true, label: "50-day" }]}
        xLabels={["90 days ago", "today"]} />
    </Card>
  );
}

// ---- findings in simple words, details on tap ----
const TAGS: Record<string, string> = { MISSED: "MISSED", SEEN: "SEEN", LESSON: "LESSON", SHIFT: "MARKET", DOWN: "SYSTEM" };

export function Findings({ items, empty }: { items: any[]; empty?: React.ReactNode }) {
  const [open, setOpen] = useState<any>(null);
  const tone = (k: string): [string, string] => k === "MISSED" || k === "SHIFT" ? [C.warnDeep, C.warnSoft] : k === "DOWN" ? [C.badDeep, C.badSoft]
    : k === "SEEN" ? [C.accent, C.accentSoft] : [C.text, C.card2];
  return (
    <Card title="Findings" right={<Text onPress={() => router.push("/missed")} style={{ color: C.accent, fontWeight: "600" }}>Missed moves ›</Text>}>
      {items.length === 0 ? (empty ?? <T dim>Nothing new in the last two days.</T>) : null}
      {items.map((f, i) => {
        const [fg, bg] = tone(f.kind);
        return (
          <View key={i}>
            {i ? <Divider /> : null}
            <Pressable onPress={() => setOpen(f)} accessibilityRole="button" style={{ flexDirection: "row", gap: 10, paddingVertical: 10, alignItems: "center" }}>
              <View style={{ backgroundColor: bg, borderRadius: 6, paddingHorizontal: 6, paddingVertical: 3 }}>
                <Text style={{ color: fg, fontSize: 10, fontWeight: "800" }}>{TAGS[f.kind] ?? "NOTE"}</Text>
              </View>
              <Text style={{ color: C.text, fontSize: 15, flex: 1, lineHeight: 20 }}>{f.simple ?? f.title}</Text>
              <Text style={{ color: C.faint, fontSize: 18 }}>›</Text>
            </Pressable>
          </View>
        );
      })}
      <ExplainSheet open={!!open} onClose={() => setOpen(null)} title={open?.title ?? ""}>
        <Text style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>{open?.body}</Text>
        {open?.link === "missed" ? <Btn label="See every missed move" kind="secondary" onPress={() => { setOpen(null); router.push("/missed"); }} /> : null}
        <Btn label="Ask Ananta about this" onPress={() => { const f = open; setOpen(null); askAbout({ screen: "home", label: f.title, coin: f.coin, item: f }, `Explain this finding simply: ${f.title}. ${f.body}`); }} />
      </ExplainSheet>
    </Card>
  );
}

// ---- before the first trade ----
export function StartCard({ title, onPress }: { title: string; onPress: () => void }) {
  return (
    <Card title={title}>
      <T dim>Nothing here yet. Start trading and set up Ananta: pick a coin to watch, choose how Ananta should act, and this fills up.</T>
      <Btn label="Start trading and set up Ananta" onPress={onPress} />
    </Card>
  );
}

// ---- a concept, introduced once when it first matters (plan 4.5) ----
export function ConceptCard() {
  const { data, reload } = useData("/v3/concepts/next", 300000);
  const c = data?.concept;
  if (!c) return null;
  const done = async () => { try { await api(`/v3/concepts/${c.id}/seen`, {}); } catch {} reload(); };
  const go = async () => {
    await done();
    if (c.open) (c.open.startsWith("/(tabs)") ? goTab : router.push)(c.open as any);
    else if (c.ask) goTab({ pathname: "/(tabs)/ask", params: { q: c.ask, t: String(Date.now()) } } as any);
  };
  return (
    <View style={{ backgroundColor: C.accentSoft, borderRadius: 14, borderWidth: 1, borderColor: C.accent, padding: 14, gap: 8 }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={{ color: C.accent, fontWeight: "800", fontSize: 15, flex: 1 }}>{c.title}</Text>
        <Pressable onPress={done} hitSlop={10} accessibilityLabel="Close"><Text style={{ color: C.dim, fontSize: 16 }}>✕</Text></Pressable>
      </View>
      <Text style={{ color: C.text, fontSize: 14, lineHeight: 20 }}>{c.text}</Text>
      <Btn label={c.button ?? "Show me"} onPress={go} />
    </View>
  );
}
