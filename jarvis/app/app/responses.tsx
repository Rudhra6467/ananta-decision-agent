// Cockpit › Additional features › Visitor feedback (Madhav only, Oct 12): what each visitor answered when their 3 practice days ended.
import { Text, View } from "react-native";
import { Stack } from "expo-router";
import { Busy, Card, Divider, ErrorBox, Screen, T } from "../src/ui";
import { useData } from "../src/useData";
import { C } from "../src/theme";

const when = (t: number) => new Date(t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export default function Responses() {
  const { data: d, err, loading, reload } = useData("/v3/feedback", 0);
  const head = <Stack.Screen options={{ headerShown: true, title: "Visitor feedback", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const qs: any[] = d.questions ?? [];
  const rs: any[] = d.responses ?? [];
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <T small dim>Each visitor's account lasts 3 days. When it ends, signing in shows them these questions once.</T>
        {rs.length === 0 ? <Card><T dim>No answers yet.</T></Card> : null}
        {rs.map((r) => (
          <Card key={r.id} title={r.name || r.email} sub={`${r.email} · ${when(r.t)}`}>
            {qs.filter((q) => r.answers?.[q.id]).map((q, i) => (
              <View key={q.id}>
                {i ? <Divider /> : null}
                <View style={{ paddingVertical: 8, gap: 3 }}>
                  <Text style={{ color: C.dim, fontSize: 13 }}>{q.q}</Text>
                  <Text style={{ color: C.text, fontSize: 15 }}>{r.answers[q.id]}{q.kind === "scale" ? ` of 5` : ""}</Text>
                </View>
              </View>
            ))}
          </Card>
        ))}
      </Screen>
    </>
  );
}
