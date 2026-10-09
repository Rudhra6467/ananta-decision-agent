// Cockpit › Additional features (plan 3.8): Systems and circuit breakers (one section), Recent activities, Invites, Mandate.
import { useCallback, useState } from "react";
import { Text, View } from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { setScreen } from "../src/context";
import { Busy, Card, Divider, Dot, ErrorBox, Line, Screen, Section, T } from "../src/ui";
import { useData } from "../src/useData";
import { C } from "../src/theme";

export default function More() {
  const { data: d, err, loading, reload } = useData("/v3/cockpit");
  const { data: ch } = useData("/v3/ask/chips", 0);
  const [all, setAll] = useState(false);
  useFocusEffect(useCallback(() => { setScreen({ screen: "cockpit", label: "Cockpit › Additional features: systems, recent activities, invites, mandate" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "Additional features", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Cockpit" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const acts: any[] = d.recent_actions ?? [];
  const breakers = Object.entries(d.circuit_breakers ?? {});
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <Section title="Systems and circuit breakers" />
        <Card>
          {(d.systems ?? []).map((s: any, i: number) => (
            <View key={`s${i}`}>
              {i ? <Divider /> : null}
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 9 }}>
                <Dot color={s.ok ? C.good : C.bad} />
                <Text style={{ color: C.text, fontSize: 15, flex: 1 }}>{s.label}</Text>
                <T small>{s.ok ? (s.last ? `last ${String(s.last).slice(11, 16)} UTC` : "running") : "not responding"}</T>
              </View>
            </View>
          ))}
          {breakers.length ? <Divider /> : null}
          {breakers.map(([k, v]: any) => (
            <Line key={k} label={`Breaker: ${k.replace(".sqlite", "").replace(/_/g, " ")}`} value={v?.status === "TRIPPED" ? "Tripped" : "OK"}
              color={v?.status === "TRIPPED" ? C.bad : C.good} sub={v?.reason ?? undefined} />
          ))}
          <T small dim>A circuit breaker stops a book by itself when its losses or errors pass a limit.</T>
        </Card>

        <Section title="Recent activities" />
        <Card>
          {acts.length === 0 ? <T dim>Nothing yet.</T> : null}
          {(all ? acts : acts.slice(0, 8)).map((a: any, i: number) => (
            <View key={i}>
              {i ? <Divider /> : null}
              <Line label={`${a.action}${a.detail ? ` · ${a.detail}` : ""}`} value={a.result === "OK" ? "✓" : String(a.result).slice(0, 18)} sub={a.time} />
            </View>
          ))}
          {acts.length > 8 ? <Text onPress={() => setAll(!all)} style={{ color: C.accent, fontWeight: "600", paddingTop: 6 }}>{all ? "Show less" : `Show all ${acts.length}`}</Text> : null}
        </Card>

        <Section title="What people tap" right={<T small>last 7 days</T>} />
        <Card>
          {(ch?.chips ?? []).length === 0 ? <T dim>No chips shown yet this week.</T> : null}
          {(ch?.chips ?? []).slice(0, 12).map((x: any, i: number) => (
            <View key={i}>
              {i ? <Divider /> : null}
              <Line label={`${x.kind === "primary" ? "★ " : ""}${x.text}`} value={`${x.picked ?? 0} of ${x.shown}`} sub={x.rate != null ? `${Math.round(x.rate * 100)}% tapped` : undefined} />
            </View>
          ))}
          <T small dim>★ = the next-action chip. Chips nobody taps get replaced; the ones people tap shape the next suggestions.</T>
        </Card>

        <Card onPress={() => router.push("/people")} title="Invites" sub="Invite visitors, see who has joined, remove an account" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />
        <Card onPress={() => router.push("/mandate")} title="Your mandate" sub="Goals, markets, styles and limits Ananta follows" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />
      </Screen>
    </>
  );
}
