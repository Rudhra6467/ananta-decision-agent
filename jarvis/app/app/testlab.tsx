import { setScreen } from "../src/context";
import { useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { Stack } from "expo-router";
import { api } from "../src/api";
import { Bullet, Busy, Card, Divider, Pill, Screen, Section, Segmented, T } from "../src/ui";
import { useData } from "../src/useData";
import { C } from "../src/theme";

// Test lab: every recorded test run of Ananta (both models, voice, stability), with the answers and your verdicts.
export default function TestLab() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "testlab", label: "Test lab (recorded test runs)" }); }, []));
  const { data: list, loading, reload } = useData("/v3/evals", 0);
  const [run, setRun] = useState<string | null>(null);
  const head = <Stack.Screen options={{ headerShown: true, title: "Test lab", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Back" }} />;
  if (!list && loading) return <>{head}<Busy /></>;
  const runs = list?.runs ?? [];
  const cur = run ?? runs[0]?.run ?? null;
  return (
    <>
      {head}
      <Screen loading={loading} onRefresh={reload}>
        <T dim>Each run asks the {list?.catalog?.cases ?? "–"} test questions to both Gemini and Claude, tries {list?.catalog?.voice ?? "–"} voice questions, and checks stability. Read the answers and mark each Good / OK / Bad.</T>
        {runs.length === 0 ? <T dim>No runs yet.</T> : null}
        {runs.length > 1 ? (
          <ScrollView horizontal contentContainerStyle={{ gap: 8 }}>
            {runs.map((r: any) => (
              <Pressable key={r.run} onPress={() => setRun(r.run)} style={{ paddingHorizontal: 12, paddingVertical: 7, borderRadius: 999, backgroundColor: r.run === cur ? C.text : C.card, borderWidth: 1, borderColor: C.line }}>
                <Text style={{ color: r.run === cur ? "#FFF" : C.text, fontSize: 12 }}>{r.run.slice(4, 6)}/{r.run.slice(6, 8)} {r.run.slice(9, 11)}:{r.run.slice(11, 13)}Z</Text>
              </Pressable>
            ))}
          </ScrollView>
        ) : null}
        {cur ? <Run run={cur} /> : null}
      </Screen>
    </>
  );
}

function Run({ run }: { run: string }) {
  const { data: d, reload } = useData(`/v3/evals/${run}`, 0);
  const [prov, setProv] = useState("gemini");
  const [cat, setCat] = useState("All");
  if (!d) return <Busy />;
  const S = d.summary ?? {};
  const rows = d.results.filter((r: any) => (r.provider ?? "system") === prov || (prov === "system" && !r.provider));
  const cats = ["All", ...Array.from(new Set(rows.map((r: any) => r.cat)))] as string[];
  const shown = rows.filter((r: any) => cat === "All" || r.cat === cat);
  const mark = async (r: any, verdict: string) => {
    await api("/v3/evals/mark", { run, id: r.id, provider: r.provider ?? "system", verdict });
    reload();
  };
  return (
    <View style={{ gap: 12 }}>
      <Card title="Summary" sub={`${d.minutes} min · spent $${(d.spend_usd ?? 0).toFixed(2)}`}>
        {Object.entries(S).map(([k, v]: any) => (
          <View key={k} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 3 }}>
            <Text style={{ color: C.text, fontWeight: "600" }}>{k === "system" ? "Stability" : k === "gemini" ? "Gemini" : "Claude"}</Text>
            <Text style={{ color: v.passed === v.cases ? C.good : C.warn, fontWeight: "700" }}>{v.passed}/{v.cases} passed</Text>
            <Text style={{ color: C.dim }}>{v.median_s != null ? `median ${v.median_s}s` : ""}{v.cost ? ` · $${v.cost.toFixed(2)}` : ""}</Text>
          </View>
        ))}
      </Card>
      <Segmented value={prov} onChange={(v) => { setProv(v); setCat("All"); }} options={[{ key: "gemini", label: "Gemini" }, { key: "claude", label: "Claude" }, { key: "system", label: "Stability" }]} />
      <ScrollView horizontal contentContainerStyle={{ gap: 8 }}>
        {cats.map((c) => (
          <Pressable key={c} onPress={() => setCat(c)} style={{ paddingHorizontal: 12, paddingVertical: 6, borderRadius: 999, backgroundColor: c === cat ? C.accent : C.card, borderWidth: 1, borderColor: C.line }}>
            <Text style={{ color: c === cat ? "#FFF" : C.text, fontSize: 12 }}>{c}</Text>
          </Pressable>
        ))}
      </ScrollView>
      {shown.map((r: any) => <CaseCard key={`${r.id}-${r.provider}`} r={r} onMark={(v) => mark(r, v)} />)}
    </View>
  );
}

function CaseCard({ r, onMark }: { r: any; onMark: (v: string) => void }) {
  const [open, setOpen] = useState(false);
  const failed = (r.checks ?? []).filter((c: any) => !c.ok);
  return (
    <Card>
      <Pressable onPress={() => setOpen(!open)} style={{ gap: 6 }}>
        <View style={{ flexDirection: "row", gap: 6, alignItems: "center" }}>
          <Pill text={r.passed ? "PASS" : "FAIL"} color={r.passed ? C.good : C.bad} bg={r.passed ? C.goodSoft : C.badSoft} />
          <Text style={{ color: C.faint, fontSize: 12 }}>{r.id} · {r.cat}{r.seconds != null ? ` · ${r.seconds}s` : ""}{r.cost_usd ? ` · ${(r.cost_usd * 100).toFixed(1)}¢` : ""}</Text>
          {r.verdict ? <Pill text={r.verdict.toUpperCase()} color={r.verdict === "good" ? C.good : r.verdict === "bad" ? C.bad : C.dim} /> : null}
        </View>
        <Text style={{ color: C.text, fontWeight: "600" }}>{r.q}</Text>
        {r.heard != null ? <T small>Heard: “{r.heard}”</T> : null}
        <Text style={{ color: r.error ? C.bad : C.text, lineHeight: 20 }} numberOfLines={open ? undefined : 3}>{r.error ?? r.answer ?? r.detail ?? ""}</Text>
      </Pressable>
      {failed.length ? failed.map((c: any, i: number) => <T key={i} small>✗ {c.check}{c.detail ? ` (${c.detail})` : ""}</T>) : null}
      {open ? (
        <View style={{ gap: 6 }}>
          {(r.breakdown ?? []).map((b: string, i: number) => <Bullet key={i}>{b}</Bullet>)}
          {r.actions?.length ? <T small>Cards prepared (cancelled by the test): {r.actions.join(" | ")}</T> : null}
          {r.lookups?.length ? <T small>Looked at: {r.lookups.join(", ")}</T> : null}
          <Divider />
          {(r.checks ?? []).map((c: any, i: number) => <T key={i} small>{c.ok ? "✓" : "✗"} {c.check}</T>)}
        </View>
      ) : null}
      {r.provider ? (
        <View style={{ flexDirection: "row", gap: 8 }}>
          {["good", "ok", "bad"].map((v) => (
            <Pressable key={v} onPress={() => onMark(v)} style={{ flex: 1, alignItems: "center", paddingVertical: 7, borderRadius: 8, borderWidth: 1,
              borderColor: r.verdict === v ? C.accent : C.line, backgroundColor: r.verdict === v ? C.accentSoft : C.card }}>
              <Text style={{ color: C.text, fontWeight: "600", fontSize: 13 }}>{v === "good" ? "Good" : v === "ok" ? "OK" : "Bad"}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </Card>
  );
}
