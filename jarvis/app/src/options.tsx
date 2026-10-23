// Options on India's Home (Madhav, 23 Oct): the Rs 60,000 index line (Nifty and Bank Nifty options), today's plan, the session's
// decisions, the option book's result, and the recorder's expiry-day paper book. Honest from day one: zero sessions say so.
// Shown only with the Indian market loaded; crypto (NDAX, spot only) has no options section.
import { Text, View } from "react-native";
import { useData } from "./useData";
import { Act, Card, ListState, T, Tag, cad, cadSigned, s as st } from "./ui";
import { C, pnlColor } from "./theme";
import { askAbout } from "./context";

export function OptionsCard() {
  const { data: d, err, loading } = useData("/v3/options", 60000);
  if (!d && loading) return <Card><T dim>Reading the options line…</T></Card>;
  if (!d) return <Card><ListState state="error" text={err ?? "No data"} /></Card>;
  const p = d.plan ?? {};
  const pct = (x: any) => (x == null ? "–" : `${Math.round(x * 100)}%`);
  const a = d.allocation ?? {};
  return (
    <Card>
      <View style={st.row}>
        <Text style={st.h}>Options · ₹60,000 index line</Text>
        <Act tight label="Ask ›" onPress={() => askAbout({ screen: "options", label: "the options line" }, "How is the options line doing, and what is today's plan?")} />
      </View>
      <View style={{ flexDirection: "row", alignItems: "baseline", gap: 10 }}>
        <Text style={{ color: C.text, fontSize: 28, fontWeight: "800" }}>{cad(d.value_inr, 0)}</Text>
        <Text style={{ color: pnlColor(d.pnl_inr), fontWeight: "700" }}>{cadSigned(d.pnl_inr)} · {d.sessions} session{d.sessions === 1 ? "" : "s"}</Text>
      </View>
      <T small>{d.words}</T>
      {p.session ? (
        <View style={{ gap: 4 }}>
          <T small>Plan for {p.session}: bull {pct(p.bull)} · bear {pct(p.bear)} · flat {pct(p.neutral)}{p.vix ? ` · VIX ${p.vix}` : ""}</T>
          <T small>{p.scenarios?.bull ? `Bull = ${p.scenarios.bull}; bear = ${p.scenarios.bear}` : ""}{(p.limits ?? []).length ? ` · limits: ${(p.limits ?? []).join(", ")}` : ""}</T>
        </View>
      ) : null}
      {(d.decisions_today ?? []).length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {d.decisions_today.map((x: any, i: number) => <Tag key={i} text={`${x.index} · ${x.point}`} value={String(x.action ?? "")} />)}
        </View>
      ) : null}
      <View style={{ gap: 2 }}>
        <T small>Recorder book (expiry-day O-03/O-04 on real option minutes): {d.recorder?.trades ?? 0} trades · {cadSigned(d.recorder?.net_inr)}</T>
        <T small>Allocation: {a.mode === "fixed" ? `fixed · stocks ${cad(a.stocks_inr, 0)} · options ${cad(a.options_inr, 0)}` : "Ananta decides the split between stocks and options"}</T>
        <T small>{d.suitability}</T>
      </View>
    </Card>
  );
}
