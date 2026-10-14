// The whole market (engine plan U8.1): every coin Ananta watches live (Universe Rule v2), by tier, with today's movers, the coins
// closest to a support zone history supports, and a search for any coin. A tap asks Ananta about that coin.
import { useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { askAbout } from "./context";
import { ExplainSheet } from "./blocks";
import { Btn, Card, Divider, Dot, ListState, StatCard, T, Tag, dayOf, s as st } from "./ui";
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
        <View style={{ flexDirection: "row", gap: 8, marginBottom: 4 }}>
          {TABS.map(([id, label]) => <Tag key={id} text={label} on={tab === id} onPress={() => setTab(id)} />)}
        </View>
      )}
      {(data?.coins ?? []).map((c: any, i: number) => <View key={c.coin}>{i ? <Divider /> : null}<Row c={c} /></View>)}
      {data && !(data.coins ?? []).length ? <T dim>{q.trim() ? "No watched coin matches that." : "Nothing here right now."}</T> : null}
      <T dim small>Tier A trades over $20M a day, B $1M–$20M. Every rule runs on every coin on paper; a rule is promoted per tier only when it beats random.</T>
    </Card>
  );
}


// The trend dial (engine fixes 1-4), first on Markets since Oct 14: market state first, setups only fill what the dial allows.
// One grammar: title · OPEN or CLOSED · one line of why · the brakes · Why › opens the rest (every reason, the benchmark books, the
// would-be account in R). Words first, the colour second: the dot is the only green or red.
export function ExposureDial({ own }: { own?: boolean }) {
  const { data, err, reload } = useData("/v3/exposure", 300000);
  const { data: bk } = useData(own ? "/v3/book500" : null, 300000);           // the account's brakes (Madhav only)
  const [why, setWhy] = useState(false);
  const d = data?.dial;
  const a = data?.account;
  const open = d?.dial != null && d.dial > 0;
  const state = d?.dial == null ? "…" : open ? "OPEN" : "CLOSED";
  const reasons: string[] = d?.why ?? [];
  const br = bk?.brakes;
  const fired = Object.entries(br?.fired ?? {}).filter(([, n]) => (n as number) > 0).map(([k]) => k.replace(/_/g, " "));
  const brakes = !own ? "" : !bk ? "" : br?.paused ? "Brakes PAUSED after a 15% fall; only you can resume" : fired.length ? `Brakes fired: ${fired.join(", ")}` : "Brakes quiet";
  if (!data && err) return <Card><ListState state="error" text="Couldn't read the dial." action={{ label: "Retry", onPress: reload }} /></Card>;
  return (
    <>
      <StatCard title={`Trend dial · crypto${d?.as_of_day ? ` · as of ${dayOf(d.as_of_day)}` : ""}`} label="The trend dial"
        meta={[brakes, "Feeds the account's core and the edge sleeve"].filter(Boolean).join(" · ")} action={{ label: "Why ›", onPress: () => setWhy(true) }}>
        {!data ? <ListState state="loading" lines={1} /> : (
          <>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
              <Dot color={d?.dial == null ? C.dim : open ? C.good : C.bad} />
              <Text style={st.title}>{state}</Text>
              <T small style={{ flex: 1 }} numberOfLines={1}>{d?.dial == null ? "" : open ? "buying allowed" : "no new buys; cash is the position"}</T>
            </View>
            <T>{reasons.slice(1, 3).map((w) => w.replace(/\s*\([^)]*\)/, "")).join(" · ") || d?.note || "Reading Bitcoin's daily close."}</T>
          </>
        )}
      </StatCard>
      <ExplainSheet open={why} onClose={() => setWhy(false)} title={`The dial is ${state}`}>
        <T>{d?.dial_words ?? "Reading Bitcoin's daily close."}</T>
        {reasons.map((w) => <T key={w} dim>· {w}</T>)}
        {d?.rule ? <T small>{d.rule}</T> : null}
        <Divider />
        {(data?.books?.books ?? []).map((b: any) => (
          <View key={b.book} style={[st.row, { paddingVertical: 4 }]}>
            <Text style={[st.t, { flex: 1 }]}>{b.book} <Text style={{ color: C.dim }}>{b.role}</Text></Text>
            <Text style={[st.rowTitle, st.num, { color: (b.return_pct ?? 0) >= 0 ? C.good : C.bad }]}>{b.return_pct == null ? "–" : `${b.return_pct >= 0 ? "+" : ""}${b.return_pct}%`}</Text>
          </View>
        ))}
        {a ? <T small>{`Would-be $2,000 account: ${a.taken} trades, ${a.closed} closed, ${a.return_pct}% (avg ${a.avg_R ?? "–"} R) vs benchmark ${a.hurdle_pct ?? "–"}% over the same days. ${a.skipped?.dial_closed ?? 0} buys skipped while the dial was closed.`}</T> : null}
        <T small>Paper only. Every strategy must make money AND beat the benchmark (Bitcoin above its 50-day average) over the same days.</T>
        <Btn label="Ask Ananta about the dial" onPress={() => { setWhy(false); askAbout({ screen: "markets", label: "the trend dial" }, "Can we buy today? Explain the trend dial, the brakes and the benchmark."); }} />
      </ExplainSheet>
    </>
  );
}
