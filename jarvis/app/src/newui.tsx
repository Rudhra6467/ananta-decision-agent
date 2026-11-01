// The redesign's building blocks (the "Ananta" design system, claude/design-2026-10-31-phase2-3-design-system-and-screens.md): the tokens
// on top of the existing palettes (C), and the seven components as drawn on the canvas: NumberTile, BookRow, GradeChip, VoiceLine,
// DecisionCard, Btn, and the orb. Dark is the default; every colour comes from C so the light theme still works.
import { Pressable, Text, View, type ViewStyle } from "react-native";
import Svg, { Circle, Path, Rect } from "react-native-svg";
import { C } from "./theme";

// tokens the palettes do not carry yet (gold is C.accent in Bat, blue in Light: here the brand is gold in both)
export const G = {
  gold: () => C.gold, goldSoft: () => C.goldSoft, onGold: () => C.onGold, twin: () => C.twin, glow: () => C.glow,
};
export const TY = {
  hero: { fontSize: 40, lineHeight: 44, fontWeight: "700" as const, letterSpacing: -0.8, fontVariant: ["tabular-nums"] as any },
  number: { fontSize: 32, lineHeight: 38, fontWeight: "700" as const, letterSpacing: -0.5, fontVariant: ["tabular-nums"] as any },
  figure: { fontSize: 17, lineHeight: 24, fontWeight: "600" as const, fontVariant: ["tabular-nums"] as any },
  title: { fontSize: 24, lineHeight: 30, fontWeight: "700" as const, letterSpacing: -0.2 },
  spoken: { fontSize: 19, lineHeight: 28, fontWeight: "500" as const },
  card: { fontSize: 17, lineHeight: 24, fontWeight: "600" as const },
  body: { fontSize: 15, lineHeight: 22, fontWeight: "400" as const },
  meta: { fontSize: 13, lineHeight: 18, fontWeight: "600" as const },
  tab: { fontSize: 11, lineHeight: 14, fontWeight: "700" as const, letterSpacing: 0.3 },
};

export const Meta = ({ children, faint, color, style, numberOfLines }: { children: React.ReactNode; faint?: boolean; color?: string; style?: any; numberOfLines?: number }) => (
  <Text style={[TY.meta, { color: color ?? (faint ? C.faint : C.dim) }, style]} numberOfLines={numberOfLines}>{children}</Text>
);
export const Body = ({ children, dim, style, numberOfLines }: { children: React.ReactNode; dim?: boolean; style?: any; numberOfLines?: number }) => (
  <Text style={[TY.body, { color: dim ? C.dim : C.text }, style]} numberOfLines={numberOfLines}>{children}</Text>
);
export const H = ({ children, style }: { children: React.ReactNode; style?: any }) => <Text style={[TY.card, { color: C.text }, style]}>{children}</Text>;
export const Title = ({ children }: { children: React.ReactNode }) => <Text style={[TY.title, { color: C.text }]}>{children}</Text>;

export function NCard({ children, style, onPress, pad = 16 }: { children: React.ReactNode; style?: ViewStyle; onPress?: () => void; pad?: number }) {
  const inner = <View style={[{ backgroundColor: C.card, borderRadius: 16, padding: pad }, style]}>{children}</View>;
  return onPress ? <Pressable onPress={onPress} accessibilityRole="button">{inner}</Pressable> : inner;
}

export function NumberTile({ label, value, sub, tone }: { label: string; value: string; sub?: string; tone?: "good" | "bad" }) {
  return (
    <NCard style={{ flex: 1 }}>
      <Meta>{label}</Meta>
      <Text style={[TY.number, value.length > 7 ? { fontSize: 26, lineHeight: 34 } : null, { color: tone === "good" ? C.good : tone === "bad" ? C.bad : C.text, marginTop: 4 }]} numberOfLines={1}>{value}</Text>
      {sub ? <Meta faint style={{ marginTop: 4 }}>{sub}</Meta> : null}
    </NCard>
  );
}

const pctWords = (p: number | null | undefined) => (p == null ? null : `${p > 0 ? "+" : ""}${p.toFixed(2)}%`);
export function BookRow({ books, clock, note }: { books: { id: string; label: string; ret_pct?: number | null; words?: string | null }[]; clock?: string | null; note?: string }) {
  const colorOf: Record<string, string> = { yours: C.dim, twin: G.twin(), managed: G.gold(), index: C.faint };
  return (
    <NCard>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}>
        <H>Four books, one start</H>
        {clock ? <Meta>{clock}</Meta> : null}
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 12 }}>
        {books.map((b) => {
          const v = b.words ?? pctWords(b.ret_pct) ?? "—";
          return (
            <View key={b.id} style={{ flexBasis: "47%", flexGrow: 1, backgroundColor: C.card2, borderRadius: 12, padding: 10, borderTopWidth: 3, borderTopColor: colorOf[b.id] ?? C.dim, borderStyle: b.id === "index" ? "dashed" : "solid" }}>
              <Meta numberOfLines={1}>{b.label}</Meta>
              <Text style={[TY.figure, { color: b.ret_pct != null ? (b.ret_pct > 0 ? C.good : b.ret_pct < 0 ? C.bad : C.text) : C.text, marginTop: 2 }]} numberOfLines={1}>{v}</Text>
            </View>
          );
        })}
      </View>
      {note ? <Meta faint style={{ marginTop: 10 }}>{note}</Meta> : null}
    </NCard>
  );
}

export function GradeChip({ grade, word }: { grade?: string | null; word?: string | null }) {
  const g = (grade || "").toUpperCase();
  const [bg, fg] = g === "A" ? [C.goodSoft, C.good] : g === "C" ? [C.warnSoft, C.warn] : g === "D" ? [C.badSoft, C.bad] : [C.card2, C.text];
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 6, paddingVertical: 4, paddingHorizontal: 10, borderRadius: 8, backgroundColor: bg }}>
      <Text style={{ color: fg, fontSize: 15, fontWeight: "700" }}>{g || "·"}</Text>
      {word ? <Text style={[TY.meta, { color: fg }]}>{word}</Text> : null}
    </View>
  );
}

export function Btn({ label, kind = "p", onPress, style }: { label: string; kind?: "p" | "s" | "t"; onPress?: () => void; style?: ViewStyle }) {
  const bg = kind === "p" ? G.gold() : kind === "s" ? C.card2 : "transparent";
  const fg = kind === "p" ? G.onGold() : kind === "s" ? C.text : G.gold();
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={[{ backgroundColor: bg, borderRadius: 12, paddingVertical: 11, paddingHorizontal: kind === "t" ? 6 : 18, minHeight: 44, justifyContent: "center" }, style]}>
      <Text style={{ color: fg, fontSize: 15, lineHeight: 22, fontWeight: "600", textAlign: "center" }}>{label}</Text>
    </Pressable>
  );
}

export function PillLink({ label, onPress }: { label: string; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={{ paddingVertical: 8, paddingHorizontal: 14, borderRadius: 999, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, minHeight: 36 }}>
      <Text style={[TY.meta, { color: C.dim }]}>{label}</Text>
    </Pressable>
  );
}

export function Dot({ color }: { color: string }) {
  return <View style={{ width: 8, height: 8, borderRadius: 999, backgroundColor: color }} />;
}

export function RowLink({ left, right, onPress }: { left: React.ReactNode; right?: React.ReactNode; onPress?: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={{ backgroundColor: C.card, borderRadius: 16, paddingVertical: 14, paddingHorizontal: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between", minHeight: 52 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 10, flex: 1 }}>{left}</View>
      {right ?? <Chev />}
    </Pressable>
  );
}

// ---- icons (1.75 stroke, 24 grid)
const I = ({ size = 22, color, children }: { size?: number; color: string; children: React.ReactNode }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round">{children}</Svg>
);
export const Chev = ({ color }: { color?: string }) => <I color={color ?? C.dim}><Path d="m9 6 6 6-6 6" /></I>;
export const SunIcon = ({ color, size }: { color: string; size?: number }) => <I color={color} size={size}><Circle cx={12} cy={12} r={4} /><Path d="M12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M5.6 18.4 7 17M17 7l1.4-1.4" /></I>;
export const RupeeIcon = ({ color, size }: { color: string; size?: number }) => <I color={color} size={size}><Path d="M7 4h10M7 9h10M7 4c5 0 7 2 7 5s-2 5-7 5l7 6" /></I>;
export const CheckIcon2 = ({ color, size }: { color: string; size?: number }) => <I color={color} size={size}><Circle cx={12} cy={12} r={9} /><Path d="m8.5 12 2.5 2.5 4.5-5" /></I>;
export const PeopleIcon = ({ color, size }: { color: string; size?: number }) => <I color={color} size={size}><Circle cx={9} cy={8} r={3.5} /><Path d="M2.5 20c0-3.6 2.9-6 6.5-6s6.5 2.4 6.5 6" /><Circle cx={17} cy={9} r={2.5} /><Path d="M15.5 14.5c3 0 6 2 6 5.5" /></I>;
export const MicIcon2 = ({ color, size }: { color: string; size?: number }) => <I color={color} size={size}><Rect x={9} y={3} width={6} height={11} rx={3} /><Path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" /></I>;
export const LockIcon = ({ color, size }: { color: string; size?: number }) => <I color={color} size={size}><Rect x={5} y={11} width={14} height={10} rx={2} /><Path d="M8 11V7a4 4 0 0 1 8 0v4" /></I>;

export function Orb({ size = 56, onPress, label = "Ask Ananta" }: { size?: number; onPress?: () => void; label?: string }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={label}
      style={{ width: size, height: size, borderRadius: 999, backgroundColor: G.gold(), alignItems: "center", justifyContent: "center",
        shadowColor: C.gold, shadowOpacity: 0.35, shadowRadius: 16, shadowOffset: { width: 0, height: 8 }, elevation: 8 }}>
      <View style={{ position: "absolute", left: -9, top: -9, right: -9, bottom: -9, borderRadius: 999, borderWidth: 2, borderColor: G.glow() }} />
      <MicIcon2 color={G.onGold()} size={Math.round(size * 0.43)} />
    </Pressable>
  );
}

export const inr = (v: number | null | undefined) => (v == null ? "—" : "₹" + Math.round(v).toLocaleString("en-IN"));
export const pctS = (p: number | null | undefined, nd = 1) => (p == null ? "—" : `${p > 0 ? "+" : ""}${p.toFixed(nd)}%`);
