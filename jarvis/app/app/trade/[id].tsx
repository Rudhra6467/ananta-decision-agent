import { Spot } from "../../src/spotlight";
import { useEffect } from "react";
import { View } from "react-native";
import { setScreen } from "../../src/context";
import { Stack, router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";
import { LineChart } from "../../src/charts";
import { Big, Btn, Bullet, Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Screen, Section, Stat, T, pct, price, usd, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor } from "../../src/theme";

export default function Trade() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: d, err, loading, reload } = useData(`/v3/trade/${id}`);
  useFocusEffect(useCallback(() => { if (d) setScreen({ screen: "trade", id: d.id, coin: d.coin, label: `${d.coin} trade (${d.open ? "open" : "closed"}, ${d.setup_name})` }); }, [d?.id]));
  const head = <Stack.Screen options={{ headerShown: true, title: d ? `${d.coin} trade` : "Trade", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "Not found"} /></Screen></>;
  const pts = d.chart.points;
  const ei = Math.max(0, pts.findIndex((p: any) => p.t >= d.chart.entry_t));
  const xi = d.chart.exit_t ? pts.findIndex((p: any) => p.t >= d.chart.exit_t) : -1;
  const refs = [{ value: d.entry, color: C.dim, label: "Bought" }];
  if (d.stop) refs.push({ value: d.stop, color: C.bad, label: "Stop" });
  if (d.target) refs.push({ value: d.target, color: C.good, label: "Target" });
  return (
    <>
      {head}
      <Screen loading={loading} onRefresh={reload}>
        <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
          <Pill text={d.open ? "OPEN" : "CLOSED"} color={d.open ? C.accent : C.dim} bg={d.open ? C.accentSoft : C.card2} />
          <Pill text="PAPER" />
          <T small>{COIN_NAME[d.coin]} · {d.type_name}</T>
        </View>
        <Spot id="trade.pnl">
        <Big value={usdSigned(d.pnl_usd)} change={d.pnl_usd} changeLabel={`${pct(d.pnl_pct)} on $${d.invested} ${d.open ? "so far" : "after costs"}`} />
        </Spot>
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Stat label="Bought at" value={price(d.entry)} sub={d.entry_time} />
          <Stat label={d.open ? "Price now" : "Sold at"} value={price(d.price)} sub={d.open ? "" : d.exit_time} />
        </View>

        <Card>
          <Spot id="trade.chart">
          <LineChart height={200} series={[{ data: pts.map((p: any) => p.c), color: C.text, width: 1.8 }]} refs={refs}
            markers={[{ index: ei, label: "buy", color: C.accent }, ...(xi >= 0 ? [{ index: xi, label: "sell", color: C.text }] : [])]}
            xLabels={[`${d.chart.tf} candles`, d.open ? "now" : "after exit"]} />
          </Spot>
        </Card>

        {d.open ? (
          <Spot id="trade.levels">
          <Card title="Where it stands">
            <Spot id="trade.stop">{d.stop ? <Line label={d.trailing ? "Stop (moves up after +2R)" : "Stop-loss"} value={`${price(d.stop)}  (${pct(d.to_stop_pct)})`} color={C.bad} /> : <Line label="Stop-loss" value="none" />}</Spot>
            <Spot id="trade.target">{d.target ? <Line label="Target" value={`${price(d.target)}  (${pct(d.to_target_pct)})`} color={C.good} /> : <Line label="Target" value="none: rides the trend" />}</Spot>
            <Line label="Time limit" value={d.time_limit} />
          </Card>
          </Spot>
        ) : (
          <Card title="How it ended"><T>{d.exit}</T></Card>
        )}

        {d.highest_price != null ? (
          <Card title="While it was open">
            <Line label="Highest price" value={`${price(d.highest_price)} (${d.highest_pct >= 0 ? "+" : ""}${d.highest_pct}%)`} />
            <Line label="Lowest price" value={`${price(d.lowest_price)} (${d.lowest_pct >= 0 ? "+" : ""}${d.lowest_pct}%)`} />
          </Card>
        ) : null}

        <Spot id="trade.why">
        <Section title="Why we bought" />
        <Card>
          <T>{d.why_bought}</T>
          {d.conditions_at_entry.map((c: string, i: number) => <Bullet key={i}>{c}</Bullet>)}
        </Card>
        </Spot>

        {d.layers_that_day ? (
          <>
            <Section title="What Ananta's reasoning said that day" right={<T small>{d.layers_that_day.day}</T>} />
            <Card>
              {d.layers_that_day.said.map((x: any) => <Bullet key={x.name}>{x.yes ? "✓" : "·"} {x.name}</Bullet>)}
              <T small>Decision chain stopped at {String(d.layers_that_day.chain_stopped_at ?? "—").toLowerCase()} · attention {String(d.layers_that_day.attention ?? "—").toLowerCase()}{d.layers_that_day.news ? ` · news ${d.layers_that_day.news}` : ""}</T>
              <T small>{d.layers_that_day.note}</T>
            </Card>
          </>
        ) : null}

        <Spot id="trade.plan">
        <Section title="Exit plan" />
        <Card><T>{d.plan}</T></Card>
        </Spot>

        <Spot id="trade.timeline">
        <Section title="Timeline" />
        <Card>
          {d.timeline.map((x: any, i: number) => (
            <View key={i}>{i ? <Divider /> : null}<Line label={x.time} value="" sub={x.text} /></View>
          ))}
        </Card>
        </Spot>

        <Card>
          <Expand title="What if we had managed it differently?" sub="The same entry with other exit rules (evidence for the repair shop)">
            {Object.entries(d.what_if).map(([k, v]: any) => (
              <Line key={k} label={k === "HOLD" ? "Just hold (no stop, time limit only)" : `As ${k.replace("AS_", "").replace("_", "-").toLowerCase()} trade`}
                value={v.net_usd == null ? "still open" : usdSigned(v.net_usd)} color={pnlColor(v.net_usd)} sub={v.net_usd == null ? undefined : v.exit} />
            ))}
          </Expand>
        </Card>
        <Btn label={`Ask Ananta about this ${d.coin} trade`} kind="secondary"
          onPress={() => router.push({ pathname: "/(tabs)/ask", params: { q: `Explain my ${d.coin} trade ${d.id}: how is it doing and what are we waiting for?`, t: String(Date.now()) } })} />
      </Screen>
    </>
  );
}
