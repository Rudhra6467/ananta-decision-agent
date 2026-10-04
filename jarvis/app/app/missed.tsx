// What we missed (the "understand" depth): each day's biggest rises, whether we were in them (caught), noticed them without
// trading (seen) or never looked (missed), and why; plus the kinds of moves we keep missing. Picked after the fact: ideas
// to test, never proof.
import { Spot } from "../src/spotlight";
import { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Stack, useFocusEffect } from "expo-router";
import { askAbout, setScreen } from "../src/context";
import { Busy, Card, Divider, ErrorBox, Screen, Segmented, T } from "../src/ui";
import { useData } from "../src/useData";
import { C, COIN_NAME } from "../src/theme";

const LABEL: Record<string, [string, string, string]> = {
  CAUGHT: ["CAUGHT", "#05603A", C.goodSoft], SEEN: ["SEEN", C.accent, C.accentSoft], MISSED: ["MISSED", "#7A2E0E", C.warnSoft],
};

export default function Missed() {
  const [days, setDays] = useState("1");
  const { data: d, err, loading, reload } = useData(`/v3/missed?days=${days === "1" ? 2 : days}`);
  useFocusEffect(useCallback(() => { setScreen({ screen: "missed", label: "What we missed: the biggest moves, caught / seen / missed" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "What we missed", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const latest = d.moves.length ? d.moves[0].day : null;
  const moves = days === "1" ? d.moves.filter((m: any) => m.day === latest) : d.moves;
  const count = (k: string) => moves.filter((m: any) => m.label === k).length;
  return (
    <>{head}
    <Screen loading={loading} onRefresh={reload}>
      <T dim>Each day's biggest rises (half a daily range and 3% or more), checked half an hour after the daily close.</T>
      <Segmented value={days} onChange={setDays} options={[{ key: "1", label: "Latest day" }, { key: "7", label: "7 days" }, { key: "30", label: "30 days" }]} />

      <Spot id="missed.counts">
        <View style={{ flexDirection: "row", gap: 8 }}>
          {(["CAUGHT", "SEEN", "MISSED"] as const).map((k) => (
            <View key={k} style={{ flex: 1, backgroundColor: LABEL[k][2], borderRadius: 12, padding: 12 }}>
              <Text style={{ color: LABEL[k][1], fontSize: 24, fontWeight: "700" }}>{count(k)}</Text>
              <Text style={{ color: LABEL[k][1], fontSize: 13 }}>{k.toLowerCase()}</Text>
            </View>
          ))}
        </View>
      </Spot>

      <Spot id="missed.moves">
        <Card title={days === "1" && latest ? new Date(latest + "T12:00:00Z").toLocaleDateString(undefined, { weekday: "long", month: "short", day: "numeric" }) : `Last ${days} days`}>
          {moves.length === 0 ? <T dim>No rise big enough to count in this period.</T> : null}
          {moves.map((m: any, i: number) => (
            <View key={`${m.day}${m.coin}`}>
              {i ? <Divider /> : null}
              <Pressable onPress={() => askAbout({ screen: "missed", label: `${m.coin} +${m.move_pct}% on ${m.day}`, coin: m.coin }, `Why did we ${m.label === "CAUGHT" ? "catch" : m.label === "SEEN" ? "see but not trade" : "miss"} ${m.coin}'s ${m.move_pct}% move on ${m.day}, and what would catch it next time?`)}
                style={{ paddingVertical: 11, gap: 5 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                  <Text style={{ color: C.text, fontSize: 16, fontWeight: "700" }}>{COIN_NAME[m.coin] ?? m.coin}  <Text style={{ color: C.good }}>+{m.move_pct.toFixed(1)}%</Text></Text>
                  <View style={{ backgroundColor: LABEL[m.label][2], borderRadius: 6, paddingHorizontal: 6, paddingVertical: 3 }}>
                    <Text style={{ color: LABEL[m.label][1], fontSize: 11, fontWeight: "700" }}>{LABEL[m.label][0]}</Text>
                  </View>
                </View>
                <Text style={{ color: C.dim, fontSize: 14, lineHeight: 20 }}>{m.why[0].toUpperCase() + m.why.slice(1)}.</Text>
                {days !== "1" ? <T small dim>{m.day}</T> : null}
              </Pressable>
            </View>
          ))}
        </Card>
      </Spot>

      <Spot id="missed.patterns">
        <Card title="Misses that keep coming back" sub="5 of the same kind in 30 days become an idea for the repair shop">
          {(d.patterns ?? []).length === 0 ? <T dim>None yet.</T> : null}
          {(d.patterns ?? []).map((p: any, i: number) => (
            <View key={p.pattern} style={{ paddingVertical: 6 }}>
              {i ? <Divider /> : null}
              <T>{p.said[0].toUpperCase() + p.said.slice(1)}</T>
              <T small dim>{p.times} times · about +{p.avg_move_pct}% each · {p.coins}</T>
            </View>
          ))}
          <T small dim>Picked after the fact, so a pattern here is an idea to test on paper, never proof.</T>
        </Card>
      </Spot>
    </Screen>
    </>
  );
}
