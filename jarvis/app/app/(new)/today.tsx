// Today (the new look, gate 2 "all looks good"): the quiet top - one decision sentence, two dated numbers, what waits, everything
// running - and the morning view's cards beneath on scroll. Before the open the cards are the morning view; after the close the first
// card is what the managed book did. Data: /india/v3/today (jarvis/india/surfaces.py).
import { Text, View } from "react-native";
import { router } from "expo-router";
import { useData } from "../../src/useData";
import { NScreen } from "../../src/newscreen";
import { Body, Dot, G, H, Meta, NCard, NumberTile, PillLink, RowLink, TY } from "../../src/newui";
import { C } from "../../src/theme";
import { ScreenError } from "../../src/safe";

export const ErrorBoundary = ScreenError;

export default function Today() {
  const { data: d, err, loading, reload } = useData<any>("/v3/today", 60000);
  const askIt = (q: string) => router.navigate({ pathname: "/(new)/ask", params: { q } } as any);
  return (
    <NScreen title="Today" loading={loading} onRefresh={reload} err={err}>
      {d ? (
        <>
          <Meta>{d.now_words}{d.when ? ` · ${d.when}` : ""}</Meta>
          <Text style={{ fontSize: 24, lineHeight: 32, fontWeight: "600", letterSpacing: -0.2, color: C.text, marginTop: 4 }}>{d.decision}</Text>
          <Meta faint>{d.decision_source}</Meta>
          <View style={{ flexDirection: "row", gap: 12, marginTop: 8 }}>
            {(d.numbers || []).map((n: any) => <NumberTile key={n.label} label={n.label} value={n.value} sub={n.sub} />)}
          </View>
          <RowLink onPress={() => askIt("What's waiting for my yes?")} left={<><Dot color={d.waiting?.count ? C.warn : C.faint} /><H>{d.waiting?.count ? `${d.waiting.count} thing${d.waiting.count === 1 ? "" : "s"} wait${d.waiting.count === 1 ? "s" : ""} for your yes` : "Nothing waits for your yes"}</H></>} />
          <RowLink onPress={() => askIt("Is everything running?")} left={<><Dot color={d.running?.ok ? C.good : C.bad} /><H>{d.running?.words}</H></>} right={<Meta>{d.running?.checked}</Meta>} />
          {d.evening ? (
            <NCard>
              <Meta color={G.gold()}>{d.evening.label}</Meta>
              <Body style={{ marginTop: 4 }}>{d.evening.text}</Body>
            </NCard>
          ) : null}
          {(d.cards || []).map((c: any) => (
            <NCard key={c.kind}>
              <Meta color={c.accent ? G.gold() : undefined}>{c.label}</Meta>
              <Body style={{ marginTop: 4 }}>{c.text}</Body>
              {c.foot ? <Meta faint style={{ marginTop: 8 }}>{c.foot}</Meta> : null}
            </NCard>
          ))}
          {d.clock ? <Meta faint>{d.clock}</Meta> : null}
          {d.next_view ? <Meta faint>{d.next_view}</Meta> : null}
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
            {(d.suggested || []).map((q: string) => <PillLink key={q} label={q} onPress={() => askIt(q)} />)}
          </View>
        </>
      ) : null}
    </NScreen>
  );
}
