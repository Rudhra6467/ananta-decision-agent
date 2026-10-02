import { Spot } from "../../src/spotlight";
import { useEffect, useState } from "react";
import { setScreen } from "../../src/context";
import { Text, View } from "react-native";
import { Stack, router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";
import { CandleChart, Progress } from "../../src/charts";
import { Big, Btn, Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Row, Screen, Section, Segmented, T, pct, price, usd, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor, ratingColor, ratingWord } from "../../src/theme";

export default function Coin() {
  const { sym } = useLocalSearchParams<{ sym: string }>();
  const { data: d, err, loading, reload } = useData(`/coin/${sym}`);
  const { data: w } = useData(`/v3/coin/${sym}/watch`);
  const { data: hv } = useData("/v3/holdings", 0);
  const [tf, setTf] = useState("1h");
  useFocusEffect(useCallback(() => { setScreen({ screen: "coin", coin: String(sym), label: `${sym} coin page (chart ${tf}, position, setups)` }); }, [sym, tf]));
  const [avg, setAvg] = useState(true);
  const { data: ch } = useData(`/v3/chart/${sym}?tf=${tf}`);
  const head = <Stack.Screen options={{ headerShown: true, title: `${sym}`, headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const cs = ch?.candles ?? [];
  const first = cs[0]?.c, last = d.price;
  const chg = first ? 100 * (last / first - 1) : null;
  const span: Record<string, string> = { "15m": "30 hours", "1h": "5 days", "4h": "20 days", "1d": "6 months" };
  const refs: any[] = [];
  (ch?.levels ?? []).forEach((l: any) => refs.push({ value: l.price, color: l.kind === "support" ? "#5B7083" : "#8A6D3B", label: l.label === "Support" ? "Support" : "Resist." }));
  (ch?.open_trades ?? []).forEach((t: any) => {
    refs.push({ value: t.entry, color: C.accent, label: "Bought" });
    if (t.stop) refs.push({ value: t.stop, color: C.bad, label: "Stop" });
    if (t.target) refs.push({ value: t.target, color: C.good, label: "Target" });
  });
  const hold = hv?.holdings?.find((h: any) => h.coin === d.coin);
  const r = d.rating;
  return (
    <>
      {head}
      <Screen loading={loading} onRefresh={reload}>
        <Big label={COIN_NAME[d.coin] ?? d.coin} value={price(d.price)} change={chg} changeLabel={`${pct(chg)} over ${span[tf]}`} />
        <Card>
          <Spot id="coin.chart">
          <CandleChart candles={cs} refs={refs} marks={ch?.marks ?? []} showAvg={avg} />
          </Spot>
          <View style={{ flexDirection: "row", gap: 12, flexWrap: "wrap" }}>
            <T small><Text style={{ color: C.accent }}>━</Text> 20-{tf === "1d" ? "day" : "bar"} avg</T>
            <T small><Text style={{ color: C.faint }}>┅</Text> 50-{tf === "1d" ? "day" : "bar"} avg</T>
            <T small><Text style={{ color: C.accent }}>▲</Text> Ananta bought  <Text style={{ color: C.text }}>▼</Text> sold</T>
            <Text onPress={() => setAvg(!avg)} style={{ color: C.accent, fontSize: 12 }}>{avg ? "Hide averages" : "Show averages"}</Text>
          </View>
        </Card>
        <Segmented value={tf} onChange={setTf} options={[{ key: "15m", label: "15m" }, { key: "1h", label: "1H" }, { key: "4h", label: "4H" }, { key: "1d", label: "1D" }]} />

        <Spot id="coin.position">
        <Section title="Your position" />
        <Card>
          {hold ? (
            <>
              <Line label="Value" value={usd(hold.value)} />
              <Line label="Total return" value={`${usdSigned(hold.pnl)} (${pct(hold.pnl_pct)})`} color={pnlColor(hold.pnl)} />
              <Line label="Share of portfolio" value={`${hold.weight_pct}%`} />
            </>
          ) : <T dim>Not held in the portfolio.</T>}
          {r ? (
            <View style={{ flexDirection: "row", gap: 8, alignItems: "center", marginTop: 4 }}>
              <Pill text={ratingWord[r.rating] ?? r.rating} color={ratingColor[r.rating]} />
              <T small style={{ flex: 1 }}>{(r.why ?? []).join(" · ")}</T>
            </View>
          ) : null}
        </Card>
        </Spot>

        {w?.ready ? (
          <>
            <Spot id="coin.market">
            <Section title="What Ananta is waiting for" right={<T small>checked {w.as_of}</T>} />
            <Card sub={`1h trend: ${w.market.trend_1h} · 4h: ${w.market.trend_4h} · BTC: ${w.market.btc_trend_1h}`} title="Market picture">
              <Line label="RSI (1 hour)" value={String(w.market.rsi_1h)} />
              <Spot id="coin.levels">
              <Line label="Next support" value={price(w.market.next_support)} />
              <Line label="Next resistance" value={price(w.market.next_resistance)} />
              </Spot>
            </Card>
            </Spot>
            <Card>
              {w.setups.map((s: any, i: number) => (
                <View key={s.setup}>
                  {i ? <Divider /> : null}
                  <Spot id={`coin.setup:${s.setup}`}>
                  <Expand openWhen={`coin.setup:${s.setup}`} title={s.name} sub={s.complete ? "All conditions met" : `${s.met} of ${s.of} conditions met`}
                    right={s.complete ? <Pill text="READY" color={C.good} bg={C.goodSoft} /> : null}>
                    <Progress value={s.met} of={s.of} color={s.complete ? C.good : C.accent} />
                    {s.conditions.map((c: any, k: number) => (
                      <T key={k} style={{ color: c.met ? C.text : C.dim }}>{c.met ? "✓" : "○"}  {c.text}</T>
                    ))}
                  </Expand>
                  </Spot>
                </View>
              ))}
              {w.hourly.map((h: any) => (
                <View key={h.strategy}>
                  <Divider />
                  <Expand title={`${h.strategy} (hourly watch)`} sub={h.decision === "WAIT" ? "Waiting" : h.decision}>
                    {h.missing.length ? h.missing.map((m: string, k: number) => <T key={k} dim>○  {m}</T>) : <T dim>No reasons reported.</T>}
                  </Expand>
                </View>
              ))}
            </Card>
          </>
        ) : null}

        <Spot id="coin.trades">
        <Section title="Explorer trades" />
        <Card>
          {d.open_trades.length === 0 && d.closed_trades.length === 0 ? <T dim>No trades on {d.coin} yet.</T> : null}
          {d.open_trades.map((t: any, i: number) => (
            <View key={t.id}>{i ? <Divider /> : null}
              <Row title={`Open · ${t.setup}`} sub={`Bought ${price(t.entry)}`} value={usdSigned(t.pnl_usd)} valueColor={pnlColor(t.pnl_usd)} onPress={() => router.push(`/trade/${t.id}`)} />
            </View>
          ))}
          {d.closed_trades.map((t: any, i: number) => (
            <View key={i}><Divider /><Row title={`Closed · ${t.setup}`} sub={t.closed} value={usdSigned(t.net_usd)} valueColor={pnlColor(t.net_usd)} /></View>
          ))}
        </Card>
        </Spot>
        <Btn label={`Ask Ananta about ${d.coin}`} kind="secondary"
          onPress={() => router.push({ pathname: "/(tabs)/ask", params: { q: `What is happening with ${d.coin}?`, t: String(Date.now()) } })} />
      </Screen>
    </>
  );
}
