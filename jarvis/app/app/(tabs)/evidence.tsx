import { Spot } from "../../src/spotlight";
import { useCallback, useState } from "react";
import { useFocusEffect, useLocalSearchParams } from "expo-router";
import { useEffect } from "react";
import { askAbout, setScreen } from "../../src/context";
import { Text, View } from "react-native";
import { LineChart, Progress } from "../../src/charts";
import { Bullet, Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Screen, Section, Segmented, Stat, T, pct, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, pnlColor } from "../../src/theme";

const VERDICT: Record<string, [string, string]> = { PASS: [C.good, C.goodSoft], FAIL: [C.dim, C.card2] };

export default function Evidence() {
  const [tab, setTab] = useState("collected");
  const p = useLocalSearchParams<{ tab?: string; t?: string }>();
  useEffect(() => { if (p.tab) setTab(String(p.tab)); }, [p.tab, p.t]);
  useFocusEffect(useCallback(() => { setScreen({ screen: "evidence", tab, label: tab === "collected" ? "Evidence being collected" : "Evidence forwarded and in use" }); }, [tab]));
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <View style={{ paddingHorizontal: 16, paddingTop: 8, paddingBottom: 4 }}>
        <Segmented value={tab} onChange={setTab} options={[{ key: "collected", label: "Being collected" }, { key: "forwarded", label: "Forwarded & in use" }]} />
      </View>
      {tab === "collected" ? <Collected /> : <Forwarded />}
    </View>
  );
}

function Collected() {
  const { data: d, err, loading, reload } = useData("/v3/evidence/collected");
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="evidence.tracker">
      <Section title="Evidence tracker" right={<T small>tap a row to see what it means</T>} />
      <Card>
        {d.tracker.map((x: any, i: number) => (
          <View key={x.key}>
            {i ? <Divider /> : null}
            <Expand title={x.label} onLongPress={() => askAbout({ screen: "evidence", label: `Evidence tracker: ${x.label} = ${x.value}` }, `What does "${x.label}: ${x.value}" tell us?`)} right={<Text style={{ color: C.text, fontWeight: "700", fontSize: 16 }}>{String(x.value)}{x.goal ? <Text style={{ color: C.faint, fontWeight: "400" }}> / {x.goal}</Text> : null}</Text>}>
              {x.goal ? <Progress value={Number(x.value) || 0} of={x.goal} /> : null}
              <T>{x.explain}</T>
              {x.parts && Object.keys(x.parts).length ? Object.entries(x.parts).map(([k, v]: any) => <Line key={k} label={k.replace(/_/g, " ")} value={String(v)} />) : null}
            </Expand>
          </View>
        ))}
      </Card>
      </Spot>

      <Spot id="evidence.collected">
      <Section title="What we collected" right={<T small>by setup</T>} />
      <Card>
        <View style={{ flexDirection: "row", paddingBottom: 6 }}>
          <Text style={{ flex: 2.2, color: C.faint, fontSize: 11 }}>SETUP</Text>
          {["SEEN", "ORDERS", "BOUGHT", "CLOSED", "NET"].map((h) => <Text key={h} style={{ flex: 1, color: C.faint, fontSize: 11, textAlign: "right" }}>{h}</Text>)}
        </View>
        {d.collected.map((r: any) => (
          <View key={r.setup}>
            <Divider />
            <View style={{ flexDirection: "row", paddingVertical: 9, alignItems: "center" }}>
              <View style={{ flex: 2.2 }}>
                <Text style={{ color: C.text, fontSize: 13, fontWeight: "600" }}>{r.setup}</Text>
                <Text style={{ color: C.dim, fontSize: 11 }} numberOfLines={1}>{r.name}</Text>
              </View>
              {[r.seen, r.orders, r.bought, r.closed].map((v: number, k: number) => <Text key={k} style={{ flex: 1, color: C.text, fontSize: 13, textAlign: "right" }}>{v}</Text>)}
              <Text style={{ flex: 1, color: pnlColor(r.net_usd), fontSize: 13, textAlign: "right" }}>{r.closed ? usdSigned(r.net_usd) : "–"}</Text>
            </View>
          </View>
        ))}
        <T small>RND = random entries tracked as the baseline every setup must beat.</T>
      </Card>
      </Spot>

      <Spot id="evidence.forwarded">
      <Section title="Forwarded to the repair shop" />
      <Card>
        {d.forwarded.map((r: any, i: number) => (
          <View key={r.id}>
            {i ? <Divider /> : null}
            <Expand title={`#${r.id.slice(1)} ${r.title}`} sub={r.date} onLongPress={() => askAbout({ screen: "review", id: r.id, label: `Repair-shop review ${r.id}: ${r.title}` }, `Explain review ${r.id} simply: why it was done and what it means for us.`)} right={<Pill text={r.verdict === "PASS" ? "PASSED" : "NO CHANGE"} color={VERDICT[r.verdict]?.[0]} bg={VERDICT[r.verdict]?.[1]} />}>
              <Label>Why it was forwarded</Label><T>{r.why}</T>
              <Label>Question tested</Label><T>{r.question}</T>
              <Label>Result</Label><T>{r.result}</T>
              <Label>What changed</Label><T>{r.changed}</T>
            </Expand>
          </View>
        ))}
      </Card>
      </Spot>

      <Spot id="evidence.shop">
      <Section title="Repair shop status" />
      <Card>
        <T>{d.shop.summary}</T>
        {d.shop.running.length ? d.shop.running.map((r: any) => <Bullet key={r.id}>Running now: {r.title}</Bullet>) : <T small>Nothing running right now.</T>}
        {d.shop.waiting.map((q: any) => (
          <View key={q.id}>
            <Divider />
            <Expand title={q.title} sub={`Waiting for ${q.waiting_for}`}>
              <T>{q.why}</T>
            </Expand>
          </View>
        ))}
      </Card>
      </Spot>
    </Screen>
  );
}

const Label = ({ children }: { children: React.ReactNode }) => (
  <Text style={{ color: C.faint, fontSize: 11, fontWeight: "700", letterSpacing: 0.6, marginTop: 4 }}>{String(children).toUpperCase()}</Text>
);

function Forwarded() {
  const { data: d, err, loading, reload } = useData("/v3/evidence/forwarded");
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  return (
    <Screen loading={loading} onRefresh={reload}>
      {d.in_use.map((x: any) => {
        const t = x.tracking ?? {};
        return (
          <View key={x.id} style={{ gap: 12 }}>
            <Spot id="evidence.in_use">
            <Section title={`In use · ${x.id}`} right={<T small>since {x.since}</T>} />
            <Card title={x.what}>
              {t.series ? (
                <LineChart height={150} series={[
                  { data: t.series.map((p: any) => p.main), color: C.accent, label: "your book" },
                  { data: t.series.map((p: any) => p.shadow), color: C.faint, dashed: true, label: "automatic copy" },
                ]} />
              ) : null}
              <View style={{ flexDirection: "row", gap: 12 }}>
                <Stat label="Your book" value={pct(t.main_return_pct)} color={pnlColor(t.main_return_pct)} />
                <Stat label="Buy & hold" value={pct(t.buy_hold_return_pct)} color={pnlColor(t.buy_hold_return_pct)} />
                <Stat label="Trades" value={t.trades ?? "–"} sub={`${t.days ?? 0} days`} />
              </View>
              <Divider />
              <Label>Expected</Label><T>{x.expect}</T>
              <Label>Watch out</Label><T>{x.watch_out}</T>
              <Label>So far</Label><T>{x.verdict_so_far}</T>
              {x.review ? (
                <Expand title={`From review #${x.review.id.slice(1)}`} sub={x.review.title}>
                  <T>{x.review.result}</T>
                </Expand>
              ) : null}
            </Card>
            </Spot>
          </View>
        );
      })}
      <Spot id="evidence.safety">
      <Section title="Safety changes" />
      <Card>
        {d.safety_changes.map((s: any, i: number) => (
          <View key={i}>{i ? <Divider /> : null}<Line label={s.date} value="" sub={s.what} /></View>
        ))}
      </Card>
      </Spot>
    </Screen>
  );
}
