import { useState } from "react";
import { View } from "react-native";
import { Stack, router, useLocalSearchParams } from "expo-router";
import { LineChart, Progress } from "../../src/charts";
import { Big, Btn, Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Row, Screen, Section, Segmented, T, pct, price, usd, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor, ratingColor, ratingWord } from "../../src/theme";

export default function Coin() {
  const { sym } = useLocalSearchParams<{ sym: string }>();
  const { data: d, err, loading, reload } = useData(`/coin/${sym}`);
  const { data: w } = useData(`/v3/coin/${sym}/watch`);
  const { data: hv } = useData("/v3/holdings", 0);
  const [range, setRange] = useState("4m");
  const head = <Stack.Screen options={{ headerShown: true, title: `${sym}`, headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const series = range === "1d" ? d.hourly.slice(-24) : range === "4d" ? d.hourly : range === "1m" ? d.daily.slice(-30) : d.daily;
  const first = series[0]?.c, last = series[series.length - 1]?.c;
  const ch = first ? 100 * (last / first - 1) : null;
  const hold = hv?.holdings?.find((h: any) => h.coin === d.coin);
  const r = d.rating;
  return (
    <>
      {head}
      <Screen loading={loading} onRefresh={reload}>
        <Big label={COIN_NAME[d.coin] ?? d.coin} value={price(d.price)} change={ch} changeLabel={`${pct(ch)} over ${range === "1d" ? "1 day" : range === "4d" ? "4 days" : range === "1m" ? "1 month" : "4 months"}`} />
        <LineChart height={190} series={[
          { data: series.map((x: any) => x.c), color: (ch ?? 0) >= 0 ? C.good : C.bad, fill: true, label: "price" },
          { data: series.map((x: any) => x.ema20), color: C.accent, width: 1.2, label: range.endsWith("d") ? "20-hour avg" : "20-day avg" },
          { data: series.map((x: any) => x.ema50), color: C.faint, width: 1.2, dashed: true, label: range.endsWith("d") ? "50-hour avg" : "50-day avg" },
        ]} />
        <Segmented value={range} onChange={setRange} options={[{ key: "1d", label: "1D" }, { key: "4d", label: "4D" }, { key: "1m", label: "1M" }, { key: "4m", label: "4M" }]} />

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

        {w?.ready ? (
          <>
            <Section title="What Ananta is waiting for" right={<T small>checked {w.as_of}</T>} />
            <Card sub={`1h trend: ${w.market.trend_1h} · 4h: ${w.market.trend_4h} · BTC: ${w.market.btc_trend_1h}`} title="Market picture">
              <Line label="RSI (1 hour)" value={String(w.market.rsi_1h)} />
              <Line label="Next support" value={price(w.market.next_support)} />
              <Line label="Next resistance" value={price(w.market.next_resistance)} />
            </Card>
            <Card>
              {w.setups.map((s: any, i: number) => (
                <View key={s.setup}>
                  {i ? <Divider /> : null}
                  <Expand title={s.name} sub={s.complete ? "All conditions met" : `${s.met} of ${s.of} conditions met`}
                    right={s.complete ? <Pill text="READY" color={C.good} bg={C.goodSoft} /> : null}>
                    <Progress value={s.met} of={s.of} color={s.complete ? C.good : C.accent} />
                    {s.conditions.map((c: any, k: number) => (
                      <T key={k} style={{ color: c.met ? C.text : C.dim }}>{c.met ? "✓" : "○"}  {c.text}</T>
                    ))}
                  </Expand>
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
        <Btn label={`Ask Ananta about ${d.coin}`} kind="secondary"
          onPress={() => router.push({ pathname: "/(tabs)/ask", params: { q: `What is happening with ${d.coin}?`, t: String(Date.now()) } })} />
      </Screen>
    </>
  );
}
