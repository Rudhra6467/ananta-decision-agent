// Every coin Ananta watches live (Home › The market › Load more, plan 3.1). Each row: tap for its trading page, + to watch or trade.
import { useCallback } from "react";
import { View } from "react-native";
import { Stack, useFocusEffect } from "expo-router";
import { setScreen } from "../src/context";
import { CoinLine } from "../src/home";
import { Busy, Card, Divider, ErrorBox, Screen, T } from "../src/ui";
import { useData } from "../src/useData";
import { C } from "../src/theme";

export default function Coins() {
  const { data: d, err, loading, reload } = useData("/v3/coins", 60000);
  useFocusEffect(useCallback(() => { setScreen({ screen: "coins", label: "All coins Ananta watches live" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "All coins", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Home" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <T dim>The {d.coins.length} coins with live prices. Tap a coin for its chart and trading page; + to have Ananta watch it or to trade it yourself.</T>
        <Card>
          {d.coins.map((c: any, i: number) => (
            <View key={c.coin}>{i ? <Divider /> : null}<CoinLine c={c} /></View>
          ))}
        </Card>
      </Screen>
    </>
  );
}
