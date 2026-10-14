import { Spot } from "../../src/spotlight";
import { useEffect, useState } from "react";
import { goTab, setScreen } from "../../src/context";
import { Text, View } from "react-native";
import { Stack, router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useCallback } from "react";
import { CandleChart, Progress } from "../../src/charts";
import { Big, Btn, Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Row, Screen, Section, Segmented, T, pct, price, usd, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor, ratingColor, ratingWord } from "../../src/theme";
import { nm } from "../../src/names";
import { ChainLadder } from "../../src/chain";
import { ReadsCoin } from "../../src/reads";
import { ZonesCoin } from "../../src/zones";
import { useMe } from "../../src/visitor";
import { OrderTicket, TradeBar } from "../../src/ticket";

export default function Coin() {
  const { sym, trade } = useLocalSearchParams<{ sym: string; trade?: string }>();
  const [ticket, setTicket] = useState<"buy" | "sell" | null>(null);
  useEffect(() => { if (trade === "buy" || trade === "sell") setTicket(trade); }, [trade]);
  const { data: d, err, loading, reload } = useData(`/coin/${sym}`);
  const { data: w } = useData(`/v3/coin/${sym}/watch`);
  const { data: chb } = useData("/v3/chain");
  const me = useMe();
  const guest = !!me?.guest;                             // a visitor: their own position, no Madhav setups or Explorer trades
  const { data: rdc } = useData(me && !guest ? `/v3/reads/${sym}` : null, 300000);
  const { data: znc } = useData(`/v3/zones/${sym}`, 300000);
  const { data: hv, reload: reloadHv } = useData("/v3/holdings", 0);
  const { data: mb, reload: reloadMb } = useData(me && !guest ? "/v3/manual" : null, 0);
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
  (ch?.levels ?? []).forEach((l: any) => refs.push({ value: l.price, color: l.kind === "support" ? C.level : C.level2, label: l.label === "Support" ? "Support" : "Resist." }));
  (guest ? [] : ch?.open_trades ?? []).forEach((t: any) => {
    refs.push({ value: t.entry, color: C.accent, label: "Bought" });
    if (t.stop) refs.push({ value: t.stop, color: C.bad, label: "Stop" });
    if (t.target) refs.push({ value: t.target, color: C.good, label: "Target" });
  });
  const hold = hv?.holdings?.find((h: any) => h.coin === d.coin);
  const mine = (guest ? hv?.book?.positions : mb?.positions)?.find((p: any) => p.coin === d.coin) ?? null;   // this account's own trade (stamped)
  const r = d.rating;
  return (
    <>
      {head}
      <Screen loading={loading} onRefresh={reload}>
        <Big label={COIN_NAME[d.coin] ?? d.coin} value={price(d.price)} change={chg} changeLabel={`${pct(chg)} over ${span[tf]}`} />
        <Card>
          <Spot id="coin.chart">
          <CandleChart candles={cs} refs={refs} marks={guest ? [] : ch?.marks ?? []} showAvg={avg} />
          </Spot>
          <View style={{ flexDirection: "row", gap: 12, flexWrap: "wrap" }}>
            <T small><Text style={{ color: C.accent }}>━</Text> 20-{tf === "1d" ? "day" : "bar"} avg</T>
            <T small><Text style={{ color: C.faint }}>┅</Text> 50-{tf === "1d" ? "day" : "bar"} avg</T>
            {guest ? null : <T small><Text style={{ color: C.accent }}>▲</Text> Ananta bought  <Text style={{ color: C.text }}>▼</Text> sold</T>}
            <Text onPress={() => setAvg(!avg)} style={{ color: C.accent, fontSize: 12 }}>{avg ? "Hide averages" : "Show averages"}</Text>
          </View>
        </Card>
        <Segmented value={tf} onChange={setTf} options={[{ key: "15m", label: "15m" }, { key: "1h", label: "1H" }, { key: "4h", label: "4H" }, { key: "1d", label: "1D" }]} />

        <Spot id="coin.position">
        <Section title="Your position" />
        <Card>
          {guest ? (mine ? (
            <>
              <Line label="Value" value={usd(mine.value)} />
              <Line label="Profit / loss" value={usdSigned(mine.pnl)} color={pnlColor(mine.pnl)} />
              {mine.stop ? <Line label="Stop" value={price(mine.stop)} /> : null}
            </>
          ) : <T dim>You don't hold any {COIN_NAME[d.coin] ?? d.coin} yet.</T>) : mine || hold ? (
            <>
              {mine ? (
                <>
                  <Line label="Your trade" value={usd(mine.value)} sub="placed by you · Ananta watches it, never closes it alone" />
                  <Line label="Profit / loss" value={usdSigned(mine.pnl)} color={pnlColor(mine.pnl)} />
                  {mine.stop ? <Line label="Stop" value={price(mine.stop)} /> : null}
                </>
              ) : null}
              {hold ? (
                <>
              <Line label="Trend portfolio" value={usd(hold.value)} />
              <Line label="Total return" value={`${usdSigned(hold.pnl)} (${pct(hold.pnl_pct)})`} color={pnlColor(hold.pnl)} />
              <Line label="Share of portfolio" value={`${hold.weight_pct}%`} />
                </>
              ) : null}
            </>
          ) : <T dim>Not held. Use Buy below to place a paper trade.</T>}
          {r && !guest ? (
            <View style={{ flexDirection: "row", gap: 8, alignItems: "center", marginTop: 4 }}>
              <Pill text={ratingWord[r.rating] ?? r.rating} color={ratingColor[r.rating]} />
              <T small style={{ flex: 1 }}>{(r.why ?? []).join(" · ")}</T>
            </View>
          ) : null}
        </Card>
        </Spot>

        {w?.ready ? (
          <>
            {chb?.coins && !guest ? (
              <Spot id="coin.chain">
                <Section title="Decision chain" right={<T small>fail-closed</T>} />
                <Card><ChainLadder row={chb.coins.find((r: any) => r.coin === String(sym).toUpperCase())} /></Card>
              </Spot>
            ) : null}
            <Spot id="coin.zones">
              <Section title="Zones" right={<T small>daily close</T>} />
              <Card><ZonesCoin d={znc} /></Card>
            </Spot>
            {guest ? null : <Spot id="coin.reads">
              <Section title="Your setups" right={<T small>daily close</T>} />
              <Card><ReadsCoin row={rdc} coin={String(sym).toUpperCase()} guest={guest} /></Card>
            </Spot>}
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

        {guest ? (hv?.started ? <Btn label={`Ask Ananta for a ${COIN_NAME[d.coin] ?? d.coin} trade idea`} onPress={() =>
          goTab({ pathname: "/(tabs)/ask", params: { q: `Is there a good trade in ${COIN_NAME[d.coin] ?? d.coin} for my book right now?`, t: String(Date.now()) } })} /> : null) : <Spot id="coin.trades">
        <Section title="Explorer trades" />
        <Card>
          {d.open_trades.length === 0 && d.closed_trades.length === 0 ? <T dim>No trades on {d.coin} yet.</T> : null}
          {d.open_trades.map((t: any, i: number) => (
            <View key={t.id}>{i ? <Divider /> : null}
              <Row title={`Open · ${nm(t.setup)}`} sub={`Bought ${price(t.entry)}`} value={usdSigned(t.pnl_usd)} valueColor={pnlColor(t.pnl_usd)} onPress={() => router.push(`/trade/${t.id}`)} />
            </View>
          ))}
          {d.closed_trades.map((t: any, i: number) => (
            <View key={i}><Divider /><Row title={`Closed · ${nm(t.setup)}`} sub={t.closed} value={usdSigned(t.net_usd)} valueColor={pnlColor(t.net_usd)} /></View>
          ))}
        </Card>
        </Spot>}
        <Btn label={`Ask Ananta about ${d.coin}`} kind="secondary"
          onPress={() => goTab({ pathname: "/(tabs)/ask", params: { q: `What is happening with ${d.coin}?`, t: String(Date.now()) } })} />
      </Screen>
      <TradeBar onBuy={() => setTicket("buy")} onSell={() => setTicket("sell")} canSell={!!mine} />
      <OrderTicket coin={d.coin} px={d.price} side={ticket ?? "buy"} held={mine?.units ?? mine?.qty} open={!!ticket} onClose={() => setTicket(null)}
        onDone={() => { reloadHv(); reloadMb(); }} />
    </>
  );
}
