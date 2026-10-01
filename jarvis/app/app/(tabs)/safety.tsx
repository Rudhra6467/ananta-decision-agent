import { Alert, View } from "react-native";
import { router } from "expo-router";
import { api, logout } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { registerPush } from "../../src/push";
import { Btn, Busy, Card, Chip, Line, Screen, T, Tile } from "../../src/ui";
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
  const allGood = kOn === false && d.hands_reachable && !d.explorer_stale;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card>
        <T dim>System status</T>
        <T style={{ fontSize: 26, fontWeight: "800", color: allGood ? C.good : C.warn }}>{allGood ? "All normal" : "Needs a look"}</T>
        <T dim>Paper only · no real money connected</T>
      </Card>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        <Tile label="Kill switch" value={kOn == null ? "?" : kOn ? "ON" : "off"} color={kOn ? C.bad : C.good} />
        <Tile label="Hands" value={d.hands_reachable ? "up" : "DOWN"} color={d.hands_reachable ? C.good : C.bad} />
        <Tile label="Explorer" value={d.explorer_stale ? "stale" : "live"} sub={d.explorer_last_scan ?? ""} color={d.explorer_stale ? C.bad : C.good} />
        <Tile label="Hourly watch" value="live" sub={String(d.hourly_watch_last ?? "–").slice(0, 16).replace("T", " ")} color={C.good} />
      </View>
      <Card title="Kill switch" right={<Chip text={kOn ? "ON" : "off"} color={kOn ? C.bad : C.good} />}>
        <T dim>{kOn ? "Everything is stopped." : "Use only if something looks wrong. It stops new entries and closes open Hands positions."}</T>
        {kOn ? <Btn label="Turn OFF" kind="good" onPress={() => kill(false)} /> : <Btn label="Turn ON (stop everything)" kind="bad" onPress={() => kill(true)} />}
      </Card>
      <Card title="Circuit breakers">
        {Object.keys(d.circuit_breakers).length === 0 ? <T dim>None tripped.</T> : Object.entries(d.circuit_breakers).map(([k, v]: any) => (
          <Line key={k} label={k.replace(".sqlite", "")} value={v.status ?? "–"} color={v.status === "TRIPPED" ? C.bad : C.good} />
        ))}
      </Card>
      <Card title="Recent actions">
        {d.recent_actions.map((a: any, i: number) => (
          <View key={i} style={{ borderTopWidth: i ? 1 : 0, borderTopColor: C.line, paddingTop: i ? 6 : 0 }}>
            <T>{a.action}{a.detail ? ` · ${a.detail}` : ""}</T>
            <T dim style={{ fontSize: 11 }}>{a.time} · {a.result}</T>
          </View>
        ))}
      </Card>
      <View style={{ flexDirection: "row", gap: 8 }}>
        <Btn label="Set up push" onPress={async () => Alert.alert("Push", await registerPush())} />
        <Btn label="Sign out" onPress={async () => { await logout(); router.replace("/login"); }} />
      </View>
    </Screen>
  );
}
