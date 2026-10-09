// Reconstruction (Watchlists › Reconstruction, plan 3.5): the nightly rebuilds, the ones you asked for, mismatches, the
// other-traders study, and the chain of findings that came out of it.
import { useCallback } from "react";
import { Text, View } from "react-native";
import { Stack, useFocusEffect } from "expo-router";
import { setScreen } from "../src/context";
import { DetailLayout } from "../src/blocks";
import { Busy, Card, Divider, ErrorBox, Line, Screen, T } from "../src/ui";
import { useData } from "../src/useData";
import { C } from "../src/theme";

export default function Reconstruction() {
  const { data: ev, err, loading, reload } = useData("/v3/evidence/live", 600000);
  useFocusEffect(useCallback(() => { setScreen({ screen: "reconstruction", label: "Reconstruction: nightly rebuilds, mismatches, findings" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "Reconstruction", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Watchlists" }} />;
  if (!ev && loading) return <>{head}<Busy /></>;
  const rb = ev?.rebuild;
  if (!rb) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  const chain: any[] = rb.chain ?? [];
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <DetailLayout
          facts={[
            { label: "Rebuilds", value: rb.total },
            { label: "Mismatches", value: rb.mismatches, color: rb.mismatches ? C.bad : C.good },
            { label: "Last rebuild", value: rb.last?.when ?? "–" },
            { label: "Decisions checked", value: rb.last ? `${rb.last.rebuilt} of ${rb.last.checked}` : "–" },
          ]}
          technical={<Card title="How it works"><T>{rb.how}</T><T small dim>{rb.if_mismatch}</T></Card>}>
          <Card title="When it runs">
            {rb.nightly ? <Line label="Nightly" value={`${rb.nightly.runs} runs`} sub={`${rb.nightly.every} · since ${rb.nightly.first}`} /> : null}
            {rb.asked ? <><Divider /><Line label="When you ask" value={`${rb.asked.runs} runs`} sub={`${rb.asked.how} · last ${rb.asked.last}`} /></> : null}
          </Card>
          {chain.length ? (
            <Card title="What it led to" sub={`${chain.length} findings`}>
              {chain.map((c: any, i: number) => (
                <View key={i} style={{ gap: 2, paddingVertical: 6 }}>
                  {i ? <Divider /> : null}
                  <Text style={{ color: C.text, fontWeight: "700", fontSize: 15 }}>{c.step}</Text>
                  {c.what ? <T small>{c.what}</T> : null}
                </View>
              ))}
            </Card>
          ) : null}
          {rb.others ? (
            <Card title={rb.others.title} sub={`${rb.others.period} · ${rb.others.runs}`}>
              <Line label="Accounts studied" value={String(rb.others.accounts_sampled)} />
              <Line label="Round trips" value={String(rb.others.round_trips)} />
              <Line label="Their timing edge" value={rb.others.their_timing_edge} />
              <T small>{rb.others.what_we_did}</T>
            </Card>
          ) : null}
        </DetailLayout>
      </Screen>
    </>
  );
}
