import React, { useCallback, useRef, useState } from "react";
import { useFocusEffect } from "expo-router";
import { setScroller } from "./spotlight";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { C, pnlColor } from "./theme";

export function Screen({ children, loading, onRefresh, pad = true }: { children: React.ReactNode; loading: boolean; onRefresh: () => void; pad?: boolean }) {
  const ref = useRef<ScrollView>(null);
  const st = useRef({ offset: { y: 0 }, height: { h: 0 }, content: { h: 0 } }).current;
  useFocusEffect(useCallback(() => { setScroller({ ref, ...st }); return () => {}; }, []));
  return (
    <ScrollView ref={ref} style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: pad ? 16 : 0, gap: 14, paddingBottom: 40 }}
      onScroll={(e) => { st.offset.y = e.nativeEvent.contentOffset.y; }} scrollEventThrottle={64}
      onLayout={(e) => { st.height.h = e.nativeEvent.layout.height; }} onContentSizeChange={(_, h) => { st.content.h = h; }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={onRefresh} tintColor={C.dim} />}>
      {children}
    </ScrollView>
  );
}

export function Card({ title, children, right, sub, onPress }: { title?: string; sub?: string; children?: React.ReactNode; right?: React.ReactNode; onPress?: () => void }) {
  const body = (
    <View style={s.card}>
      {title ? (
        <View style={[s.row, { marginBottom: 2 }]}>
          <View style={{ flex: 1 }}>
            <Text style={s.h}>{title}</Text>
            {sub ? <Text style={s.small}>{sub}</Text> : null}
          </View>
          {right}
        </View>
      ) : null}
      {children}
    </View>
  );
  return onPress ? <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.75 : 1 })}>{body}</Pressable> : body;
}

export const Section = ({ title, right }: { title: string; right?: React.ReactNode }) => (
  <View style={[s.row, { marginTop: 6, paddingHorizontal: 2 }]}>
    <Text style={s.section}>{title}</Text>
    {right}
  </View>
);

export function Line({ label, value, color, sub }: { label: string; value: React.ReactNode; color?: string; sub?: string }) {
  return (
    <View style={[s.row, { paddingVertical: 4 }]}>
      <View style={{ flex: 1 }}>
        <Text style={s.dim}>{label}</Text>
        {sub ? <Text style={s.small}>{sub}</Text> : null}
      </View>
      <Text style={[s.t, { fontWeight: "600" }, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

// A tappable list row (brokerage style): left title/sub, right value/sub, chevron.
export function Row({ title, sub, value, valueSub, valueColor, valueSubColor, onPress, onLongPress, left }: {
  title: string; sub?: string; value?: string; valueSub?: string; valueColor?: string; valueSubColor?: string; onPress?: () => void; onLongPress?: () => void; left?: React.ReactNode;
}) {
  return (
    <Pressable onPress={onPress} onLongPress={onLongPress} delayLongPress={350} disabled={!onPress && !onLongPress} style={({ pressed }) => [s.rowItem, { opacity: pressed ? 0.6 : 1 }]}>
      {left}
      <View style={{ flex: 1 }}>
        <Text style={s.rowTitle}>{title}</Text>
        {sub ? <Text style={s.small} numberOfLines={2}>{sub}</Text> : null}
      </View>
      <View style={{ alignItems: "flex-end" }}>
        {value ? <Text style={[s.rowTitle, valueColor ? { color: valueColor } : null]}>{value}</Text> : null}
        {valueSub ? <Text style={[s.small, valueSubColor ? { color: valueSubColor } : null]}>{valueSub}</Text> : null}
      </View>
      {onPress ? <Text style={{ color: C.faint, fontSize: 18, marginLeft: 6 }}>›</Text> : null}
    </Pressable>
  );
}

export const Divider = () => <View style={{ height: 1, backgroundColor: C.line }} />;

export function Btn({ label, onPress, kind = "primary", small }: { label: string; onPress: () => void; kind?: "primary" | "secondary" | "danger"; small?: boolean }) {
  const bg = kind === "primary" ? C.accent : kind === "danger" ? C.bad : C.card;
  const fg = kind === "secondary" ? C.text : "#FFFFFF";
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [s.btn, small && { paddingVertical: 7, paddingHorizontal: 12 },
      { backgroundColor: bg, borderColor: kind === "secondary" ? C.line : bg, opacity: pressed ? 0.7 : 1 }]}>
      <Text style={[s.btnT, { color: fg }, small && { fontSize: 13 }]}>{label}</Text>
    </Pressable>
  );
}

export const T = ({ children, dim, small, style, numberOfLines }: { children: React.ReactNode; dim?: boolean; small?: boolean; style?: any; numberOfLines?: number }) => (
  <Text numberOfLines={numberOfLines} style={[small ? s.small : dim ? s.dim : s.t, style]}>{children}</Text>
);

export function Big({ value, label, change, changeLabel }: { value: string; label?: string; change?: number | null; changeLabel?: string }) {
  return (
    <View style={{ gap: 2 }}>
      {label ? <Text style={s.dim}>{label}</Text> : null}
      <Text style={s.big}>{value}</Text>
      {changeLabel ? <Text style={[s.t, { color: pnlColor(change), fontWeight: "600" }]}>{changeLabel}</Text> : null}
    </View>
  );
}

export function Stat({ label, value, sub, color }: { label: string; value: React.ReactNode; sub?: string; color?: string }) {
  return (
    <View style={{ flex: 1, gap: 2 }}>
      <Text style={s.small}>{label}</Text>
      <Text style={[s.statV, color ? { color } : null]}>{value}</Text>
      {sub ? <Text style={s.small}>{sub}</Text> : null}
    </View>
  );
}

export function Pill({ text, color = C.dim, bg = C.card2 }: { text: string; color?: string; bg?: string }) {
  return (
    <View style={{ backgroundColor: bg, borderRadius: 6, paddingHorizontal: 7, paddingVertical: 2, alignSelf: "flex-start" }}>
      <Text style={{ color, fontSize: 11, fontWeight: "700", letterSpacing: 0.3 }}>{text}</Text>
    </View>
  );
}
export const Chip = ({ text, color }: { text: string; color: string }) => <Pill text={text} color={color} />;

export function Segmented({ options, value, onChange }: { options: { key: string; label: string }[]; value: string; onChange: (k: string) => void }) {
  return (
    <View style={s.seg}>
      {options.map((o) => (
        <Pressable key={o.key} onPress={() => onChange(o.key)} style={[s.segI, value === o.key && s.segOn]}>
          <Text style={{ color: value === o.key ? C.text : C.dim, fontWeight: "600", fontSize: 13 }}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

// Tap to open: keeps long explanations out of the way until asked for.
export function Expand({ title, sub, right, children, start = false, onLongPress }: { title: string; sub?: string; right?: React.ReactNode; children: React.ReactNode; start?: boolean; onLongPress?: () => void }) {
  const [open, setOpen] = useState(start);
  return (
    <View>
      <Pressable onPress={() => setOpen(!open)} onLongPress={onLongPress} delayLongPress={350} style={[s.rowItem]}>
        <View style={{ flex: 1 }}>
          <Text style={s.rowTitle}>{title}</Text>
          {sub ? <Text style={s.small}>{sub}</Text> : null}
        </View>
        {right}
        <Text style={{ color: C.faint, fontSize: 14, marginLeft: 8 }}>{open ? "▲" : "▼"}</Text>
      </Pressable>
      {open ? <View style={{ paddingBottom: 10, gap: 6 }}>{children}</View> : null}
    </View>
  );
}

export const Bullet = ({ children }: { children: React.ReactNode }) => (
  <View style={{ flexDirection: "row", gap: 8 }}>
    <Text style={s.dim}>•</Text>
    <Text style={[s.t, { flex: 1, lineHeight: 20 }]}>{children}</Text>
  </View>
);

export const Dot = ({ color }: { color: string }) => <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />;

export const Busy = () => <ActivityIndicator color={C.dim} style={{ marginTop: 60 }} />;
export const ErrorBox = ({ err }: { err: string }) => (
  <View style={[s.card, { backgroundColor: C.badSoft, borderColor: C.badSoft }]}><Text style={{ color: C.bad }}>{err}</Text></View>
);

export const usd = (x?: number | null, d = 2) =>
  x == null ? "–" : `${x < 0 ? "-" : ""}$${Math.abs(x).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const usdSigned = (x?: number | null) => (x == null ? "–" : `${x >= 0 ? "+" : "-"}$${Math.abs(x).toFixed(2)}`);
export const pct = (x?: number | null) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${x.toFixed(2)}%`);
export const price = (x?: number | null) =>
  x == null ? "–" : x >= 10 ? `$${x.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : x >= 0.1 ? `$${x.toFixed(4)}` : `$${x.toFixed(5)}`;

export const s = StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: 14, padding: 16, gap: 8, borderWidth: 1, borderColor: C.line },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  rowItem: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 11 },
  rowTitle: { color: C.text, fontSize: 15, fontWeight: "600" },
  h: { color: C.text, fontSize: 16, fontWeight: "700" },
  section: { color: C.dim, fontSize: 12, fontWeight: "700", letterSpacing: 0.8, textTransform: "uppercase" },
  big: { color: C.text, fontSize: 32, fontWeight: "700", letterSpacing: -0.5 },
  statV: { color: C.text, fontSize: 17, fontWeight: "700" },
  t: { color: C.text, fontSize: 14 },
  dim: { color: C.dim, fontSize: 14 },
  small: { color: C.dim, fontSize: 12, lineHeight: 16 },
  btn: { paddingVertical: 11, paddingHorizontal: 16, borderRadius: 10, alignItems: "center", borderWidth: 1 },
  btnT: { fontWeight: "700", fontSize: 15 },
  seg: { flexDirection: "row", backgroundColor: C.card2, borderRadius: 10, padding: 3 },
  segI: { flex: 1, alignItems: "center", paddingVertical: 8, borderRadius: 8 },
  segOn: { backgroundColor: C.card, shadowColor: "#000", shadowOpacity: 0.08, shadowRadius: 3, shadowOffset: { width: 0, height: 1 } },
});
