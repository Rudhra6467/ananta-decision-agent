// Ananta's book (the "understand" depth): the trades Ananta decides itself, $100 each on paper, each with a random twin.
// The honest score is against the twins, counted in independent events (10 before any verdict).
import { Spot } from "../src/spotlight";
import { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { askAbout, goTab, setScreen } from "../src/context";
import { ExplainLink } from "../src/blocks";
import { LineChart, Progress } from "../src/charts";
import { Busy, Card, Divider, ErrorBox, Screen, Stat, T, price, usdSigned } from "../src/ui";
import { useData } from "../src/useData";
import { C, COIN_NAME, pnlColor } from "../src/theme";
import { nm } from "../src/names";

const KNOW: Record<string, string> = {
  REGIME: "Market rule", T3: "Trend portfolio", ZONES: "Zones", LOOKOUT: "Zone reactions", EXITS: "Exits", TRAIL: "Trailing stops",
  H07: "Short dip trade", M2A_G: "Your retest", READS: "Your setups", EXPLORER: "Explorer setups", COSTS: "Costs", TEACHER_50D: "50-day dip",
  BREAKOUT_VOL: "Breakouts on volume", STOP_ZONE: "Stop under the zone", NEWS: "News check", MISSED: "Missed moves", LIVE_BOOKS: "Live books",
};

export default function JarvisBook() {
  const { data: d, err, loading, reload } = useData("/v3/brain");
  useFocusEffect(useCallback(() => { setScreen({ screen: "jarvis", label: "Ananta's book: its own paper trades against random twins" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "Ananta's book", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
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
          <Text style={{ color: C.warnDeep, fontSize: 13, lineHeight: 19 }}>My open trades started on the same market move, so they count as one event. I size down when a new trade only adds more of the same bet.</Text>
        </View>
      ) : null}

      <Spot id="jarvis.open">
        <Card onPress={() => goTab("/(tabs)/portfolio")} title={`${open.length} open trade${open.length === 1 ? "" : "s"}`}
          sub="They are in Books › Trades with the stamp “Ananta's own pick”" right={<Text style={{ color: C.accent, fontSize: 18 }}>›</Text>} />
      </Spot>

      <Spot id="jarvis.learning">
        <Card title="Ananta's learnings" sub="What my plans leaned on, scored by how those trades ended"
          right={<ExplainLink title="Ananta's learnings, explained" label="Explain">
            <T>Every time I take a trade, my plan says which pieces of knowledge it leans on: the market rule, zones, the trend portfolio, exits, and so on.</T>
            <T>When the trade closes, each piece it leaned on gets the result: the number of trades that used it, and the average dollars per $100 trade after costs.</T>
            <T>A piece with many trades and a positive average is helping; a negative one is a candidate for the repair shop. Few trades mean nothing yet.</T>
            <T>The confidence check below asks a second question: when I said I was more sure, did those trades really do better?</T>
          </ExplainLink>}>
          {(d.knowledge_credit ?? []).length === 0 ? (
            <T dim small>No closed trades yet, so no credit or blame yet.</T>
          ) : (d.knowledge_credit ?? []).map((k: any, i: number) => (
            <View key={k.knowledge} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 5 }}>
              <T>{KNOW[k.knowledge] ?? nm(k.knowledge)}</T>
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
        <Decisions d={d} />
      </Spot>
    </Screen>
    </>
  );
}

// Ananta's decisions (plan 3.4): today's counts in colour beside the title, titles only, 10 shown, then Show more.
function Decisions({ d }: { d: any }) {
  const [all, setAll] = useState(false);
  const list: any[] = d.decisions ?? [];
  const shown = all ? list : list.slice(0, 10);
  const take = d.today?.TAKE ?? 0, pass = d.today?.PASS ?? 0;
  return (
    <Card title="Ananta's decisions" sub={`at most ${d.daily_limit} a day`}
      right={<View style={{ flexDirection: "row", gap: 6 }}>
        <View style={{ backgroundColor: C.goodSoft, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3 }}><Text style={{ color: C.goodDeep, fontSize: 12, fontWeight: "700" }}>{take} taken</Text></View>
        <View style={{ backgroundColor: C.card2, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3 }}><Text style={{ color: C.dim, fontSize: 12, fontWeight: "700" }}>{pass} passed</Text></View>
      </View>}>
      {list.length === 0 ? <T dim>No decisions yet.</T> : null}
      {shown.map((x: any, i: number) => (
        <View key={x.id}>
          {i ? <Divider /> : null}
          <Pressable onPress={() => x.trade_id ? router.push(`/jtrade/${x.trade_id}`) : askAbout({ screen: "jarvis", label: `Ananta's ${x.coin} decision`, coin: x.coin }, `Why did you ${x.action === "PASS" ? "pass on" : "decide on"} ${x.coin}?`)}
            style={{ paddingVertical: 9, flexDirection: "row", alignItems: "center", gap: 8 }}>
            <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: x.action === "TAKE" ? C.good : C.faint }} />
            <Text style={{ color: C.text, fontWeight: "600", flex: 1 }}>{x.action === "TAKE" ? "Bought" : x.action === "PASS" ? "Passed" : "No decision"} {COIN_NAME[x.coin] ?? x.coin}</Text>
            <T small dim>{new Date(x.t * 1000).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" })}</T>
            <Text style={{ color: C.faint, fontSize: 16 }}>›</Text>
          </Pressable>
        </View>
      ))}
      {list.length > 10 ? <Text onPress={() => setAll(!all)} style={{ color: C.accent, fontWeight: "700", paddingTop: 6 }}>{all ? "Show less" : `Show more (${list.length - 10})`}</Text> : null}
    </Card>
  );
}
