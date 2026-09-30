import React from "react";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { C } from "./theme";

export function Screen({ children, loading, onRefresh }: { children: React.ReactNode; loading: boolean; onRefresh: () => void }) {
  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: 14, gap: 12 }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={onRefresh} tintColor={C.dim} />}>
      {children}
    </ScrollView>
  );
}
export function Card({ title, children, right }: { title?: string; children: React.ReactNode; right?: React.ReactNode }) {
  return (
    <View style={s.card}>
      {title ? <View style={s.row}><Text style={s.h}>{title}</Text>{right}</View> : null}
      {children}
    </View>
  );
}
export function Line({ label, value, color }: { label: string; value: React.ReactNode; color?: string }) {
  return (
    <View style={s.row}><Text style={s.dim}>{label}</Text><Text style={[s.t, color ? { color } : null]}>{value}</Text></View>
  );
}
export function Btn({ label, onPress, kind = "normal" }: { label: string; onPress: () => void; kind?: "normal" | "good" | "bad" }) {
  const bg = kind === "good" ? C.good : kind === "bad" ? C.bad : C.accent;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [s.btn, { backgroundColor: bg, opacity: pressed ? 0.7 : 1 }]}>
      <Text style={s.btnT}>{label}</Text>
    </Pressable>
  );
}
export const T = ({ children, dim, style }: { children: React.ReactNode; dim?: boolean; style?: any }) => (
  <Text style={[dim ? s.dim : s.t, style]}>{children}</Text>
);
export const Busy = () => <ActivityIndicator color={C.dim} style={{ marginTop: 40 }} />;
export const usd = (x?: number | null) => (x == null ? "–" : `$${x.toLocaleString(undefined, { maximumFractionDigits: 2 })}`);
export const pct = (x?: number | null) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${x.toFixed(2)}%`);

const s = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 12, padding: 14, gap: 8, borderWidth: 1, borderColor: C.line },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  h: { color: C.text, fontSize: 16, fontWeight: "700" },
  t: { color: C.text, fontSize: 14 },
  dim: { color: C.dim, fontSize: 13 },
  btn: { paddingVertical: 10, paddingHorizontal: 14, borderRadius: 10, alignItems: "center" },
  btnT: { color: "#0A0E17", fontWeight: "700" },
});
