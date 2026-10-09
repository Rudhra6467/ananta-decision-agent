// Shared by Chat, Voice and Home: confirmation cards for things Ananta prepared, and opening a screen Ananta pointed to.
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { api } from "./api";
import { confirmWithFaceId } from "./guard";
import { showToast } from "./visitor";
import { goTab } from "./context";
import { C } from "./theme";
import { DecisionCard } from "./blocks";

export function openScreen(sh: any) {
  const to: Record<string, string> = { markets: "/(tabs)/watchlists", portfolio: "/(tabs)/portfolio", evidence: "/lab",
    cockpit: "/(tabs)/cockpit", mandate: "/mandate", home: "/(tabs)/today", jarvis: "/jarvis", missed: "/missed" };
  if (sh.screen === "coin" && sh.coin) router.push(`/coin/${sh.coin}`);
  else if (sh.screen === "trade" && sh.id) router.push(`/trade/${sh.id}`);
  else if (to[sh.screen]) (to[sh.screen].startsWith("/(tabs)") ? goTab : router.push)(to[sh.screen] as any);   // a tab: switch to it, never stack a copy
}

export function ActionCard({ a, onDone }: { a: any; onDone?: () => void }) {
  const [status, setStatus] = useState<string>(a.status ?? "PENDING");
  const [err, setErr] = useState<string | null>(null);
  const decide = async (confirm: boolean) => {
    if (confirm && !(await confirmWithFaceId("Confirm", a.summary))) return;
    try {
      const r = await api(`/v3/actions/${a.id}`, { confirm });
      setStatus(r.status);
      if (confirm && r.status === "DONE") showToast(a.kind === "paper_order" ? "Order placed ✓" : "Done ✓");
      onDone?.();
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    }
  };
  return (
    <View style={{ borderWidth: 1, borderColor: C.accent, borderRadius: 12, padding: 12, gap: 8, backgroundColor: C.accentSoft }}>
      <Text style={{ color: C.accent, fontSize: 11, fontWeight: "700", letterSpacing: 0.6 }}>NEEDS YOUR OK</Text>
      <Text style={{ color: C.text, fontSize: 14 }}>{a.summary}</Text>
      {a.card ? <DecisionCard card={a.card} /> : null}
      {a.expires_t && status === "PENDING" ? (
        <Text style={{ color: C.dim, fontSize: 12 }}>Expires at {new Date(a.expires_t * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}; the price is checked again when you confirm.</Text>
      ) : null}
      {status === "PENDING" ? (
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Pressable onPress={() => decide(false)} style={{ flex: 1, borderWidth: 1, borderColor: C.line, backgroundColor: C.card, borderRadius: 8, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.text, fontWeight: "600" }}>Cancel</Text>
          </Pressable>
          <Pressable onPress={() => decide(true)} style={{ flex: 1, backgroundColor: C.accent, borderRadius: 8, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.onInk, fontWeight: "700" }}>Confirm</Text>
          </Pressable>
        </View>
      ) : <Text style={{ color: status === "DONE" ? C.good : C.dim, fontWeight: "600" }}>{status === "DONE" ? "✓ Done" : "Cancelled"}</Text>}
      {err ? <Text style={{ color: C.bad, fontSize: 12 }}>{err}</Text> : null}
    </View>
  );
}

