import { Spot } from "../src/spotlight";
import { setScreen } from "../src/context";
import { Stack, useFocusEffect } from "expo-router";
import { useCallback, useState } from "react";
import { Alert, Switch, Text, View } from "react-native";
import { router } from "expo-router";
import { api, logout } from "../src/api";
import { confirmWithFaceId } from "../src/guard";
import { Btn, Busy, Card, Divider, Dot, ErrorBox, Line, Screen, Section, Segmented, T } from "../src/ui";
import { Progress } from "../src/charts";
import { useData } from "../src/useData";
import { C } from "../src/theme";

export default function CockpitPage() {
  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: "Cockpit", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
        headerTintColor: C.text, headerBackTitle: "Home" }} />
      <Cockpit />
    </>
  );
}

function Cockpit() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "cockpit", label: "Cockpit: switches, AI budget, alerts, systems" }); }, []));
  const { data: d, err, loading, reload } = useData("/v3/cockpit");
  const [showActions, setShowActions] = useState(false);
  const { data: sp, reload: reloadSpend } = useData("/v3/spend");
  const { data: al, reload: reloadAlerts } = useData("/v3/alerts");
  const { data: me } = useData("/v3/me", 0);
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;

  const flip = async (key: string, on: boolean) => {
    try {
      if (key === "kill_switch") {
        const ok = await confirmWithFaceId(on ? "Turn ON the kill switch?" : "Turn OFF the kill switch?",
          on ? "Every paper position closes at the next price and no new trades start." : "Trading (paper) may start again.");
        if (!ok) return;
        await api("/safety/kill", { on, confirm: true });
      } else if (key === "portfolio_auto") {
        if (on && !(await confirmWithFaceId("Turn on portfolio autopilot?", "The portfolio will rebalance (paper) by itself without asking you."))) return;
        await api("/portfolio/mode", { mode: on ? "AUTO" : "SUGGEST", confirm: true });
      }
    } catch (e: any) {
      Alert.alert("Not changed", e?.message ?? String(e));
    }
    reload();
  };

  return (
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="cockpit.controls">
      <Section title="Controls" />
      <Card>
        {d.switches.map((w: any, i: number) => (
          <View key={w.key}>
            {i ? <Divider /> : null}
            <View style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 10 }}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: w.locked ? C.faint : C.text, fontSize: 15, fontWeight: "600" }}>{w.label}{w.locked ? "  🔒" : ""}</Text>
                <T small>{w.help}</T>
              </View>
              <Switch value={!!w.on} disabled={!!w.locked} onValueChange={(v) => flip(w.key, v)}
                trackColor={{ true: w.key === "kill_switch" ? C.bad : C.accent, false: C.line }} />
            </View>
          </View>
        ))}
      </Card>
      </Spot>

      {sp ? (
        <>
          <Spot id="cockpit.ai">
          <Section title="Ananta AI" />
          <Card>
            <AiSwitch label="Ask Ananta" help="Off = no AI answers at all (nothing can cost money)." on={sp.settings.ask_enabled === "1"}
              onChange={async (v) => { await api("/v3/settings", { key: "ask_enabled", value: v ? "1" : "0" }); reloadSpend(); }} />
            <Divider />
            <AiSwitch label="Voice and announcements" help="Off = Ananta never speaks or reaches out by itself." on={sp.settings.voice_enabled === "1"}
              onChange={async (v) => { await api("/v3/settings", { key: "voice_enabled", value: v ? "1" : "0" }); reloadSpend(); }} />
            <Divider />
            <View style={{ paddingVertical: 10, gap: 8 }}>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Claude budget per day</Text>
                <Text style={{ color: C.text, fontWeight: "700" }}>${sp.today_usd.toFixed(2)} of ${sp.budget_usd.toFixed(2)}</Text>
              </View>
              <Progress value={sp.today_usd} of={sp.budget_usd || 1} color={sp.today_usd >= sp.budget_usd ? C.bad : C.accent} />
              <Segmented value={String(sp.budget_usd)} onChange={async (v) => { await api("/v3/settings", { key: "daily_budget_usd", value: v }); reloadSpend(); }}
                options={["0", "1", "2", "5", "10"].map((x) => ({ key: x, label: `$${x}` }))} />
              <T small>When today's budget is used up: {sp.settings.over_budget === "stop" ? "Claude stops until tomorrow." : "Gemini (free) answers instead."}
                {"  "}<Text style={{ color: C.accent }} onPress={async () => { await api("/v3/settings", { key: "over_budget", value: sp.settings.over_budget === "stop" ? "gemini" : "stop" }); reloadSpend(); }}>Change</Text></T>
              <Line label="This month" value={`$${sp.month_usd.toFixed(2)}`} />
              {Object.entries(sp.month).map(([k, v]: any) => <Line key={k} label={`  ${k}`} value={`${v.answers} answers · $${v.usd.toFixed(2)}`} />)}
              {sp.tests ? (
                <>
                  <Divider />
                  <Line label="Test Lab today (separate budget)" value={`$${sp.tests.today_usd.toFixed(2)} of $${sp.tests.budget_usd.toFixed(2)}`} />
                  <Line label="Test Lab this month" value={`$${sp.tests.month_usd.toFixed(2)}`} />
                </>
              ) : null}
            </View>
          </Card>
          </Spot>
        </>
      ) : null}

      <Card onPress={() => router.push("/testlab")} title="Test lab" sub="Recorded test runs of Ananta: answers from both models, voice, stability" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />
      <Card onPress={() => router.push("/mandate")} title="Your mandate" sub="Goals, markets, styles and limits Ananta follows" right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />

      <Spot id="cockpit.alerts">
      <Section title="Alerts" right={<T small>checked every 15 min · free</T>} />
      <Card>
        {(al?.alerts ?? []).filter((a: any) => a.status === "ACTIVE").length === 0 ? <T dim>No active alerts. Ask Ananta: "tell me if BTC drops below 80k".</T> : null}
        {(al?.alerts ?? []).filter((a: any) => a.status === "ACTIVE").map((a: any, i: number) => (
          <View key={a.id}>
            {i ? <Divider /> : null}
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8 }}>
              <Text style={{ color: C.text, flex: 1 }}>{a.what}{a.note ? ` · ${a.note}` : ""}</Text>
              <Text onPress={async () => { await api(`/v3/alerts/${a.id}/off`, {}); reloadAlerts(); }} style={{ color: C.bad, fontWeight: "600" }}>Turn off</Text>
            </View>
          </View>
        ))}
        {(al?.alerts ?? []).filter((a: any) => a.status === "FIRED").slice(0, 5).map((a: any) => (
          <T key={a.id} small>Fired: {a.message}</T>
        ))}
      </Card>
      </Spot>

      <Spot id="cockpit.systems">
      <Section title="Systems" />
      <Card>
        {d.systems.map((s: any, i: number) => (
          <View key={i}>
            {i ? <Divider /> : null}
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 9 }}>
              <Dot color={s.ok ? C.good : C.bad} />
              <Text style={{ color: C.text, fontSize: 15, flex: 1 }}>{s.label}</Text>
              <T small>{s.ok ? (s.last ? `last ${String(s.last).slice(11, 16)} UTC` : "running") : "not responding"}</T>
            </View>
          </View>
        ))}
      </Card>
      </Spot>

      {d.circuit_breakers && Object.keys(d.circuit_breakers).length ? (
        <>
          <Section title="Circuit breakers" />
          <Card>
            {Object.entries(d.circuit_breakers).map(([k, v]: any) => (
              <Line key={k} label={k.replace(".sqlite", "").replace(/_/g, " ")} value={v?.status ?? "OK"} color={v?.status === "TRIPPED" ? C.bad : C.good}
                sub={v?.reason ?? undefined} />
            ))}
          </Card>
        </>
      ) : null}

      <Card>
        <Text onPress={() => setShowActions(!showActions)} style={{ color: C.accent, fontWeight: "600" }}>
          {showActions ? "Hide recent actions" : "Show recent actions"}
        </Text>
        {showActions ? d.recent_actions.map((a: any, i: number) => (
          <View key={i}>
            <Divider />
            <Line label={`${a.action}${a.detail ? ` · ${a.detail}` : ""}`} value={a.result === "OK" ? "✓" : String(a.result).slice(0, 18)} sub={a.time} />
          </View>
        )) : null}
      </Card>
      {me && !me.guest ? (
        <Card title="People" sub={`Signed in as ${me.name} (${me.who}). Invite visitors and remove their accounts.`} onPress={() => router.push("/people")} />
      ) : null}
      <Btn label="Sign out" kind="secondary" onPress={async () => { await logout(); router.replace("/login"); }} />
    </Screen>
  );
}

function AiSwitch({ label, help, on, onChange }: { label: string; help: string; on: boolean; onChange: (v: boolean) => void }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 10 }}>
      <View style={{ flex: 1 }}>
        <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>{label}</Text>
        <T small>{help}</T>
      </View>
      <Switch value={on} onValueChange={onChange} trackColor={{ true: C.accent, false: C.line }} />
    </View>
  );
}
