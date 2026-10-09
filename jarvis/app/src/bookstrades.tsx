// Books › Trades (plan 3.3a, D8): a summary on top, then every trade this account holds in ONE list, each with a stamp saying
// who took it (you with your initials, or Ananta: 15-minute, hourly, daily, its own pick, the trend portfolio). Card or row
// view, Open / Closed, a filter by stamp, and the two explainers at the bottom. No charts. Same screen for Madhav and a visitor.
import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { askAbout } from "./context";
import { StampChip } from "./blocks";
import { C, COIN_NAME, pnlColor } from "./theme";
import { Card, Divider, Expand, Segmented, Stat, T, pct, price, usd, usdSigned } from "./ui";

const openTrade = (t: any) => router.push(t.link ?? `/story/${encodeURIComponent(t.id)}`);

export function BooksTrades({ d, explainers }: { d: any; explainers?: React.ReactNode }) {
  const [view, setView] = useState<"card" | "row">("card");
  const [which, setWhich] = useState("open");
  const [only, setOnly] = useState<string>("all");
  const s = d.summary ?? {};
  const list: any[] = (which === "open" ? d.trades : d.closed) ?? [];
  const stamps = Array.from(new Set(list.map((t) => t.stamp?.label?.split(" · ")[0]).filter(Boolean))) as string[];
  const shown = list.filter((t) => only === "all" || (only === "mine" ? t.stamp?.who === "you" : only === "ananta" ? t.stamp?.who === "ananta"
    : t.stamp?.label?.startsWith(only)));
  const gain = (s.value ?? 0) - (s.start ?? 0);
  return (
    <View style={{ gap: 14 }}>
      <Card>
        <T dim small>All your paper books</T>
        <View style={{ flexDirection: "row", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
          <Text style={{ color: C.text, fontSize: 30, fontWeight: "700", letterSpacing: -0.5 }}>{usd(s.value, 0)}</Text>
          <Text style={{ color: pnlColor(gain), fontWeight: "600" }}>{usdSigned(gain)} since start</Text>
        </View>
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Stat label="Open result" value={usdSigned(s.open_pnl)} color={pnlColor(s.open_pnl)} />
          <Stat label="Closed (recent)" value={usdSigned(s.closed_pnl_recent)} color={pnlColor(s.closed_pnl_recent)} />
          <Stat label="Open" value={s.open_count ?? 0} />
        </View>
      </Card>

      <View style={{ flexDirection: "row", gap: 10, alignItems: "center" }}>
        <View style={{ flex: 1 }}>
          <Segmented value={which} onChange={(k) => { setWhich(k); setOnly("all"); }} options={[{ key: "open", label: `Open · ${d.trades?.length ?? 0}` }, { key: "closed", label: "Closed" }]} />
        </View>
        <Pressable onPress={() => setView(view === "card" ? "row" : "card")} accessibilityLabel={view === "card" ? "Show as rows" : "Show as cards"}
          style={{ borderWidth: 1, borderColor: C.line, borderRadius: 10, paddingHorizontal: 10, paddingVertical: 8 }}>
          <Text style={{ color: C.accent, fontWeight: "700", fontSize: 13 }}>{view === "card" ? "▤ Rows" : "▦ Cards"}</Text>
        </Pressable>
      </View>

      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {[["all", "All"], ["mine", "Only mine"], ["ananta", "Only Ananta's"], ...stamps.map((x) => [x, x])].map(([k, l]) => (
          <Pressable key={k} onPress={() => setOnly(k)} style={{ borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5, borderWidth: 1,
            borderColor: only === k ? C.accent : C.line, backgroundColor: only === k ? C.accentSoft : C.card }}>
            <Text style={{ color: only === k ? C.accent : C.dim, fontSize: 12, fontWeight: "600" }}>{l}</Text>
          </Pressable>
        ))}
      </View>

      {shown.length === 0 ? <Card><T dim>{which === "open" ? "No open trades here." : "No closed trades here yet."}</T></Card> : null}
      {view === "card" ? (
        <View style={{ gap: 10 }}>
          {shown.map((t) => <TradeCard key={`${t.id}`} t={t} closed={which === "closed"} />)}
        </View>
      ) : shown.length ? (
        <Card>
          {shown.map((t, i) => (
            <View key={`${t.id}`}>
              {i ? <Divider /> : null}
              <TradeRow t={t} closed={which === "closed"} />
            </View>
          ))}
        </Card>
      ) : null}

      {explainers}
    </View>
  );
}

function TradeCard({ t, closed }: { t: any; closed: boolean }) {
  const res = closed ? t.net_usd : t.pnl_usd;
  return (
    <Pressable onPress={() => openTrade(t)} delayLongPress={350}
      onLongPress={() => askAbout({ screen: "trade", id: t.id, coin: t.coin, label: `${t.coin} trade (${t.stamp?.label})` }, `How is this ${t.coin} trade doing?`)}
      style={({ pressed }) => ({ backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 14, gap: 8, opacity: pressed ? 0.7 : 1 })}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 16, flex: 1 }}>{COIN_NAME[t.coin] ?? t.coin}</Text>
        <Text style={{ color: pnlColor(res), fontWeight: "700", fontSize: 16 }}>{usdSigned(res)}</Text>
      </View>
      {t.stamp ? <StampChip stamp={t.stamp} small /> : null}
      {closed ? (
        <T small dim>{[t.time, t.why].filter(Boolean).join(" · ")}</T>
      ) : (
        <View style={{ flexDirection: "row", gap: 14, flexWrap: "wrap" }}>
          <T small>Bought {price(t.entry)}</T>
          <T small>Now {price(t.now)}{t.pnl_pct != null ? ` (${pct(t.pnl_pct)})` : ""}</T>
          {t.stop ? <T small dim>Stop {price(t.stop)}</T> : null}
        </View>
      )}
    </Pressable>
  );
}

function TradeRow({ t, closed }: { t: any; closed: boolean }) {
  const res = closed ? t.net_usd : t.pnl_usd;
  return (
    <Pressable onPress={() => openTrade(t)} style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 9, opacity: pressed ? 0.6 : 1 })}>
      <View style={{ flex: 1, gap: 3 }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 14 }}>{t.coin}</Text>
        <Text style={{ color: C.dim, fontSize: 12 }} numberOfLines={1}>{t.stamp?.who === "you" ? "👤 " : "✦ "}{t.stamp?.label}</Text>
      </View>
      <View style={{ alignItems: "flex-end" }}>
        <Text style={{ color: pnlColor(res), fontWeight: "700" }}>{usdSigned(res)}</Text>
        {!closed && t.pnl_pct != null ? <Text style={{ color: C.dim, fontSize: 12 }}>{pct(t.pnl_pct)}</Text> : null}
      </View>
      <Text style={{ color: C.faint, fontSize: 18 }}>›</Text>
    </Pressable>
  );
}

// the two explainers at the bottom (Madhav's trend portfolio rule and the compare against its automatic copy)
export function Explainers({ h }: { h: any }) {
  if (!h) return null;
  return (
    <Card>
      <Expand title="How this portfolio works" sub="Who takes trades here, and the trend rule">
        <T>Every trade in this list carries a stamp. ✦ means Ananta took it: the 15-minute Explorer, the hourly watch, the daily watches, Ananta's own picks
          or the trend portfolio. 👤 with your initials means you placed it; Ananta watches those and warns you, but never closes them without your yes.</T>
        {h.rule_plain ? <T>The trend portfolio: {h.rule_plain}</T> : null}
        <T small>Ratings: Strong = leading the group; Steady = middle; Weak = lagging, first to go if the trend breaks.</T>
      </Expand>
      <Divider />
      <Expand title="Compare" sub="The trend portfolio against its automatic copy">
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Stat label="Your book" value={pct(h.return_pct)} color={pnlColor(h.return_pct)} />
          {h.shadow ? <Stat label="Automatic copy" value={pct(h.shadow.return_pct)} color={pnlColor(h.shadow.return_pct)} /> : null}
        </View>
        <T small>The automatic copy follows the rule at once. A gap shows what waiting for approvals cost or saved.</T>
      </Expand>
    </Card>
  );
}
