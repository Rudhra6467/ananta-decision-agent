// India · Today: what Ananta decided and why, in under three seconds, from the India read model (V0) and nothing else.
// Lead line (trend, Nifty, how many new paper trades for the next session), four cards, the five sentences with Hear it, every decision
// with its reason, and the Telugu brief for father mode with its own Hear it. Read-only: this screen books nothing.
import { useEffect, useState } from "react";
import { Platform, Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { api } from "../../src/api";
import { useData } from "../../src/useData";
import { C, RADIUS, SPACE, TYPE } from "../../src/theme";
import { INDIA, IndiaHeader } from "./_layout";

const pct = (x: any, d = 1) => (x == null ? "n/a" : `${(Number(x) * 100).toFixed(d)}%`);
const rs = (x: any) => (x == null ? "—" : `₹${Math.round(Number(x)).toLocaleString("en-IN")}`);
const tone = (x: any) => (Number(x) > 0 ? INDIA.green : Number(x) < 0 ? INDIA.red : C.dim);

function Card({ h, big, sub, color }: { h: string; big: string; sub: string; color?: string }) {
  return (
    <View style={{ backgroundColor: C.card, borderRadius: RADIUS.card, borderWidth: 1, borderColor: C.line, padding: SPACE.card, flexGrow: 1, flexBasis: 150 }}>
      <Text style={{ color: C.faint, fontSize: TYPE.tab, fontWeight: "700", letterSpacing: 0.6 }}>{h.toUpperCase()}</Text>
      <Text style={{ color: color ?? C.text, fontSize: 26, fontWeight: "800", marginTop: 4 }}>{big}</Text>
      <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 4 }}>{sub}</Text>
    </View>
  );
}

function Hear({ lang, color }: { lang: "en" | "te"; color: string }) {
  const [state, setState] = useState("");
  const play = async () => {
    setState("making the audio…");
    try {
      const b: any = await api(`/india/api/brief?lang=${lang}`);
      const a: any = await api("/india/api/speak", { sentences: b.sentences, lang }, 300000);
      if (Platform.OS === "web") {
        const audio = new (window as any).Audio(`data:${a.mime || "audio/mpeg"};base64,${a.audio_b64}`);
        audio.play();
        setState(`${Math.round(a.duration || 0)} s`);
      } else setState("plays on the web for now");
    } catch (e: any) { setState(e?.message || "the voice server did not answer"); }
  };
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginTop: 8 }}>
      <Pressable onPress={play} accessibilityRole="button" accessibilityLabel={lang === "te" ? "Hear it in Telugu" : "Hear it"}
        style={{ backgroundColor: color, paddingVertical: 9, paddingHorizontal: 16, borderRadius: RADIUS.button }}>
        <Text style={{ color: "#fff", fontWeight: "800" }}>{lang === "te" ? "వినండి · hear it" : "Hear it"}</Text>
      </Pressable>
      <Text style={{ color: C.dim, fontSize: TYPE.meta }}>{state}</Text>
    </View>
  );
}

export default function IndiaToday() {
  // the same hook every crypto screen uses: a stale sign-in goes to the login page, a quiet refresh every minute, pull-down to reload
  const { data: rm, err, loading, reload } = useData<any>("/india/api/readmodel");
  const [te, setTe] = useState<string[]>([]);
  useEffect(() => {
    if (!rm) return;
    api("/india/api/brief?lang=te", undefined, 20000, true).then((b: any) => setTe(b.sentences || [])).catch(() => setTe([]));
  }, [rm?.built_at]);
  const m = rm?.market || {}, c = rm?.call || {}, sb = rm?.stock_book || {}, d = rm?.decisions_today || {}, s = rm?.sp1 || {};
  const picks = (d.chosen || []).filter((x: any) => x.campaign !== "CTL");
  const tot = Object.values(sb.by_campaign || {}).reduce((a: number, v: any) => a + (v.realised_inr || 0), 0);
  const trend = m.trend_state === "above_both" ? ["UPTREND", INDIA.green] : m.trend_state === "below_both" ? ["DOWNTREND", INDIA.red] : ["NO CLEAR TREND", C.dim];
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <IndiaHeader title="Indian market" />
      <ScrollView refreshControl={<RefreshControl refreshing={loading && !!rm} onRefresh={reload} />}
        contentContainerStyle={{ padding: SPACE.screen, paddingBottom: 60, maxWidth: 960, alignSelf: "center", width: "100%" }}>
        {err ? <Text style={{ color: INDIA.red, fontWeight: "700" }}>{err}</Text> : null}
        {rm ? (
          <>
            <Text style={{ color: C.faint, fontSize: TYPE.meta }}>data through {rm.data_through} · built {(rm.built_at || "").slice(0, 16).replace("T", " ")} UTC · {rm.rules}</Text>
            <View style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap", gap: 8, marginTop: 8, marginBottom: 12 }}>
              <Text style={{ color: "#fff", backgroundColor: trend[1], fontSize: TYPE.tab, fontWeight: "800", paddingVertical: 3, paddingHorizontal: 8, borderRadius: 6, overflow: "hidden" }}>{trend[0]}</Text>
              <Text style={{ color: C.text, fontSize: TYPE.title, fontWeight: "800", flexShrink: 1 }}>
                {m.status === "ok" ? `Nifty ${Number(m.nifty_close).toLocaleString("en-IN")} · ${picks.length} new paper trades for ${rm.next_session}` : "No market section for this session"}
              </Text>
            </View>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: SPACE.gap }}>
              <Card h="Daily call" big={c.call || "—"} sub={c.scored != null ? `${c.hits} of ${c.scored} right (coin flip ${c.null_hits})` : "no calls scored yet"} />
              <Card h="Stock paper book" big={rs(tot)} color={tone(tot)} sub={`${sb.open_positions ?? "—"} open · realised on the reference exit`} />
              <Card h="SP1 index line" big={s.status === "ok" ? `${(s.decisions || []).length} decisions` : s.status === "lost" ? "lost" : "—"} sub={(s.words || "").slice(0, 90)} />
              <Card h="Breadth" big={m.breadth_200d_liquid != null ? `${Math.round(m.breadth_200d_liquid * 100)}%` : "—"} sub={`of the liquid 250 above their 200-day · VIX ${m.vix_close ?? "—"}`} />
            </View>
            <Text style={{ color: C.text, fontSize: TYPE.card, fontWeight: "800", marginTop: 22 }}>In five sentences</Text>
            {(rm.brief || []).map((x: string, i: number) => <Text key={i} style={{ color: C.text, fontSize: TYPE.body, lineHeight: 22, marginTop: 6 }}>• {x}</Text>)}
            <Hear lang="en" color={INDIA.saffron} />
            <Text style={{ color: C.text, fontSize: TYPE.card, fontWeight: "800", marginTop: 22 }}>Decisions for {rm.next_session}</Text>
            <Text style={{ color: C.faint, fontSize: TYPE.meta, marginBottom: 6 }}>{d.rules} · decided {(d.decided_at || "").slice(0, 16).replace("T", " ")} UTC · entry at the next open, ₹50,000 notional, every registered exit tracked</Text>
            {d.status === "ok" ? (d.chosen || []).map((x: any, i: number) => (
              <View key={i} style={{ backgroundColor: C.card, borderRadius: RADIUS.card, borderWidth: 1, borderColor: C.line, padding: SPACE.card, marginTop: 8 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Text style={{ color: C.text, fontSize: TYPE.card, fontWeight: "800" }}>{x.symbol} <Text style={{ color: C.dim, fontSize: TYPE.meta, fontWeight: "700" }}>{x.campaign}</Text></Text>
                  <Text style={{ color: C.dim, fontSize: TYPE.meta }}>close {x.close}</Text>
                </View>
                <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 4 }}>{x.why}</Text>
              </View>
            )) : <Text style={{ color: C.dim }}>No decision file for this session.</Text>}
            {(rm.missing || []).length ? <Text style={{ color: INDIA.saffron, marginTop: 12, fontWeight: "700" }}>Not available for this session: {rm.missing.join(", ")}</Text> : null}
            <Text style={{ color: C.text, fontSize: TYPE.card, fontWeight: "800", marginTop: 26 }}>నాన్నగారి కోసం · the Telugu brief</Text>
            {te.map((x, i) => <Text key={i} style={{ color: C.text, fontSize: 18, lineHeight: 30, marginTop: 4 }}>{x}</Text>)}
            {te.length ? <Hear lang="te" color={INDIA.green} /> : null}
            <Text style={{ color: C.faint, fontSize: TYPE.meta, marginTop: 14 }}>Father mode on paper: every sentence comes from the read model; nothing is booked from this screen yet.</Text>
          </>
        ) : !err ? <Text style={{ color: C.dim }}>Loading the India read model…</Text> : null}
      </ScrollView>
    </View>
  );
}
