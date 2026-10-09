// The whole market (engine plan U8.1): every coin Ananta watches live (Universe Rule v2), by tier, with today's movers, the coins
// closest to a support zone history supports, and a search for any coin. A tap asks Ananta about that coin.
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { askAbout } from "./context";
import { Card, Divider, T } from "./ui";
import { useData } from "./useData";
import { C } from "./theme";

const TABS: [string, string][] = [["up", "Up today"], ["down", "Down today"], ["near", "Near support"]];
const TIER_WORDS: Record<string, string> = { A: "A", B: "B", C: "C" };

function money(p?: number | null) {
  if (p == null) return "–";
  if (p >= 100) return "$" + p.toLocaleString(undefined, { maximumFractionDigits: 0 });
  if (p >= 1) return "$" + p.toFixed(2);
  return "$" + Number(p.toPrecision(3)).toString();
}

function Row({ c }: { c: any }) {
  const chg = c.change_today_pct;
  const col = chg == null ? C.dim : chg >= 0 ? C.good : C.bad;
  return (
    <Pressable onPress={() => askAbout({ screen: "markets", label: `${c.coin} in the whole market`, coin: c.coin }, `Tell me about ${c.coin}`)}
      accessibilityLabel={`${c.coin}, ask Ananta about it`} style={{ flexDirection: "row", alignItems: "center", paddingVertical: 8, gap: 10 }}>
      <View style={{ minWidth: 26, borderRadius: 6, paddingHorizontal: 6, paddingVertical: 2, backgroundColor: C.card2 }}>
        <Text style={{ color: C.dim, fontSize: 12, fontWeight: "800", textAlign: "center" }}>{TIER_WORDS[c.tier] ?? "–"}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={{ color: C.text, fontWeight: "700" }}>{c.coin}{c.name ? <Text style={{ color: C.dim, fontWeight: "400" }}>  {c.name}</Text> : null}</Text>
        {c.near_zone ? <Text style={{ color: C.dim, fontSize: 12 }}>{c.near_zone.above_pct <= 0 ? "inside a support zone" : `${c.near_zone.above_pct}% above a support zone`}</Text> : null}
      </View>
      <Text style={{ color: C.text }}>{money(c.price)}</Text>
      <Text style={{ color: col, minWidth: 58, textAlign: "right", fontWeight: "700" }}>{chg == null ? "–" : `${chg >= 0 ? "+" : ""}${chg}%`}</Text>
    </Pressable>
  );
}

export function WholeMarket() {
  const [tab, setTab] = useState("up");
  const [q, setQ] = useState("");
  const path = q.trim() ? `/v3/universe/coins?q=${encodeURIComponent(q.trim().toUpperCase())}&n=12` : `/v3/universe/coins?sort=${tab}&tier=AB&n=8`;
  const { data } = useData(path, 60000);
  const k = data?.counts;
  return (
    <Card title="The whole market" sub={k ? `${k.listed} coins watched live · tier A ${k.A} · B ${k.B} · C ${k.C} (watched, never judged)` : "every coin Ananta watches"}>
      <TextInput value={q} onChangeText={setQ} placeholder="Search any coin (e.g. SUI, PEPE)" placeholderTextColor={C.faint} autoCapitalize="characters"
        style={{ backgroundColor: C.card2, color: C.text, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 9, marginBottom: 8 }} />
      {q.trim() ? null : (
        <View style={{ flexDirection: "row", gap: 6, marginBottom: 4 }}>
          {TABS.map(([id, label]) => (
            <Pressable key={id} onPress={() => setTab(id)} accessibilityLabel={label}
              style={{ borderRadius: 999, paddingHorizontal: 12, paddingVertical: 5, backgroundColor: tab === id ? C.accent : C.card2 }}>
              <Text style={{ color: tab === id ? C.onInk : C.dim, fontWeight: "700", fontSize: 13 }}>{label}</Text>
            </Pressable>
          ))}
        </View>
      )}
      {(data?.coins ?? []).map((c: any, i: number) => <View key={c.coin}>{i ? <Divider /> : null}<Row c={c} /></View>)}
      {data && !(data.coins ?? []).length ? <T dim>{q.trim() ? "No watched coin matches that." : "Nothing here right now."}</T> : null}
      <T dim small>Tier A trades over $20M a day, B $1M–$20M. Every rule runs on every coin on paper; a rule is promoted per tier only when it beats random.</T>
    </Card>
  );
}
