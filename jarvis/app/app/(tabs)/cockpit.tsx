import { useState } from "react";
import { Alert, Switch, Text, View } from "react-native";
import { router } from "expo-router";
import { api, logout } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { Btn, Busy, Card, Divider, Dot, ErrorBox, Line, Screen, Section, T } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";

export default function Cockpit() {
  const { data: d, err, loading, reload } = useData("/v3/cockpit");
  const [showActions, setShowActions] = useState(false);
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
      <Btn label="Sign out" kind="secondary" onPress={async () => { await logout(); router.replace("/login"); }} />
    </Screen>
  );
}
