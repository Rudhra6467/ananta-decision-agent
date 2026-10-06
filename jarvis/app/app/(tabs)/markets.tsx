import { Spot } from "../../src/spotlight";
import { Pressable, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { useCallback } from "react";
import { askAbout, setScreen } from "../../src/context";
import { Progress, Spark } from "../../src/charts";
import { Busy, Card, Divider, ErrorBox, Pill, Screen, Section, T, pct, price } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor, ratingColor, ratingWord } from "../../src/theme";
import { ChainBoard } from "../../src/chain";
import { ReadsBoard } from "../../src/reads";
import { ZonesBoard } from "../../src/zones";
import { VisitorMarkets, useMe } from "../../src/visitor";

export default function Markets() {
  const me = useMe();
  const own = !!me && !me.guest;                         // a visitor sees only their own coins (no research boards)
  const { data: d, err, loading, reload } = useData(me ? "/v3/markets" : null);
  const { data: ch } = useData(own ? "/v3/chain" : null);
  const { data: rd } = useData(own ? "/v3/reads" : null, 300000);
  const { data: zn } = useData(own ? "/v3/zones" : null, 300000);
  useFocusEffect(useCallback(() => { setScreen({ screen: "markets", label: me?.guest ? "Markets tab: your coins" : "Markets tab: watchlist of 10 coins" }); }, [me?.guest]));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  if (d.visitor) return <VisitorMarkets d={d} loading={loading} reload={reload} />;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card>
        <Spot id="markets.summary">
        <T>{d.summary}</T>
        <Progress value={d.breadth.up_1h} of={d.breadth.of} color={C.good} />
        </Spot>
        <T small>{d.btc_gate ? "Portfolio gate open: BTC is above its 50-day average." : "Portfolio gate closed: BTC is below its 50-day average."}</T>
      </Card>
      {zn ? (
        <Spot id="markets.zones">
          <Section title="Zones" right={<T small>bands, not lines</T>} />
          <Card><ZonesBoard d={zn} /></Card>
        </Spot>
      ) : null}
      {rd ? (
        <Spot id="markets.reads">
          <Section title="Your setups" right={<T small>from your own buys</T>} />
          <Card><ReadsBoard d={rd} /></Card>
        </Spot>
      ) : null}
      {ch?.coins?.length ? (
        <Spot id="markets.chain">
          <Section title="Ananta's reasoning" right={<T small>tap a coin for its ladder</T>} />
          <Card><ChainBoard d={ch} /></Card>
        </Spot>
      ) : null}
      <Section title="Watchlist" right={<T small>tap for chart and setups</T>} />
      <Card>
        {d.coins.map((c: any, i: number) => (
          <View key={c.coin}>
            {i ? <Divider /> : null}
            <Spot id={`markets.coin:${c.coin}`}>
            <Pressable onPress={() => router.push(`/coin/${c.coin}`)} delayLongPress={350}
              onLongPress={() => askAbout({ screen: "coin", coin: c.coin, label: `${c.coin} in the watchlist` }, `What is happening with ${c.coin}?`)} style={({ pressed }) => ({ paddingVertical: 12, gap: 8, opacity: pressed ? 0.6 : 1 })}>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
                <View style={{ flex: 1 }}>
                  <View style={{ flexDirection: "row", gap: 6, alignItems: "center" }}>
                    <Text style={{ color: C.text, fontSize: 16, fontWeight: "700" }}>{c.coin}</Text>
                    {c.rating ? <Pill text={ratingWord[c.rating] ?? c.rating} color={ratingColor[c.rating]} /> : null}
                    {c.open_trades ? <Pill text={`${c.open_trades} TRADE`} color={C.accent} bg={C.accentSoft} /> : null}
                  </View>
                  <Text style={{ color: C.dim, fontSize: 12 }}>{COIN_NAME[c.coin]} · 1h {c.trend_1h ?? "–"} · 4h {c.trend_4h ?? "–"}</Text>
                </View>
                <Spark data={c.spark} color={pnlColor(c.day_pct)} />
                <View style={{ alignItems: "flex-end", minWidth: 86 }}>
                  <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>{price(c.price)}</Text>
                  <Text style={{ color: pnlColor(c.day_pct), fontSize: 12, fontWeight: "600" }}>{pct(c.day_pct)} today</Text>
                </View>
              </View>
              {c.closest ? (
                <View style={{ gap: 4 }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                    <Text style={{ color: C.dim, fontSize: 12 }}>Closest setup: {c.closest.name}</Text>
                    <Text style={{ color: C.dim, fontSize: 12 }}>{c.closest.met}/{c.closest.of}</Text>
                  </View>
                  <Progress value={c.closest.met} of={c.closest.of} color={c.closest.met === c.closest.of ? C.good : C.accent} />
                  {c.closest.missing.length ? <Text style={{ color: C.faint, fontSize: 11 }} numberOfLines={1}>Missing: {c.closest.missing[0]}</Text> : null}
                </View>
              ) : null}
            </Pressable>
            </Spot>
          </View>
        ))}
      </Card>
    </Screen>
  );
}
