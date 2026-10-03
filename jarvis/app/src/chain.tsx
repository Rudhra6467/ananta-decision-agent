// Madhav's decision chain, shown as a ladder: regime -> trend -> location -> trigger -> invalidation -> risk -> exposure.
// The first broken gate is where the coin stops (fail-closed). Gates after it are greyed out: "not reached".
// Relative strength, volume and setup family are evidence, shown under the ladder (not gates).
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { askAbout } from "./context";
import { Divider, Pill, T } from "./ui";
import { C } from "./theme";

const WORD: Record<string, string> = {
  REGIME: "Regime", TREND: "Trend", LOCATION: "Location", TRIGGER: "Trigger", INVALIDATION: "Invalidation", RISK: "Risk", EXPOSURE: "Exposure",
};

function Mark({ status, reached }: { status: string; reached: boolean }) {
  if (!reached) return <Text style={{ color: C.faint, width: 18, fontWeight: "700" }}>·</Text>;
  const ok = status === "PASS";
  return <Text style={{ color: ok ? C.good : C.bad, width: 18, fontWeight: "800" }}>{ok ? "✓" : "✗"}</Text>;
}

export function ChainLadder({ row }: { row: any }) {
  if (!row) return null;
  const o = row.observations ?? {};
  return (
    <View style={{ gap: 6 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <Pill text={row.verdict === "CANDIDATE" ? "CANDIDATE" : `STOPS AT ${WORD[row.stops_at] ?? row.stops_at}`.toUpperCase()}
          color={row.verdict === "CANDIDATE" ? C.good : C.dim} bg={row.verdict === "CANDIDATE" ? C.goodSoft : C.card2} />
      </View>
      <T>{row.summary}</T>
      {(row.gates ?? []).map((g: any) => (
        <View key={g.gate} style={{ flexDirection: "row", gap: 6, opacity: g.reached ? 1 : 0.45 }}>
          <Mark status={g.status} reached={g.reached} />
          <View style={{ flex: 1 }}>
            <Text style={{ color: C.text, fontSize: 13, fontWeight: "600" }}>{WORD[g.gate] ?? g.gate} <Text style={{ color: C.faint, fontWeight: "400" }}>· {g.question}</Text></Text>
            <Text style={{ color: C.dim, fontSize: 12 }}>{g.reached ? g.why : `not reached (${g.why})`}</Text>
            <Text style={{ color: C.faint, fontSize: 10 }}>{g.source}</Text>
          </View>
        </View>
      ))}
      <Divider />
      <Text style={{ color: C.faint, fontSize: 11, fontWeight: "700", letterSpacing: 0.6 }}>EVIDENCE (NOT GATES)</Text>
      {o.relative_strength ? <T small>Relative strength vs BTC, 30 days: {o.relative_strength.vs_btc_30d_pct > 0 ? "+" : ""}{o.relative_strength.vs_btc_30d_pct}% ({o.relative_strength.state})</T> : null}
      {o.volume ? <T small>Volume: {o.volume.state}{o.volume.last_day_vs_20d ? ` (last day ${o.volume.last_day_vs_20d}x its 20-day average)` : ""}</T> : null}
      {o.setup_family ? <T small>Setup family: {String(o.setup_family).replace("_", " ")} · daily range {o.daily_atr_pct}%</T> : null}
    </View>
  );
}

export function ChainBoard({ d }: { d: any }) {
  if (!d || !d.coins) return null;
  const stops = Object.entries(d.stops ?? {}).map(([k, v]) => `${v} at ${WORD[k] ?? k.toLowerCase()}`).join(" · ");
  return (
    <View style={{ gap: 4 }}>
      <T small>Every coin walks the same ladder; the first broken gate means no trade. {stops}</T>
      {d.coins.map((r: any, i: number) => (
        <View key={r.coin}>
          {i ? <Divider /> : null}
          <Pressable onPress={() => router.push(`/coin/${r.coin}`)} delayLongPress={350}
            onLongPress={() => askAbout({ screen: "markets", label: `Decision chain for ${r.coin}: ${r.summary}` }, `Why does ${r.coin} stop at ${r.stops_at ?? "no gate"}?`)}
            style={({ pressed }) => ({ paddingVertical: 8, flexDirection: "row", gap: 10, alignItems: "center", opacity: pressed ? 0.6 : 1 })}>
            <Text style={{ color: C.text, fontWeight: "700", width: 44 }}>{r.coin}</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.dim, fontSize: 12 }} numberOfLines={2}>{r.summary?.replace(`${r.coin} `, "")}</Text>
            </View>
            <Pill text={r.verdict === "CANDIDATE" ? "CANDIDATE" : (WORD[r.stops_at] ?? r.stops_at ?? "").toUpperCase()}
              color={r.verdict === "CANDIDATE" ? C.good : C.dim} bg={r.verdict === "CANDIDATE" ? C.goodSoft : C.card2} />
          </Pressable>
        </View>
      ))}
    </View>
  );
}
