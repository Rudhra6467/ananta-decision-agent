// One evidence trade in full (the "detail" depth): the price with its zone, entry and stop; the plan Jarvis wrote before the
// trade; what woke it; its random twin; and the review once it has closed. Works for any evidence book's trade.
import { Spot } from "../../src/spotlight";
import { useCallback } from "react";
import { Text, View } from "react-native";
import { Stack, useFocusEffect, useLocalSearchParams } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { LineChart } from "../../src/charts";
import { Btn, Busy, Card, ErrorBox, Screen, Stat, T, price, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor } from "../../src/theme";

const TRIGGER: Record<string, string> = {
  zone_entry: "the price came down into a support zone", attention_high: "the coin turned high attention (a supported zone, the market allowed)",
  market_shift: "the market turned allowed again", hunter: "Hunter's strategy fired", squeeze: "the Squeeze strategy fired",
};
const trig = (k: string) => TRIGGER[k] ?? (k.startsWith("explorer:") ? `the Explorer's ${k.slice(9)} setup fired` : k.startsWith("setup:") ? `the ${k.slice(6)} watch fired` : k);
const when = (t?: number) => (t ? new Date(t * 1000).toLocaleString(undefined, { weekday: "short", month: "short", day: "numeric", hour: "numeric", minute: "2-digit" }) : "");

export default function EvidenceTrade() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: d, err, loading, reload } = useData(`/v3/brain/trade/${id}`);
  const coin = d?.trade?.coin ?? "";
  useFocusEffect(useCallback(() => { setScreen({ screen: "jtrade", id: String(id), coin, label: `Evidence trade ${coin}: the plan, the chart, what happened` }); }, [id, coin]));
  const head = <Stack.Screen options={{ headerShown: true, title: coin ? `${COIN_NAME[coin] ?? coin}` : "Trade", headerStyle: { backgroundColor: C.bg },
    headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const t = d.trade, det = d.detail ?? {}, dec = d.decision, plan = dec?.plan ?? {};
  const open = t.status === "OPEN";
  const res = open ? d.pnl_usd : t.net_usd;
  const book = t.watch === "JARVIS" ? "Jarvis's book" : t.watch === "JARVIS_RANDOM" ? "a random twin" : `${t.watch} evidence book`;
  const closes = (d.hourly ?? []).map((x: any) => x.c);
  const entryIdx = (d.hourly ?? []).findIndex((x: any) => x.t >= (t.entry_t ?? 0));
  const refs: any[] = [{ value: t.entry, color: C.accent, label: "Bought" }];
  if (t.stop) refs.push({ value: t.stop, color: C.bad, label: open && det.stop0 && t.stop > det.stop0 ? "Trail" : "Stop" });
  if (det.target) refs.push({ value: det.target, color: C.good, label: "Target" });
  if (d.zone) refs.push({ value: d.zone[0], color: "#5B7083", label: "Zone" }, { value: d.zone[1], color: "#5B7083", label: "Zone" });
  return (
    <>{head}
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="jtrade.result">
        <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "flex-end" }}>
          <View style={{ gap: 2, flex: 1 }}>
            <T dim small>{book} · {open ? `open since ${when(t.entry_t)}` : `closed ${when(t.exit_t)}`}</T>
            <T dim small>$100 on paper at {price(t.entry)}{open && d.now ? ` · now ${price(d.now)}` : t.exit ? ` · sold ${price(t.exit)}` : ""}</T>
          </View>
          <View style={{ alignItems: "flex-end" }}>
            <Text style={{ color: pnlColor(res), fontSize: 24, fontWeight: "700" }}>{res == null ? "–" : usdSigned(res)}</Text>
            <T small dim>{open ? "before costs" : `after costs · ${t.exit_why ?? ""}`}</T>
          </View>
        </View>
      </Spot>

      <Spot id="jtrade.chart">
        <Card title="The price around it" sub="Hourly closes, with the zone, entry and stop">
          <LineChart height={190} series={[{ data: closes, color: C.text, width: 1.6 }]} refs={refs}
            markers={entryIdx >= 0 ? [{ index: entryIdx, label: "bought", color: C.accent }] : []} xLabels={["2 days before", open ? "now" : "a day after"]} />
        </Card>
      </Spot>

      {dec ? (
        <Spot id="jtrade.plan">
          <Card title="The plan, written before the trade">
            {dec.thesis ? <Text style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>“{dec.thesis}”</Text> : null}
            <View style={{ flexDirection: "row", gap: 10, marginTop: 6 }}>
              <Stat label="Confidence" value={`${Math.round(dec.confidence ?? 0)}%`} />
              <Stat label="Size" value={`${Math.round(dec.size_pct ?? 0)}%`} />
              <Stat label="Stop" value={price(det.stop0 ?? t.stop)} sub={det.stop0 && t.entry ? `${(100 * (det.stop0 / t.entry - 1)).toFixed(1)}%` : undefined} />
              <Stat label="Exit" value={det.trail_atr ? `Trail ${det.trail_atr}` : det.target ? "Target" : "Time"} sub={`${det.days ?? "–"} days max`} />
            </View>
            {(plan.for ?? []).length ? (<View style={{ gap: 4, marginTop: 6 }}><Text style={{ color: C.good, fontWeight: "700" }}>For</Text>
              {plan.for.map((x: string, i: number) => <T key={i} small>· {x}</T>)}</View>) : null}
            {(plan.against ?? []).length ? (<View style={{ gap: 4, marginTop: 6 }}><Text style={{ color: C.bad, fontWeight: "700" }}>Against, and how the plan handles it</Text>
              {plan.against.map((x: string, i: number) => <T key={i} small>· {x}</T>)}</View>) : null}
            {plan.change_mind ? (<View style={{ gap: 4, marginTop: 6 }}><Text style={{ color: C.text, fontWeight: "700" }}>Wrong if</Text><T small>{plan.change_mind}</T></View>) : null}
            {(dec.knowledge ?? []).length ? <T small dim>Knowledge used: {dec.knowledge.join(", ")}</T> : null}
          </Card>
        </Spot>
      ) : null}

      <Spot id="jtrade.timeline">
        <Card title="What happened">
          {dec ? <Line2 when={when(dec.t)} text={`Woke because ${Object.keys(dec.triggers ?? {}).map(trig).join("; ") || "a flagged moment"}.`} /> : null}
          {dec ? <Line2 when={when(dec.t)} text={`Decided to buy, $100 on paper (cost of the decision about ${Math.max(1, Math.round(100 * (dec.cost_usd ?? 0)))} cents).`} /> : null}
          {!dec && t.why ? <Line2 when={when(t.signal_t)} text={`Signal: ${t.why}.`} /> : null}
          {d.twin ? <Line2 when="" text={`Random twin: ${COIN_NAME[d.twin.coin] ?? d.twin.coin} at ${price(d.twin.entry)}, the same plan${d.twin.status === "CLOSED" ? `: ${usdSigned(d.twin.net_usd)}` : ", still open"}.`} /> : null}
          {open ? <Line2 when="now" text="The eye checks the stop every 10 seconds and raises it as the price rises." /> : <Line2 when={when(t.exit_t)} text={`Closed: ${t.exit_why ?? "its rule"}.`} />}
          {d.review ? <Line2 when="review" text={d.review.text} /> : <Line2 when="later" text="A review 3 days after it closes: best and worst while open, and what the next 3 days did." />}
        </Card>
      </Spot>

      <Btn label="Ask Jarvis about this trade" kind="secondary"
        onPress={() => askAbout({ screen: "jtrade", label: `${book}: ${coin} trade`, coin, id: String(id) }, `Walk me through your ${COIN_NAME[coin] ?? coin} trade: why, and how is it going?`)} />
    </Screen>
    </>
  );
}

function Line2({ when, text }: { when: string; text: string }) {
  return (
    <View style={{ flexDirection: "row", gap: 10, paddingVertical: 5 }}>
      <Text style={{ color: C.dim, fontSize: 12, width: 78 }}>{when}</Text>
      <Text style={{ color: C.text, fontSize: 14, lineHeight: 20, flex: 1 }}>{text}</Text>
    </View>
  );
}
