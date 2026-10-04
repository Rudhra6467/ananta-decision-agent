// Jarvis's book (the "understand" depth): the trades Jarvis decides itself, $100 each on paper, each with a random twin.
// The honest score is against the twins, counted in independent events (10 before any verdict).
import { Spot } from "../src/spotlight";
import { useCallback } from "react";
import { Pressable, Text, View } from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { askAbout, setScreen } from "../src/context";
import { LineChart, Progress } from "../src/charts";
import { Busy, Card, Divider, ErrorBox, Screen, Stat, T, price, usdSigned } from "../src/ui";
import { useData } from "../src/useData";
import { C, COIN_NAME, pnlColor } from "../src/theme";

const KNOW: Record<string, string> = {
  REGIME: "Market rule", T3: "Trend portfolio", ZONES: "Zones", LOOKOUT: "Zone reactions", EXITS: "Exits", TRAIL: "Trailing stops",
  H07: "Short dip trade", M2A_G: "Your retest", READS: "Your setups", EXPLORER: "Explorer setups", COSTS: "Costs", TEACHER_50D: "50-day dip",
  BREAKOUT_VOL: "Breakouts on volume", STOP_ZONE: "Stop under the zone", NEWS: "News check", MISSED: "Missed moves", LIVE_BOOKS: "Live books",
};

export default function JarvisBook() {
  const { data: d, err, loading, reload } = useData("/v3/brain");
  useFocusEffect(useCallback(() => { setScreen({ screen: "jarvis", label: "Jarvis's book: its own paper trades against random twins" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "Jarvis's book", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const me = (d.running?.me ?? []).map((x: any) => x.v), tw = (d.running?.twins ?? []).map((x: any) => x.v);
  const n = Math.max(me.length, tw.length);
  const pad = (a: number[]) => a.concat(Array(Math.max(0, n - a.length)).fill(null));
  const open = d.open ?? [];
  const sameMove = open.length > 1 && Math.max(...open.map((o: any) => o.entry_t)) - Math.min(...open.map((o: any) => o.entry_t)) < 6 * 3600;
  return (
    <>{head}
    <Screen loading={loading} onRefresh={reload}>
      <T dim>Trades I decide myself: $100 each on paper, each with a random twin that copies the plan on another coin at the same moment.</T>

      <Spot id="jarvis.score">
        <Card title="Am I beating random?">
          <View style={{ flexDirection: "row", gap: 12 }}>
            <Stat label="Me, per trade" value={d.avg_usd_per_100 == null ? "–" : usdSigned(d.avg_usd_per_100)} color={pnlColor(d.avg_usd_per_100)} sub={`${d.closed} closed · ${open.length} open`} />
            <Stat label="Twins, per trade" value={d.random_twin_avg_usd == null ? "–" : usdSigned(d.random_twin_avg_usd)} color={pnlColor(d.random_twin_avg_usd)} />
            <Stat label="Sized result" value={usdSigned(d.sized_net_usd)} color={pnlColor(d.sized_net_usd)} sub="with my chosen sizes" />
          </View>
          {n >= 2 ? (
            <LineChart height={120} series={[{ data: pad(me), color: C.accent, label: "me" }, { data: pad(tw), color: C.dim, label: "twins" }]}
              xLabels={["first close", "latest"]} />
          ) : <T dim small>The running line starts when trades close. Blue will be me, grey the twins, after costs.</T>}
          <View style={{ gap: 6 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <T small dim>Independent events for a verdict</T><T small>{d.events} of 10 · {d.verdict}</T>
            </View>
            <Progress value={d.events} of={10} />
          </View>
        </Card>
      </Spot>

      {sameMove ? (
        <View style={{ backgroundColor: C.warnSoft, borderRadius: 12, padding: 12 }}>
          <Text style={{ color: "#7A2E0E", fontSize: 13, lineHeight: 19 }}>My open trades started on the same market move, so they count as one event. I size down when a new trade only adds more of the same bet.</Text>
        </View>
      ) : null}

      <Spot id="jarvis.open">
        <Card title="Open" sub="Live price; the bar shows how much room is left before the stop">
          {open.length === 0 ? <T dim>No open trades.</T> : null}
          {open.map((o: any, i: number) => {
            const room = o.now && o.stop && o.entry ? Math.max(0, Math.min(1, (o.now - o.stop) / (o.entry - o.stop))) : 1;
            return (
              <View key={o.id}>
                {i ? <Divider /> : null}
                <Pressable onPress={() => router.push(`/jtrade/${o.id}`)} delayLongPress={350}
                  onLongPress={() => askAbout({ screen: "jarvis", label: `Jarvis's ${o.coin} trade`, coin: o.coin, id: o.id }, `Why did you buy ${o.coin}, and how is it going?`)}
                  style={{ paddingVertical: 11, gap: 7 }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}>
                    <Text style={{ color: C.text, fontSize: 16, fontWeight: "700" }}>{COIN_NAME[o.coin] ?? o.coin}
                      <Text style={{ color: C.dim, fontWeight: "400", fontSize: 13 }}>  {price(o.entry)} · conf {Math.round(o.confidence ?? 0)}% · size {Math.round(o.size_pct ?? 0)}%</Text></Text>
                    <Text style={{ color: pnlColor(o.pnl_pct), fontSize: 15, fontWeight: "600" }}>{o.pnl_pct == null ? "–" : `${o.pnl_pct >= 0 ? "+" : ""}${o.pnl_pct.toFixed(1)}%`}</Text>
                  </View>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                    <Text style={{ color: C.dim, fontSize: 12, width: 92 }}>{o.stop_raised ? "trail " : "stop "}{o.stop_pct}%</Text>
                    <View style={{ flex: 1 }}><Progress value={room} of={1} color={room < 0.35 ? C.bad : C.accent} /></View>
                    <Text style={{ color: C.dim, fontSize: 12, width: 104, textAlign: "right" }}>{o.trail_atr ? `trail ${o.trail_atr}` : o.target ? "target" : "time"} · {o.days} days</Text>
                  </View>
                  {o.twin ? <T small dim>Random twin: {COIN_NAME[o.twin] ?? o.twin}</T> : null}
                </Pressable>
              </View>
            );
          })}
        </Card>
      </Spot>

      <Spot id="jarvis.learning">
        <Card title="What I learn from" sub="Each knowledge piece my plans cited, scored by the trades that cited it once they close">
          {(d.knowledge_credit ?? []).length === 0 ? (
            <T dim small>No closed trades yet, so no credit or blame yet.</T>
          ) : (d.knowledge_credit ?? []).map((k: any, i: number) => (
            <View key={k.knowledge} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 5 }}>
              <T>{KNOW[k.knowledge] ?? k.knowledge}</T>
              <T small>{k.trades} trades · <Text style={{ color: pnlColor(k.avg_usd) }}>{usdSigned(k.avg_usd)}</Text></T>
            </View>
          ))}
          {(d.calibration ?? []).length ? (
            <View style={{ marginTop: 8, gap: 4 }}>
              <T small dim>Confidence check: does a higher confidence mean better results?</T>
              {d.calibration.map((c: any) => (
                <View key={c.confidence} style={{ flexDirection: "row", justifyContent: "space-between" }}>
                  <T small>{c.confidence}% sure</T><T small>{c.trades} trades · {Math.round(100 * c.win_rate)}% won · {usdSigned(c.avg_usd)}</T>
                </View>
              ))}
            </View>
          ) : null}
        </Card>
      </Spot>

      <Spot id="jarvis.decisions">
        <Card title="Recent decisions" sub={`Today: ${d.today?.TAKE ?? 0} taken, ${d.today?.PASS ?? 0} passed · at most ${d.daily_limit} a day`}>
          {(d.decisions ?? []).map((x: any, i: number) => (
            <View key={x.id}>
              {i ? <Divider /> : null}
              <Pressable onPress={() => x.trade_id ? router.push(`/jtrade/${x.trade_id}`) : askAbout({ screen: "jarvis", label: `Jarvis's ${x.coin} decision`, coin: x.coin }, `Why did you ${x.action === "PASS" ? "pass on" : "decide on"} ${x.coin}?`)}
                style={{ paddingVertical: 9, gap: 3 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                  <Text style={{ color: C.text, fontWeight: "600" }}>{x.action === "TAKE" ? "Bought" : x.action === "PASS" ? "Passed" : "No decision"} {COIN_NAME[x.coin] ?? x.coin}</Text>
                  <T small dim>{new Date(x.t * 1000).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" })}</T>
                </View>
                {x.thesis ? <Text style={{ color: C.dim, fontSize: 13, lineHeight: 18 }} numberOfLines={3}>{x.thesis}</Text> : null}
                {x.after_5d_pct != null ? <T small>Five days later: {x.after_5d_pct >= 0 ? "+" : ""}{x.after_5d_pct}%</T> : null}
              </Pressable>
            </View>
          ))}
        </Card>
      </Spot>
    </Screen>
    </>
  );
}
