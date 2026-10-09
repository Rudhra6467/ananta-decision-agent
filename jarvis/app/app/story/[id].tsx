// A trade's full story (plan 3.3b): key facts on top (start, now, stop, peak, low, result), its decision card and reasons,
// how it ended, and the chart since it opened at the bottom.
import { useCallback } from "react";
import { View } from "react-native";
import { Stack, useFocusEffect, useLocalSearchParams } from "expo-router";
import { goTab, setScreen } from "../../src/context";
import { DecisionCard, DetailLayout, StampChip } from "../../src/blocks";
import { CandleChart } from "../../src/charts";
import { Btn, Busy, Card, ErrorBox, Screen, T, price, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor } from "../../src/theme";

export default function Story() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: d, err, loading, reload } = useData(`/v3/books/trade/${encodeURIComponent(String(id))}`, 60000);
  useFocusEffect(useCallback(() => { setScreen({ screen: "trade", id: String(id), coin: d?.coin, label: `Trade story: ${d?.coin ?? ""} ${d?.stamp?.label ?? ""}` }); }, [id, d?.coin]));
  const head = <Stack.Screen options={{ headerShown: true, title: d ? `${COIN_NAME[d.coin] ?? d.coin} trade` : "Trade", headerStyle: { backgroundColor: C.bg },
    headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Books" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const refs: any[] = [];
  if (d.entry) refs.push({ value: d.entry, color: C.accent, label: "Start" });
  if (d.stop) refs.push({ value: d.stop, color: C.bad, label: "Stop" });
  if (d.target) refs.push({ value: d.target, color: C.good, label: "Target" });
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <StampChip stamp={d.stamp} />
        <DetailLayout
          facts={[
            { label: d.open ? "Result so far" : "Result", value: usdSigned(d.result_usd), color: pnlColor(d.result_usd) },
            { label: "Started", value: d.entry ? price(d.entry) : "–" },
            { label: d.open ? "Now" : "Ended", value: d.open ? price(d.now) : d.exits?.[0]?.price ? price(d.exits[0].price) : "–" },
            { label: "Stop", value: d.stop ? price(d.stop) : "none" },
            { label: "Highest since", value: d.peak ? price(d.peak) : "–" },
            { label: "Lowest since", value: d.low ? price(d.low) : "–" },
          ]}
          technical={d.candles?.length ? (
            <Card title="Since it opened" sub="hourly candles">
              <CandleChart candles={d.candles} refs={refs} height={220} />
            </Card>
          ) : undefined}>
          <DecisionCard card={d.card} title="The decision" time={d.entry_when ?? undefined} />
          <Card title="Why it was taken">
            {d.reasons.length ? d.reasons.map((r: string, i: number) => <T key={i}>• {r}</T>) : <T dim>No reason was recorded.</T>}
            {d.target ? <T small dim>Target {price(d.target)}</T> : null}
          </Card>
          {d.exits?.length ? (
            <Card title="How it ended">
              {d.exits.map((x: any, i: number) => (
                <View key={i}><T>{new Date(x.t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}: {x.why ?? "closed"}{x.price ? ` at ${price(x.price)}` : ""}</T></View>
              ))}
            </Card>
          ) : null}
        </DetailLayout>
        <Btn label="Ask Ananta about this trade" kind="secondary"
          onPress={() => goTab({ pathname: "/(tabs)/ask", params: { q: `Tell me about my ${d.coin} trade (${d.stamp.label}): how is it doing and what would end it?`, t: String(Date.now()) } } as any)} />
      </Screen>
    </>
  );
}
