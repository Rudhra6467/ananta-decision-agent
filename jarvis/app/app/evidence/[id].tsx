// One review's page (plan 3.8): what matters on top (the verdict, what changed), the story in the middle (the question, why it was
// asked, what the test found), the technical part at the bottom.
import { useCallback } from "react";
import { Stack, useFocusEffect, useLocalSearchParams } from "expo-router";
import { goTab, setScreen } from "../../src/context";
import { DetailLayout, VERDICT } from "../../src/blocks";
import { Btn, Busy, Card, ErrorBox, Screen, T } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";

export default function Review() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const { data: d, err, loading, reload } = useData("/v3/evidence/collected", 600000);
  const r = (d?.forwarded ?? []).find((x: any) => x.id === id);
  useFocusEffect(useCallback(() => { if (r) setScreen({ screen: "evidence", id: String(id), label: `Evidence: ${r.title}` }); }, [r?.id]));
  const head = <Stack.Screen options={{ headerShown: true, title: "Review", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Evidence" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!r) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "That review was not found."} /></Screen></>;
  const [word, tone] = VERDICT[r.verdict] ?? [r.verdict, "dim"];
  const n = String(r.id).replace(/^R/, "");
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <T style={{ color: C.text, fontSize: 20, fontWeight: "700", lineHeight: 26 }}>{r.title}</T>
        <DetailLayout
          facts={[
            { label: "Verdict", value: word, color: (C as any)[tone] },
            { label: "Date", value: r.date },
          ]}
          technical={<Card><T small dim>Review {n} in the repair shop's ledger. The full write-up lives in the research notes.</T></Card>}>
          {r.changed ? <Card title="What changed"><T>{r.changed}</T></Card> : null}
          {r.question ? <Card title="The question"><T>{r.question}</T></Card> : null}
          {r.why ? <Card title="Why it was asked"><T>{r.why}</T></Card> : null}
          {r.result ? <Card title="What the test found"><T>{r.result}</T></Card> : null}
        </DetailLayout>
        <Btn label="Ask Ananta about this review" kind="secondary"
          onPress={() => goTab({ pathname: "/(tabs)/ask", params: { q: `Explain this review simply: ${r.title}. What did it find and what changed?`, t: String(Date.now()) } } as any)} />
      </Screen>
    </>
  );
}
