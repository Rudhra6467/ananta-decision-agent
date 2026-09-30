import { Alert, View } from "react-native";
import { router } from "expo-router";
import { api, logout } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { registerPush } from "../../src/push";
import { Btn, Busy, Card, Line, Screen, T } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";

export default function Safety() {
  const { data: d, err, loading, reload } = useData("/safety");
  const kill = async (on: boolean) => {
    const msg = on ? "Stops all new entries and closes every open Hands position at market." : "Allows entries again.";
    if (!(await confirmWithFaceId(on ? "Turn kill switch ON" : "Turn kill switch OFF", msg))) return;
    try { await api("/safety/kill", { on, confirm: true }); reload(); } catch (e: any) { Alert.alert("Failed", e.message); }
  };
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><T style={{ color: C.bad }}>{err}</T></Screen>;
  const kOn = d.kill_switch_on;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card title="Kill switch" right={<T style={{ color: kOn ? C.bad : C.good, fontWeight: "800" }}>{kOn == null ? "UNKNOWN" : kOn ? "ON" : "off"}</T>}>
        {kOn ? <Btn label="Turn OFF" kind="good" onPress={() => kill(false)} /> : <Btn label="Turn ON (stop everything)" kind="bad" onPress={() => kill(true)} />}
      </Card>
      <Card title="System">
        <Line label="Trading" value={d.paper_only ? "PAPER ONLY" : "LIVE"} color={C.warn} />
        <Line label="Hands reachable" value={d.hands_reachable ? "yes" : "NO"} color={d.hands_reachable ? C.good : C.bad} />
        <Line label="Explorer last scan" value={d.explorer_last_scan ?? "–"} color={d.explorer_stale ? C.bad : undefined} />
        <Line label="Hourly watch last" value={String(d.hourly_watch_last ?? "–").slice(0, 16).replace("T", " ")} />
      </Card>
      <Card title="Circuit breakers">
        {Object.keys(d.circuit_breakers).length === 0 ? <T dim>None tripped.</T> : Object.entries(d.circuit_breakers).map(([k, v]: any) => (
          <Line key={k} label={k} value={v.status ?? JSON.stringify(v).slice(0, 40)} color={v.status === "TRIPPED" ? C.bad : C.good} />
        ))}
      </Card>
      <Card title="Recent actions (audit log)">
        {d.recent_actions.map((a: any, i: number) => (
          <View key={i}><T>{a.action} {a.detail ? `· ${a.detail}` : ""}</T><T dim>{a.time} · {a.result}</T></View>
        ))}
      </Card>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <Btn label="Set up push" onPress={async () => Alert.alert("Push", await registerPush())} />
        <Btn label="Sign out" onPress={async () => { await logout(); router.replace("/login"); }} />
      </View>
    </Screen>
  );
}
