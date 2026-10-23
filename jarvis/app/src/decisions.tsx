// Ananta's recent decisions on Home (Madhav, 23 Oct): two or three lines a person reads in seconds ("Bought Bitcoin at … because …"),
// Show more to the decisions page, a tap opens a small popup with the whole message (close, or the chat mark to talk it over in
// Ask Ananta); a tap anywhere outside the popup goes back to Home. Both markets: each backend answers /v3/decisions/recent.
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { router } from "expo-router";
import { askAbout } from "./context";
import { useData } from "./useData";
import { Act, Card, Divider, Dot, ListState, T, s as st } from "./ui";
import { C, RADIUS, SPACE, TYPE } from "./theme";
import { VoiceIcon } from "./icons";

type Decision = { id: string; t: number; time: string; coin: string | null; action: string; headline: string; message: string; link?: string };
const COLOR: Record<string, string> = { TAKE: C.accent, PASS: C.faint, CALL: C.warn };

export function RecentDecisions() {
  const { data: d, err, loading } = useData("/v3/decisions/recent?n=10", 60000);
  const [open, setOpen] = useState<Decision | null>(null);
  const rows: Decision[] = (d?.decisions ?? []).slice(0, 3);
  return (
    <Card>
      <View style={st.row}>
        <Text style={st.h}>Ananta's decisions</Text>
        <Act tight label="Show more ›" onPress={() => router.push((d?.page ?? "/jarvis") as any)} />
      </View>
      {!d && loading ? <T dim>Reading the decisions…</T> : null}
      {err && !d ? <ListState state="error" text={err} /> : null}
      {d && rows.length === 0 ? <ListState state="empty" text="No decisions recorded yet." /> : null}
      {rows.map((r, i) => (
        <View key={r.id}>
          {i ? <Divider /> : null}
          <Pressable onPress={() => setOpen(r)} accessibilityRole="button" accessibilityLabel={`${r.headline}. Tap to read the whole message`}
            style={{ flexDirection: "row", gap: 12, paddingVertical: 10 }}>
            <View style={{ paddingTop: 6 }}><Dot color={COLOR[r.action] ?? C.faint} /></View>
            <View style={{ flex: 1, gap: 2 }}>
              <Text style={{ color: C.text, fontSize: TYPE.body, lineHeight: 21 }} numberOfLines={2}>{r.headline}</Text>
              <T small>{r.time}{r.action === "PASS" ? " · no trade" : ""}</T>
            </View>
            <Text style={{ color: C.dim, fontSize: 18, alignSelf: "center" }}>›</Text>
          </Pressable>
        </View>
      ))}
      <DecisionPopup d={open} onClose={() => setOpen(null)} />
    </Card>
  );
}

function DecisionPopup({ d, onClose }: { d: Decision | null; onClose: () => void }) {
  if (!d) return null;
  const talk = () => {
    onClose();
    askAbout({ screen: "decision", label: d.headline, coin: d.coin ?? undefined, id: d.id, item: d }, `Let's talk about this decision: ${d.headline}`);
  };
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} accessibilityRole="button" accessibilityLabel="Close" style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: SPACE.screen }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: RADIUS.card, borderWidth: 1, borderColor: C.line, padding: SPACE.card + 2, maxHeight: "80%", maxWidth: 560, width: "100%", alignSelf: "center" }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
            <Dot color={COLOR[d.action] ?? C.faint} />
            <Text style={{ color: C.text, fontWeight: "800", fontSize: TYPE.card, flex: 1 }} numberOfLines={3}>{d.headline}</Text>
            <Pressable onPress={onClose} hitSlop={10} accessibilityRole="button" accessibilityLabel="Close"
              style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: C.card2, alignItems: "center", justifyContent: "center" }}>
              <Text style={{ color: C.text, fontWeight: "800", fontSize: 16 }}>✕</Text>
            </Pressable>
          </View>
          <T small>{d.time}</T>
          <ScrollView style={{ marginTop: 10 }} contentContainerStyle={{ paddingBottom: 6 }}>
            {d.message.split("\n").filter(Boolean).map((line, i) => <Text key={i} style={{ color: C.text, fontSize: TYPE.body, lineHeight: 22, marginBottom: 6 }}>{line}</Text>)}
          </ScrollView>
          <View style={{ flexDirection: "row", gap: 10, marginTop: 8 }}>
            <Pressable onPress={talk} accessibilityRole="button" accessibilityLabel="Discuss this decision with Ananta"
              style={{ flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: C.accent, borderRadius: RADIUS.button, paddingVertical: 10, paddingHorizontal: 14 }}>
              <VoiceIcon color={C.bg} />
              <Text style={{ color: C.bg, fontWeight: "800" }}>Talk it over</Text>
            </Pressable>
            {d.link ? <Act label="Open ›" onPress={() => { onClose(); router.push(d.link as any); }} /> : null}
          </View>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
