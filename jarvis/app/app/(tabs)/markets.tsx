import { Pressable, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { useCallback } from "react";
import { askAbout, setScreen } from "../../src/context";
import { Progress, Spark } from "../../src/charts";
import { Busy, Card, Divider, ErrorBox, Pill, Screen, Section, T, pct, price } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor, ratingColor, ratingWord } from "../../src/theme";

export default function Markets() {
  const { data: d, err, loading, reload } = useData("/v3/markets");
  useFocusEffect(useCallback(() => { setScreen({ screen: "markets", label: "Markets tab: watchlist of 10 coins" }); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card>
        <T>{d.summary}</T>
        <Progress value={d.breadth.up_1h} of={d.breadth.of} color={C.good} />
        <T small>{d.btc_gate ? "Portfolio gate open: BTC is above its 50-day average." : "Portfolio gate closed: BTC is below its 50-day average."}</T>
      </Card>
      <Section title="Watchlist" right={<T small>tap for chart and setups</T>} />
      <Card>
        {d.coins.map((c: any, i: number) => (
          <View key={c.coin}>
            {i ? <Divider /> : null}
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
          </View>
        ))}
      </Card>
    </Screen>
  );
}
