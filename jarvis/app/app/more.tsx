// Cockpit › Additional features (plan 3.8; Madhav, Oct 14): simple outside, details on tap.
// Every feature is one card with a one-line summary in plain words; the full detail opens in place (Expand).
import { useCallback, useState } from "react";
import { Text, View } from "react-native";
import { Stack, router, useFocusEffect } from "expo-router";
import { setScreen } from "../src/context";
import { Busy, Card, Divider, Dot, ErrorBox, Expand, Line, Screen, T } from "../src/ui";
import { useData } from "../src/useData";
import { api } from "../src/api";
import { showToast } from "../src/blocks";
import { C } from "../src/theme";
import { VoiceSettings } from "../src/voicesettings";

export default function More() {
  const { data: d, err, loading, reload } = useData("/v3/cockpit");
  const { data: ch } = useData("/v3/ask/chips", 0);
  const { data: acc, reload: reloadAcc } = useData("/v3/acceptance", 20000);
  const [days, setDays] = useState("30");
  const { data: cost } = useData(`/v3/costs?days=${days}`, 0);
  const runAcc = async () => { try { await api("/v3/acceptance/run", {}); showToast("Running the checks: a few minutes"); reloadAcc(); } catch (e: any) { showToast(e?.message ?? "Could not start"); } };
  const [all, setAll] = useState(false);
  useFocusEffect(useCallback(() => { setScreen({ screen: "cockpit", label: "More › Additional features: voice and model, systems, recent activities, costs, invites, mandate" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "Additional features", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "More" }} />;
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;

  // one-line summaries, computed so the closed card already answers "is anything wrong?"
  const acts: any[] = d.recent_actions ?? [];
  const systems: any[] = d.systems ?? [];
  const breakers = Object.entries(d.circuit_breakers ?? {});
  const down = systems.filter((s: any) => !s.ok).length;
  const tripped = breakers.filter(([, v]: any) => v?.status === "TRIPPED").length;
  const sysSub = down || tripped
    ? [down ? `${down} not responding` : "", tripped ? `${tripped} breaker tripped` : ""].filter(Boolean).join(" · ")
    : `All ${systems.length} running · no breaker tripped`;
  const lastAct = acts[0];
  const costRows: any[] = (cost?.rows ?? []).filter((r: any) => r.answers);
  const costSub = cost ? `$${cost.usd.toFixed(2)} in ${days} days${costRows[0] ? ` · biggest: ${costRows[0].job}` : ""}` : "Adding it up…";
  const accSub = acc?.latest
    ? `${acc.latest.passed} of ${acc.latest.of} pass · ${new Date(acc.latest.t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`
    : "Not run yet";
  const topChip = (ch?.chips ?? [])[0];
  const chipSub = topChip
    ? `Top: “${String(topChip.text).slice(0, 36)}” · ${topChip.rate != null ? `${Math.round(topChip.rate * 100)}% tapped` : `${topChip.picked ?? 0} of ${topChip.shown}`}`
    : "No chips shown yet this week";

  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <Card>
          <Expand title="Voice and model" sub="The voice that speaks and the model that answers">
            <VoiceSettings />
          </Expand>
        </Card>

        <Card>
          <Expand title="Systems and circuit breakers" sub={sysSub} right={<Dot color={down || tripped ? C.bad : C.good} />}>
            {systems.map((s: any, i: number) => (
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
          </Expand>
        </Card>

        <Card>
          <Expand title="Recent activities" sub={lastAct ? `Last: ${lastAct.action} · ${lastAct.time}` : "Nothing yet"}>
            {acts.length === 0 ? <T dim>Nothing yet.</T> : null}
            {(all ? acts : acts.slice(0, 8)).map((a: any, i: number) => (
              <View key={i}>
                {i ? <Divider /> : null}
                <Line label={`${a.action}${a.detail ? ` · ${a.detail}` : ""}`} value={a.result === "OK" ? "✓" : String(a.result).slice(0, 18)} sub={a.time} />
              </View>
            ))}
            {acts.length > 8 ? <Text onPress={() => setAll(!all)} style={{ color: C.accent, fontWeight: "600", paddingTop: 6 }}>{all ? "Show less" : `Show all ${acts.length}`}</Text> : null}
          </Expand>
        </Card>

        <Card>
          <Expand title="Where the AI money goes" sub={costSub}>
            <Text onPress={() => setDays(days === "30" ? "7" : "30")} style={{ color: C.accent, fontWeight: "700", paddingVertical: 4 }}>
              {days === "30" ? "Show 7 days" : "Show 30 days"}
            </Text>
            {cost ? <T small dim>${cost.usd.toFixed(2)} · {(cost.tokens_in / 1e6).toFixed(1)}M tokens in, {(cost.tokens_out / 1e6).toFixed(2)}M out</T> : null}
            {costRows.slice(0, 8).map((r: any, i: number) => (
              <View key={i}>
                {i ? <Divider /> : null}
                <Line label={`${r.job} · ${r.model}`} value={`$${r.usd.toFixed(2)}`} sub={`${r.answers} answers · ${Math.round(r.share * 100)}% of the cost · ${(r.avg_in / 1000).toFixed(1)}k tokens in each`} />
              </View>
            ))}
            {cost?.input_split ? <T small dim>Input since measuring began ({cost.input_split.answers} answers): {cost.input_split.cached_pct}% read from the cache (a tenth of the price), {cost.input_split.written_pct}% written to it, {cost.input_split.fresh_pct}% fresh.</T> : <T small dim>From now on each answer also records how much of its input came from the cache.</T>}
          </Expand>
        </Card>

        <Card>
          <Expand title="Acceptance checks" sub={accSub}>
            <Text onPress={runAcc} style={{ color: C.accent, fontWeight: "700", paddingVertical: 4 }}>{acc?.running ? "Running…" : "Run the checks now"}</Text>
            {(acc?.latest?.checks ?? []).map((c: any, i: number) => (
              <View key={i}>
                {i ? <Divider /> : null}
                <View style={{ flexDirection: "row", gap: 10, paddingVertical: 7, alignItems: "flex-start" }}>
                  <Text style={{ color: c.ok ? C.good : C.bad, fontWeight: "800", width: 18 }}>{c.ok ? "✓" : "✗"}</Text>
                  <View style={{ flex: 1, gap: 2 }}>
                    <Text style={{ color: C.text, fontSize: 14 }}>“{c.question}” <Text style={{ color: C.faint }}>· {c.who}</Text></Text>
                    <T small dim>{c.why}</T>
                  </View>
                </View>
              </View>
            ))}
            {!acc?.latest ? <T dim>Not run yet. Each run asks about 30 questions on the Test lab budget.</T> : null}
          </Expand>
        </Card>

        <Card>
          <Expand title="What people tap" sub={chipSub}>
            {(ch?.chips ?? []).length === 0 ? <T dim>No chips shown yet this week.</T> : null}
            {(ch?.chips ?? []).slice(0, 12).map((x: any, i: number) => (
              <View key={i}>
                {i ? <Divider /> : null}
                <Line label={`${x.kind === "primary" ? "★ " : ""}${x.text}`} value={`${x.picked ?? 0} of ${x.shown}`} sub={x.rate != null ? `${Math.round(x.rate * 100)}% tapped` : undefined} />
              </View>
            ))}
            <T small dim>★ = the next-action chip. Chips nobody taps get replaced; the ones people tap shape the next suggestions.</T>
          </Expand>
        </Card>

        <Card onPress={() => router.push("/people")} title="Invites" sub="Invite visitors (3 days each), see who has joined, give more days, remove an account" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />
        <Card onPress={() => router.push("/responses")} title="Visitor feedback" sub="What visitors answered when their 3 days ended" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />
        <Card onPress={() => router.push("/password")} title="Change password" sub="Your sign-in password; other devices are signed out" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />
        <Card onPress={() => router.push("/mandate")} title="Your mandate" sub="Goals, markets, styles and limits Ananta follows" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />
      </Screen>
    </>
  );
}
