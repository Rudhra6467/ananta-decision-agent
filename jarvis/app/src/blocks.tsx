// Shared building blocks (plan 2.6), so every screen says the same thing the same way:
//  · DecisionCard: what Ananta found, why, where it is wrong, what it is doing (every watch action writes one)
//  · StampChip: who took a trade (you, with your initials, or Ananta and which of its books)
//  · ExplainSheet: "Explain the data": a sheet from the bottom with the plain meaning of what is on screen
//  · DetailLayout: one layout for detail pages: key facts on top, the story in the middle, the technical part at the bottom
//  · showToast (from visitor.tsx): the confirmation pop-up that closes after 2 seconds and has a ✕
import React, { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C } from "./theme";
export { showToast } from "./visitor";

// a review's verdict in words, with the colour token that goes with it (colour is never the only signal)
export const VERDICT: Record<string, [string, string]> = { PASS: ["Passed", "good"], FAIL: ["No change", "dim"], INSUFFICIENT: ["Not enough data", "warn"] };

export type Decision = { found?: string; why?: string; wrong_if?: string; doing?: string };

export function DecisionCard({ card, title, time, children }: { card: Decision; title?: string; time?: string; children?: React.ReactNode }) {
  const rows: [string, string | undefined][] = [["Found", card.found], ["Why", card.why], ["Wrong if", card.wrong_if], ["Doing", card.doing]];
  return (
    <View style={{ backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 14, gap: 8 }}>
      {title || time ? (
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <Text style={{ color: C.text, fontWeight: "700", fontSize: 15, flex: 1 }}>{title}</Text>
          {time ? <Text style={{ color: C.faint, fontSize: 12 }}>{time}</Text> : null}
        </View>
      ) : null}
      {rows.filter(([, v]) => !!v).map(([k, v]) => (
        <View key={k} style={{ flexDirection: "row", gap: 10 }}>
          <Text style={{ color: C.dim, fontSize: 12, fontWeight: "700", width: 64, paddingTop: 1 }}>{k.toUpperCase()}</Text>
          <Text style={{ color: C.text, fontSize: 14, lineHeight: 20, flex: 1 }}>{v}</Text>
        </View>
      ))}
      {children}
    </View>
  );
}

export type Stamp = { who: "you" | "ananta" | string; label: string; source?: string };

export function StampChip({ stamp, small }: { stamp: Stamp; small?: boolean }) {
  const mine = stamp.who === "you";
  return (
    <View accessibilityLabel={`Taken by ${mine ? "you" : "Ananta"}: ${stamp.label}`}
      style={{ flexDirection: "row", alignItems: "center", gap: 5, alignSelf: "flex-start", borderRadius: 999,
        paddingHorizontal: small ? 7 : 9, paddingVertical: small ? 2 : 3, backgroundColor: mine ? C.card2 : C.accentSoft,
        borderWidth: 1, borderColor: mine ? C.line : C.accentSoft }}>
      <Text style={{ fontSize: small ? 10 : 11 }}>{mine ? "👤" : "✦"}</Text>
      <Text style={{ color: mine ? C.text : C.accent, fontSize: small ? 11 : 12, fontWeight: "700" }} numberOfLines={1}>{stamp.label}</Text>
    </View>
  );
}

export function ExplainSheet({ open, onClose, title, children }: { open: boolean; onClose: () => void; title: string; children: React.ReactNode }) {
  const bottom = useSafeAreaInsets().bottom;
  return (
    <Modal visible={open} transparent animationType="slide" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.35)" }} accessibilityLabel="Close" />
      <View style={{ backgroundColor: C.card, borderTopLeftRadius: 20, borderTopRightRadius: 20, maxHeight: "75%", paddingBottom: bottom + 12 }}>
        <View style={{ alignItems: "center", paddingTop: 8 }}><View style={{ width: 36, height: 4, borderRadius: 2, backgroundColor: C.line }} /></View>
        <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 18, paddingTop: 10, paddingBottom: 6 }}>
          <Text style={{ color: C.text, fontSize: 17, fontWeight: "700", flex: 1 }}>{title}</Text>
          <Pressable onPress={onClose} hitSlop={12} accessibilityLabel="Close"><Text style={{ color: C.dim, fontSize: 18 }}>✕</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={{ paddingHorizontal: 18, paddingBottom: 12, gap: 10 }}>{children}</ScrollView>
      </View>
    </Modal>
  );
}

// a small "Explain the data" link that opens the sheet
export function ExplainLink({ title, children, label = "Explain the data" }: { title: string; children: React.ReactNode; label?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <>
      <Text onPress={() => setOpen(true)} style={{ color: C.accent, fontWeight: "600", fontSize: 13 }}>ⓘ {label}</Text>
      <ExplainSheet open={open} onClose={() => setOpen(false)} title={title}>{children}</ExplainSheet>
    </>
  );
}

export function DetailLayout({ facts, children, technical }: {
  facts: { label: string; value: React.ReactNode; color?: string }[]; children?: React.ReactNode; technical?: React.ReactNode;
}) {
  const [tech, setTech] = useState(false);
  return (
    <View style={{ gap: 14 }}>
      <View style={{ flexDirection: "row", flexWrap: "wrap", backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 6 }}>
        {facts.map((f, i) => (
          <View key={i} style={{ width: "50%", padding: 10, gap: 2 }}>
            <Text style={{ color: C.dim, fontSize: 12 }}>{f.label}</Text>
            <Text style={{ color: f.color ?? C.text, fontSize: 17, fontWeight: "700" }}>{f.value}</Text>
          </View>
        ))}
      </View>
      {children}
      {technical ? (
        <View style={{ gap: 10 }}>
          <Text onPress={() => setTech(!tech)} style={{ color: C.dim, fontWeight: "600", fontSize: 13 }}>{tech ? "▾ Hide the technical part" : "▸ The technical part"}</Text>
          {tech ? technical : null}
        </View>
      ) : null}
    </View>
  );
}
