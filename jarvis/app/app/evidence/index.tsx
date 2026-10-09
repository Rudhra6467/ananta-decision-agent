// Evidence (plan 3.8): every repair-shop review with a human name, newest first; each opens its own page.
import { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { setScreen } from "../../src/context";
import { Busy, Card, Divider, ErrorBox, Screen, Segmented, T } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";
import { VERDICT } from "../../src/blocks";

export default function Evidence() {
  const { data: d, err, loading, reload } = useData("/v3/evidence/collected", 600000);
  const [f, setF] = useState("all");
  useFocusEffect(useCallback(() => { setScreen({ screen: "evidence", label: "Evidence: every review of the repair shop" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "Evidence", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Cockpit" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const all: any[] = [...(d.forwarded ?? [])].reverse();
  const list = all.filter((r) => f === "all" || r.verdict === f);
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <T dim>Each review asks one question about the trading rules, tests it on history, and either changes something (Passed) or leaves the rules as they are.</T>
        <Segmented value={f} onChange={setF} options={[{ key: "all", label: `All ${all.length}` }, { key: "PASS", label: "Passed" }, { key: "FAIL", label: "No change" }]} />
        <Card>
          {list.map((r: any, i: number) => {
            const [word, tone] = VERDICT[r.verdict] ?? [r.verdict, "dim"];
            return (
              <View key={r.id}>
                {i ? <Divider /> : null}
                <Pressable onPress={() => router.push(`/evidence/${r.id}`)} style={({ pressed }) => ({ paddingVertical: 10, gap: 3, opacity: pressed ? 0.6 : 1 })}>
                  <View style={{ flexDirection: "row", gap: 8 }}>
                    <Text style={{ color: C.text, fontWeight: "600", fontSize: 15, flex: 1 }}>{r.title}</Text>
                    <Text style={{ color: C.faint, fontSize: 18 }}>›</Text>
                  </View>
                  <Text style={{ color: (C as any)[tone], fontSize: 12, fontWeight: "700" }}>{word.toUpperCase()} <Text style={{ color: C.faint, fontWeight: "400" }}>· {r.date}</Text></Text>
                  {r.changed ? <Text style={{ color: C.dim, fontSize: 13 }} numberOfLines={2}>{r.changed}</Text> : null}
                </Pressable>
              </View>
            );
          })}
        </Card>
      </Screen>
    </>
  );
}
