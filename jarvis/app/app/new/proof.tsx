// Proof (the new look): the depth, one tap away - studies run, the nightly check, the clocks as progress rows, what we missed, last
// night's card, and the way into teachers, the repair board and the reconstruction. Data: /india/v3/proof.
import { Text, View } from "react-native";
import { router } from "expo-router";
import { useData } from "../../src/useData";
import { NScreen } from "../../src/newscreen";
import { Body, Btn, G, H, Meta, NCard, PillLink, TY } from "../../src/newui";
import { C } from "../../src/theme";
import { ScreenError } from "../../src/safe";

export const ErrorBoundary = ScreenError;

export default function Proof() {
  const { data: d, err, loading, reload } = useData<any>("/v3/proof", 120000);
  const askIt = (q: string) => router.navigate({ pathname: "/new/ask", params: { q } } as any);
  return (
    <NScreen title="Proof" loading={loading} onRefresh={reload} err={err}>
      {d ? (
        <>
          <View style={{ flexDirection: "row", gap: 12 }}>
            <NCard style={{ flex: 1 }} pad={14} onPress={() => askIt("Explain the versions tested: what a version is, how many held up and on what data, which ones matter for my money, and what was rejected.")}>
              <Meta>Versions tested ›</Meta>
              <Text style={[TY.number, { color: C.text }]}>{d.studies?.run ?? "—"}</Text>
              <Meta faint>{d.studies?.held_up ?? "—"} held up · {d.studies?.basis}</Meta>
            </NCard>
            <NCard style={{ flex: 1 }} pad={14} onPress={() => askIt("Explain the nightly check: what it re-asks every night, how it is graded, what failed recently and what is still open.")}>
              <Meta>Nightly check ›</Meta>
              <Text style={[TY.number, { color: C.text }]}>{d.exam?.grade ?? "B"}</Text>
              <Meta faint numberOfLines={3}>{d.exam?.words}</Meta>
            </NCard>
          </View>
          <View style={{ backgroundColor: C.card, borderRadius: 16, paddingHorizontal: 16, paddingTop: 12, paddingBottom: 4 }}>
            <H>The clocks</H>
            {(d.clocks || []).map((t: any, i: number) => {
              const frac = t.need ? Math.max(0.02, Math.min(1, (t.done || 0) / t.need)) : 0;
              return (
                <View key={t.name} style={{ paddingVertical: 10, borderTopWidth: i ? 1 : 0, borderTopColor: C.line, marginTop: i ? 0 : 6 }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                    <Body style={{ flex: 1 }}>{t.name}</Body>
                    <Meta>{t.complete ? "complete" : `${t.done} of ${t.need} · ${t.finish_words}`}</Meta>
                  </View>
                  <View style={{ height: 4, borderRadius: 2, backgroundColor: C.card2, marginTop: 8 }}><View style={{ width: `${Math.round(100 * frac)}%`, height: 4, borderRadius: 2, backgroundColor: G.gold() }} /></View>
                </View>
              );
            })}
            <Btn label="Ask Ananta to explain the clocks" kind="s" style={{ marginTop: 8, marginBottom: 12, paddingVertical: 8, minHeight: 40 }}
              onPress={() => askIt("Explain every clock in detail: what each trial is testing, where it stands today, what has happened so far, when it finishes, and what result would count as a pass.")} />
          </View>
          {d.missed?.words ? <NCard pad={14}><View style={{ flexDirection: "row", justifyContent: "space-between" }}><H>What we missed</H>{d.missed.day ? <Meta>{d.missed.day}</Meta> : null}</View><Body style={{ marginTop: 4 }}>{d.missed.words}</Body></NCard> : null}
          {d.last_night?.words ? <NCard pad={14}><H>Last night's card</H><Body style={{ marginTop: 4 }} numberOfLines={6}>{d.last_night.words}</Body></NCard> : null}
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {(d.links || []).map((l: any) => <PillLink key={l.route} label={l.label} onPress={() => router.push(l.route as any)} />)}
          </View>
        </>
      ) : null}
    </NScreen>
  );
}
