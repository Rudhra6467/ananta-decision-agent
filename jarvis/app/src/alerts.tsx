// The alerts bell beside the Cockpit title (plan 3.8): a count of active alerts; a tap shows them, with Turn off, and the
// ones that fired recently.
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { api } from "./api";
import { ExplainSheet } from "./blocks";
import { C } from "./theme";
import { Divider, T } from "./ui";
import { useData } from "./useData";

export function AlertsBell() {
  const [open, setOpen] = useState(false);
  const { data: al, reload } = useData("/v3/alerts", 60000);
  const active = (al?.alerts ?? []).filter((a: any) => a.status === "ACTIVE");
  const fired = (al?.alerts ?? []).filter((a: any) => a.status === "FIRED").slice(0, 5);
  return (
    <>
      <Pressable onPress={() => { setOpen(true); reload(); }} hitSlop={10} accessibilityLabel={`Alerts: ${active.length} active`}
        style={{ width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center", backgroundColor: C.card2, borderWidth: 1, borderColor: C.line }}>
        <Text style={{ fontSize: 15, color: C.text }}>🔔</Text>
        {active.length ? (
          <View style={{ position: "absolute", top: -3, right: -3, minWidth: 16, height: 16, borderRadius: 8, backgroundColor: C.accent, alignItems: "center", justifyContent: "center", paddingHorizontal: 3 }}>
            <Text style={{ color: C.onInk, fontSize: 10, fontWeight: "800" }}>{active.length}</Text>
          </View>
        ) : null}
      </Pressable>
      <ExplainSheet open={open} onClose={() => setOpen(false)} title="Alerts">
        <T small dim>Checked every 15 minutes, free. Ask Ananta: “tell me if Bitcoin drops below 80,000”.</T>
        {active.length === 0 ? <T dim>No active alerts.</T> : null}
        {active.map((a: any, i: number) => (
          <View key={a.id}>
            {i ? <Divider /> : null}
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8 }}>
              <Text style={{ color: C.text, flex: 1, fontSize: 15 }}>{a.what}{a.note ? ` · ${a.note}` : ""}</Text>
              <Text onPress={async () => { await api(`/v3/alerts/${a.id}/off`, {}); reload(); }} style={{ color: C.bad, fontWeight: "600" }}>Turn off</Text>
            </View>
          </View>
        ))}
        {fired.length ? <Text style={{ color: C.text, fontWeight: "700", marginTop: 6 }}>Fired recently</Text> : null}
        {fired.map((a: any) => <T key={a.id} small>{a.message}</T>)}
      </ExplainSheet>
    </>
  );
}
