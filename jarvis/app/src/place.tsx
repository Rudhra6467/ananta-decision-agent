// The redesign's twelve building blocks (Madhav, 10 Nov 2026: "yes for all your recommendations. lets complete it and test it as planned").
// The design canvas "Ananta redesign: screens and logo" drew every screen from these twelve, and only these:
//   hero number · summary box · row · section with a chevron · chip line · tile grid · information page · receipt · notice card ·
//   the bell · bottom sheet · floating tab bar (the bar is app/new/_layout.tsx)
// The server writes each place as a list of parts in plain words (jarvis/placekit.py checks the eight rules on it); this file only draws
// them, so a wording fix never needs a new app build. A tap ("to") goes to a tab, a place, a page that rode in with the payload, a bottom
// sheet, a question for Ask, or an older screen. Colours come from C (the theme) so dark and light both work; bronze is the one accent.
import { useEffect, useRef, useState } from "react";
import { Platform, Pressable, ScrollView, Text, TextInput, View, type LayoutChangeEvent } from "react-native";
import { router } from "expo-router";
import Svg, { Circle, G, Path } from "react-native-svg";
import * as SecureStore from "expo-secure-store";
import { C, NUM, setTheme, themeName } from "./theme";
import { AnantaMark } from "./logo";
import { goTab } from "./context";
import { useMarket } from "./market";
import { useData } from "./useData";

// ---------------------------------------------------------------------------------------------------- where a tap goes
export type To = { tab?: string; place?: string; page?: any; sheet?: any; ask?: string; route?: string; action?: string } | null | undefined;
const PAGES = new Map<string, any>();
let nextId = 1;
export const pageOf = (id: string) => PAGES.get(id);

export function go(to: To) {
  if (!to) return;
  if (to.tab) { goTab(`/new/${to.tab}`); return; }
  if (to.place) { router.push({ pathname: "/page", params: { place: to.place } } as any); return; }
  if (to.page) {
    const id = String(nextId++);
    PAGES.set(id, to.page);
    if (PAGES.size > 60) PAGES.delete(PAGES.keys().next().value as string);
    router.push({ pathname: "/page", params: { id } } as any);
    return;
  }
  if (to.sheet) { openSheet(to.sheet); return; }
  if (to.ask) { closeSheet(); goTab({ pathname: "/new/ask", params: { q: to.ask, t: String(Date.now()) } }); return; }
  if (to.route) { closeSheet(); router.push(to.route as any); return; }
  if (to.action === "theme") setTheme(themeName() === "bat" ? "light" : "bat");
}

// ---------------------------------------------------------------------------------------------------- data
export function usePlace(name: string | null, refreshMs = 60000) {
  const mk = useMarket();
  return useData<any>(mk && name ? `/v3/place/${name}?m=${mk}` : null, refreshMs);
}
// the open list lives with the sign-in service; both markets ask it (src/api.ts SHARED)
export function useNeeds() {
  const mk = useMarket();
  return useData<any>(mk ? `/v3/place/needs?m=${mk}` : null, 60000);
}

// ---------------------------------------------------------------------------------------------------- type and small pieces
const T = {
  hero: { fontSize: 40, lineHeight: 46, fontWeight: "700" as const, letterSpacing: -0.8, ...NUM },
  title: { fontSize: 24, lineHeight: 30, fontWeight: "700" as const, letterSpacing: -0.2 },
  today: { fontSize: 20, lineHeight: 26, fontWeight: "600" as const, letterSpacing: -0.2 },
  section: { fontSize: 17, lineHeight: 24, fontWeight: "600" as const },
  row: { fontSize: 15, lineHeight: 22, fontWeight: "600" as const },
  body: { fontSize: 15, lineHeight: 22, fontWeight: "400" as const },
  meta: { fontSize: 13, lineHeight: 18, fontWeight: "600" as const },
  small: { fontSize: 12, lineHeight: 16, fontWeight: "500" as const },
  box: { fontSize: 24, lineHeight: 30, fontWeight: "700" as const, letterSpacing: -0.3, ...NUM },
};
const cap = (s: any) => { const t = String(s ?? ""); return t ? t[0].toUpperCase() + t.slice(1) : t; };
const toneColor = (t?: string | null) => (t === "good" ? C.good : t === "bad" ? C.bad : t === "warn" ? C.warn : undefined);
const card = () => ({ backgroundColor: C.card, borderRadius: 20, borderWidth: 1, borderColor: C.line });

const ICONS: Record<string, string> = {
  up: "M12 19V5M6 11l6-6 6 6", down: "M12 5v14M6 13l6 6 6-6", note: "M7 4h7l4 4v12H7zM14 4v4h4M10 13h5M10 16h5",
  check: "M12 4a8 8 0 1 0 0 16a8 8 0 1 0 0-16zM8.5 12.5l2.5 2.5 4.5-5", pencil: "M5 19l1-4L16 5l3 3L9 18z", moon: "M19 14.5A7.5 7.5 0 0 1 9.5 5a7.5 7.5 0 1 0 9.5 9.5z",
  bell: "M6 9a6 6 0 1 1 12 0c0 5 2 6 2 6H4s2-1 2-6M10 19a2 2 0 0 0 4 0", you: "M12 4a8 8 0 1 0 0 16a8 8 0 1 0 0-16zM12 8v5M12 16v.5",
  tool: "M14.5 5.5a4 4 0 0 0-5 5L4 16l4 4 5.5-5.5a4 4 0 0 0 5-5l-2.5 2.5-3-3z", clock: "M12 4a8 8 0 1 0 0 16a8 8 0 1 0 0-16zM12 8v4l3 2",
  pause: "M9 6v12M15 6v12", play: "M8 5l11 7-11 7z", flask: "M10 4h4M11 4v6l-5 8a1.5 1.5 0 0 0 1.3 2.2h9.4A1.5 1.5 0 0 0 18 18l-5-8V4",
  exam: "M6 5h12v15H6zM9 5V4h6v1M9 13l2 2 4-4", eye: "M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6zM12 9.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 1 0 0-5z",
  bars: "M6 19V11M12 19V5M18 19v-6", people: "M9 6a3 3 0 1 0 0 6a3 3 0 1 0 0-6zM3.5 19c.5-3 2.7-5 5.5-5s5 2 5.5 5M17 5.5a2.5 2.5 0 1 0 0 5M16 13.5c2.5 0 4 1.8 4.5 4.5",
  list: "M9 7h10M9 12h10M9 17h10M5 7h.01M5 12h.01M5 17h.01", flag: "M6 21V4M6 5h11l-2 4 2 4H6", phone: "M7 3h10v18H7zM11 18h2",
  sun: "M12 8a4 4 0 1 0 0 8a4 4 0 1 0 0-8zM12 3v2M12 19v2M3 12h2M19 12h2M5.6 5.6l1.4 1.4M17 17l1.4 1.4M18.4 5.6L17 7M7 17l-1.4 1.4",
  person: "M12 5.5a3.5 3.5 0 1 0 0 7a3.5 3.5 0 1 0 0-7zM5 20c.8-3.6 3.6-5.5 7-5.5s6.2 1.9 7 5.5", info: "M12 4a8 8 0 1 0 0 16a8 8 0 1 0 0-16zM12 11v5M12 8v.5",
  dot: "M12 10a2 2 0 1 0 0 4a2 2 0 1 0 0-4z", chev: "M9 6l6 6-6 6", back: "M15 6l-6 6 6 6", close: "M6 6l12 12M18 6L6 18",
  search: "M11 5a6 6 0 1 0 0 12a6 6 0 1 0 0-12zM20 20l-4.5-4.5", swap: "M7 8h11l-3-3M17 16H6l3 3", home: "M4 11l8-7 8 7M6 10v9h12v-9",
  markets: "M4 19h16M5 15l4-4 3 3 6-7", activity: "M12 4a8 8 0 1 0 0 16a8 8 0 1 0 0-16zM12 8v4l3 2", more: "M4 4h6v6H4zM14 4h6v6h-6zM4 14h6v6H4zM14 14h6v6h-6z",
  lock: "M6 11h12v9H6zM9 11V8a3 3 0 0 1 6 0v3", plus: "M12 6v12M6 12h12",
};
export function Icon({ name, size = 22, color, stroke = 1.75 }: { name: string; size?: number; color?: string; stroke?: number }) {
  return (
    <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color ?? C.dim} strokeWidth={stroke} strokeLinecap="round" strokeLinejoin="round">
      <Path d={ICONS[name] ?? ICONS.dot} />
    </Svg>
  );
}
const tintOf = (t?: string) => (t === "bronze" ? [C.bronzeTint, C.gold] : t === "blue" ? [C.blueTint, C.blue] : t === "violet" ? [C.violetTint, C.violet] : [C.card2, C.dim]);
function IconTile({ name, tint, size = 40 }: { name: string; tint?: string; size?: number }) {
  const [bg, fg] = tintOf(tint);
  return <View style={{ width: size, height: size, borderRadius: size * 0.3, backgroundColor: bg, alignItems: "center", justifyContent: "center" }}><Icon name={name} color={fg} /></View>;
}
function Letter({ ch, grade }: { ch?: string; grade?: string }) {
  const g = (grade || "").toUpperCase();
  const [bg, fg] = g === "C" ? [C.warnSoft, C.warn] : g === "D" ? [C.badSoft, C.bad] : g === "A" ? [C.goodSoft, C.good] : [C.card2, C.text];
  return (
    <View accessibilityLabel={g ? `Grade ${g}` : undefined} style={{ width: 40, height: 40, borderRadius: 999, backgroundColor: bg, alignItems: "center", justifyContent: "center" }}>
      <Text style={{ color: fg, fontSize: 15, fontWeight: "700" }}>{g || ch || "·"}</Text>
    </View>
  );
}
const Chev = () => <Icon name="chev" size={20} />;
function Badge({ n }: { n: number }) {
  return (
    <View style={{ minWidth: 22, height: 22, paddingHorizontal: 6, borderRadius: 11, backgroundColor: C.gold, alignItems: "center", justifyContent: "center" }}>
      <Text style={{ color: C.onGold, fontSize: 13, fontWeight: "700" }}>{n}</Text>
    </View>
  );
}

// 10 · the bell: its count is the open list's "needs your yes" (never red: red only ever means a loss)
export function Bell({ count }: { count: number }) {
  return (
    <Pressable onPress={() => go({ place: "notices" })} accessibilityRole="button" accessibilityLabel={count ? `Notices: ${count} need you` : "Notices"}
      style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}>
      <Icon name="bell" size={24} color={C.text} />
      {count ? (
        <View style={{ position: "absolute", top: 2, right: 0, minWidth: 18, height: 18, paddingHorizontal: 5, borderRadius: 9, backgroundColor: C.gold, alignItems: "center", justifyContent: "center" }}>
          <Text style={{ color: C.onGold, fontSize: 11, fontWeight: "700" }}>{count}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}
export function MarketChip() {
  const mk = useMarket();
  return (
    <Pressable onPress={() => router.push("/market" as any)} accessibilityRole="button" accessibilityLabel={`Market: ${mk === "india" ? "India" : "crypto"}. Switch market`}
      style={{ flexDirection: "row", alignItems: "center", gap: 8, height: 36, paddingHorizontal: 14, borderRadius: 999, backgroundColor: C.card, borderWidth: 1, borderColor: C.line }}>
      <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: mk === "india" ? C.india : C.twin }} />
      <Text style={{ color: C.text, fontSize: 14, fontWeight: "600" }}>{mk === "india" ? "India" : "Crypto"}</Text>
      <Icon name="swap" size={16} />
    </Pressable>
  );
}

// ---------------------------------------------------------------------------------------------------- 1 · hero number
function Hero({ p }: { p: any }) {
  return (
    <View style={{ gap: 6, marginTop: 4 }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
        <Text style={[T.meta, { color: C.dim, flexShrink: 1 }]}>{p.label}</Text>
        {p.status ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
            <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: p.status.ok ? C.good : C.warn }} />
            <Text style={[T.meta, { color: C.dim }]}>{p.status.words}</Text>
          </View>
        ) : null}
      </View>
      <Text style={[T.hero, { color: C.text }, String(p.value).length > 11 ? { fontSize: 32, lineHeight: 40 } : null]} numberOfLines={1} adjustsFontSizeToFit>{p.value}</Text>
      {p.change || p.since ? (
        <Text style={[T.row, { color: toneColor(p.tone) ?? C.text }]}>{p.change ? p.change + " " : ""}<Text style={{ color: C.dim, fontWeight: "500" }}>{p.since}</Text></Text>
      ) : null}
    </View>
  );
}

// the "Today" card: one line, one sentence, a chevron
function TodayCard({ p }: { p: any }) {
  return (
    <Pressable onPress={() => go(p.to)} accessibilityRole="button" style={[card(), { padding: 16, gap: 6 }]}>
      <Text style={[T.meta, { color: C.gold }]}>{p.label}</Text>
      <Text style={[T.today, { color: C.text }]}>{p.line}</Text>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
        <Text style={[T.body, { color: C.dim, flex: 1 }]}>{p.sub}</Text>
        {p.to ? <Chev /> : null}
      </View>
    </Pressable>
  );
}

// ---------------------------------------------------------------------------------------------------- 2 · summary box (and the sliding cards)
function Spark({ values, tone, w, h = 40 }: { values: number[]; tone?: string; w: number; h?: number }) {
  if (!values || values.length < 2 || w < 20) return <View style={{ height: h }} />;
  const lo = Math.min(...values), hi = Math.max(...values), span = hi - lo || 1;
  const pts = values.map((v, i) => [2 + (i * (w - 8)) / (values.length - 1), 3 + (h - 6) * (1 - (v - lo) / span)]);
  const d = "M" + pts.map((q) => `${q[0].toFixed(1)} ${q[1].toFixed(1)}`).join("L");
  const last = pts[pts.length - 1];
  return (
    <Svg width={w} height={h} accessibilityLabel={`A small chart of ${values.length} closes, ending ${values[values.length - 1] >= values[0] ? "higher" : "lower"}`}>
      <Path d={d} stroke={C.dim} strokeWidth={1.5} fill="none" strokeLinejoin="round" strokeLinecap="round" />
      <Circle cx={last[0]} cy={last[1]} r={3} fill={toneColor(tone) ?? C.text} />
    </Svg>
  );
}
function Box({ b, width }: { b: any; width?: number }) {
  const [w, setW] = useState(0);
  return (
    <Pressable onPress={b.to ? () => go(b.to) : undefined} accessibilityRole={b.to ? "button" : undefined}
      style={[card(), { padding: 16, gap: 4 }, width ? { width } : { flex: 1, minWidth: 0 }]}
      onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width - 32)}>
      <Text style={[T.meta, { color: C.dim }]} numberOfLines={1}>{cap(b.label)}</Text>
      <Text style={[T.box, { color: C.text }, String(b.value).length > 8 ? { fontSize: 20 } : null]} numberOfLines={1}>{b.value}</Text>
      {b.spark ? <Spark values={b.spark} tone={b.tone} w={w} /> : null}
      {b.bar ? (
        <View accessibilityLabel={`${Math.round(100 * (b.bar[0] || 0))}% of the account`} style={{ height: 40, justifyContent: "center" }}>
          <View style={{ flexDirection: "row", gap: 2, height: 8, borderRadius: 4, overflow: "hidden", backgroundColor: C.card2, borderWidth: 1, borderColor: C.line }}>
            {(b.bar as number[]).map((s, i) => s > 0 ? <View key={i} style={{ width: `${Math.round(100 * s)}%`, backgroundColor: i === 0 ? C.text : C.faint }} /> : null)}
          </View>
        </View>
      ) : null}
      {b.change ? <Text style={[T.meta, { color: toneColor(b.tone) ?? C.dim }]} numberOfLines={1}>{b.change} <Text style={{ color: C.dim, fontWeight: "500" }}>{b.since || ""}</Text></Text> : null}
      {b.caption ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]} numberOfLines={1}>{b.caption}</Text> : null}
    </Pressable>
  );
}
function Peek({ p }: { p: any }) {
  return (
    <View style={{ gap: 8 }}>
      <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginRight: -16 }} contentContainerStyle={{ gap: 12, paddingRight: 16 }}>
        {(p.items || []).map((b: any, i: number) => <Box key={b.label + i} b={b} width={150} />)}
      </ScrollView>
      {p.note ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{p.note}</Text> : null}
    </View>
  );
}

// ---------------------------------------------------------------------------------------------------- 3 · row, 4 · section with a chevron
export function Row({ r, last }: { r: any; last?: boolean }) {
  const left = r.icon ? <IconTile name={r.icon} tint={r.tint} /> : r.letter || r.grade ? <Letter ch={r.letter} grade={r.grade} /> : null;
  const body = (
    <>
      {left}
      <View style={{ flex: 1, minWidth: 0 }}>
        <Text style={[T.row, { color: C.text }]} numberOfLines={1}>{cap(r.title)}</Text>
        {r.sub ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]} numberOfLines={1}>{r.sub}</Text> : null}
      </View>
      {r.chip ? <View style={{ paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, borderWidth: 1, borderColor: C.line }}><Text style={[T.small, { color: C.dim, fontWeight: "600" }]}>{r.chip}</Text></View> : null}
      {r.right ? (
        <View style={{ alignItems: "flex-end" }}>
          <Text style={[r.right_tone || /[₹$\d]/.test(r.right) ? T.row : T.meta, { color: (r.right_sub ? undefined : toneColor(r.right_tone)) ?? (/[₹$\d]/.test(r.right) ? C.text : C.dim), ...NUM }]} numberOfLines={1}>{r.right}</Text>
          {r.right_sub ? <Text style={[T.meta, { color: toneColor(r.right_tone) ?? C.dim }]}>{r.right_sub}</Text> : null}
        </View>
      ) : null}
      {r.to && !r.right && !r.chip ? <Chev /> : null}
    </>
  );
  const style = { flexDirection: "row" as const, alignItems: "center" as const, gap: 12, minHeight: 64, paddingVertical: 10, borderBottomWidth: last ? 0 : 1, borderBottomColor: C.line2 };
  return r.to ? <Pressable onPress={() => go(r.to)} accessibilityRole="button" style={style}>{body}</Pressable> : <View style={style}>{body}</View>;
}
function Section({ p, rows, needs }: { p: any; rows?: any[]; needs?: number }) {
  const rs = rows ?? p.rows ?? [];
  if (!rs.length) return null;
  const n = needs ?? p.count;
  return (
    <View style={{ gap: 4 }}>
      {p.title ? (
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", minHeight: 44 }}>
          <View style={{ flexDirection: "row", alignItems: "baseline", gap: 8, flexShrink: 1 }}>
            <Text style={[T.section, { color: C.text }]}>{p.title}</Text>
            {p.badge && n ? <Badge n={n} /> : p.sub ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{p.sub}</Text> : null}
          </View>
          {p.more ? (
            <Pressable onPress={() => go(p.more)} accessibilityRole="button" accessibilityLabel={`All of ${p.title}`} style={{ width: 44, height: 44, alignItems: "flex-end", justifyContent: "center" }}><Chev /></Pressable>
          ) : null}
        </View>
      ) : null}
      <View style={[card(), { paddingHorizontal: 16 }]}>
        {rs.map((r: any, i: number) => <Row key={(r.title || "") + i} r={r} last={i === rs.length - 1} />)}
      </View>
      {p.foot ? <Text style={[T.meta, { color: C.dim, fontWeight: "500", paddingHorizontal: 4, paddingTop: 6 }]}>{p.foot}</Text> : null}
    </View>
  );
}

// ---------------------------------------------------------------------------------------------------- 5 · chip line
function Chips({ p, on, set }: { p: any; on: string; set: (id: string) => void }) {
  return (
    <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ marginRight: -16 }} contentContainerStyle={{ gap: 8, paddingRight: 16 }}>
      {(p.items || []).map((c: any) => {
        const sel = c.id === on;
        return (
          <Pressable key={c.id} onPress={() => set(c.id)} accessibilityRole="button" accessibilityState={{ selected: sel }}
            style={{ height: 36, paddingHorizontal: 14, borderRadius: 999, justifyContent: "center", borderWidth: 1, borderColor: sel ? C.text : C.line, backgroundColor: sel ? C.text : C.card }}>
            <Text style={{ color: sel ? C.bg : C.text, fontSize: 14, fontWeight: "600" }}>{c.label}{c.count ? ` · ${c.count}` : ""}</Text>
          </Pressable>
        );
      })}
    </ScrollView>
  );
}

// ---------------------------------------------------------------------------------------------------- 6 · tile grid (things not set up yet look quieter)
function Tiles({ p, needs }: { p: any; needs?: any }) {
  const items = (p.items || []).map((x: any) => {
    if (x.t === "needs_tile") return { ...x, value: needs ? needs.list_value : "—" };
    if (x.t === "push_tile") return needs && !needs.push?.on ? { ...x, value: "Not set up yet", quiet: true, to: needs.push?.to } : { ...x, value: needs ? "On" : "—" };
    return x;
  });
  return (
    <View style={{ gap: 4 }}>
      {p.title ? <Text style={[T.section, { color: C.text, paddingTop: 8, paddingBottom: 8 }]}>{p.title}</Text> : null}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
        {items.map((x: any) => (
          <Pressable key={x.label} onPress={() => go(x.to)} accessibilityRole="button" accessibilityLabel={`${x.label}${x.value ? ", " + x.value : ""}`}
            style={[{ width: "31%", flexGrow: 1, height: 120, padding: 12, borderRadius: 20, justifyContent: "space-between" },
              x.quiet ? { borderWidth: 1, borderStyle: "dashed", borderColor: C.faint } : { backgroundColor: C.card, borderWidth: 1, borderColor: C.line }]}>
            <View>
              {x.quiet ? (
                <View style={{ width: 36, height: 36, borderRadius: 10, borderWidth: 1, borderColor: C.faint, alignItems: "center", justifyContent: "center" }}>
                  <Icon name={x.icon} size={20} />
                  <View style={{ position: "absolute", right: -7, bottom: -7, width: 18, height: 18, borderRadius: 9, backgroundColor: C.text, alignItems: "center", justifyContent: "center" }}><Icon name="plus" size={12} color={C.bg} stroke={3} /></View>
                </View>
              ) : <IconTile name={x.icon} tint={x.tint} size={36} />}
            </View>
            <View>
              <Text style={[T.meta, { color: C.text }]} numberOfLines={1}>{x.label}</Text>
              {x.value ? <Text style={[T.small, { color: C.dim }]} numberOfLines={1}>{x.value}</Text> : null}
            </View>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------------------------------- 7 · information page pieces, 8 · receipt
function Pill({ p }: { p: any }) {
  const fg = toneColor(p.tone) ?? C.text;
  return (
    <View style={{ alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6, height: 28, paddingHorizontal: 12, borderRadius: 999,
      backgroundColor: p.tone === "warn" ? C.warnSoft : p.tone === "good" ? C.goodSoft : p.tone === "bad" ? C.badSoft : C.card2 }}>
      {p.icon ? <Icon name={p.icon} size={14} color={fg} stroke={2.2} /> : null}
      <Text style={[T.meta, { color: fg }]}>{p.text}</Text>
    </View>
  );
}
function Points({ p }: { p: any }) {
  return (
    <View style={{ gap: 12 }}>
      {p.title ? <Text style={[T.section, { color: C.text }]}>{p.title}</Text> : null}
      {(p.items || []).map((x: any, i: number) => (
        <View key={i} style={{ flexDirection: "row", gap: 12, alignItems: "flex-start" }}>
          <Icon name={x.icon || (x.tone === "bad" ? "down" : x.tone === "good" ? "up" : "check")} color={toneColor(x.tone) ?? C.dim} />
          <Text style={[T.body, { color: C.text, flex: 1 }]}>{x.text}</Text>
        </View>
      ))}
    </View>
  );
}
function KV({ p }: { p: any }) {
  return (
    <View style={{ gap: 4 }}>
      {p.title ? <Text style={[T.section, { color: C.text, minHeight: 32 }]}>{p.title}</Text> : null}
      <View style={[card(), { paddingHorizontal: 16 }]}>
        {(p.rows || []).map((r: any, i: number) => (
          <View key={r.k + i} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 12, minHeight: r.k_sub || r.v_sub ? 60 : 50,
            borderBottomWidth: i === p.rows.length - 1 ? 0 : 1, borderBottomColor: C.line2 }}>
            <View style={{ flexShrink: 1 }}>
              <Text style={[r.bold ? { fontSize: 16, fontWeight: "700" } : T.body, { color: r.bold ? C.text : C.dim }]}>{r.k}</Text>
              {r.k_sub ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{r.k_sub}</Text> : null}
            </View>
            <View style={{ alignItems: "flex-end", flexShrink: 1 }}>
              <Text style={[{ fontSize: r.bold ? 16 : 15, fontWeight: r.bold ? "700" : "600", ...NUM }, { color: toneColor(r.tone) ?? C.text, textAlign: "right" }]}>{r.v}</Text>
              {r.v_sub ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{r.v_sub}</Text> : null}
            </View>
          </View>
        ))}
      </View>
      {p.foot ? <Text style={[T.meta, { color: C.dim, fontWeight: "500", paddingHorizontal: 4, paddingTop: 6 }]}>{p.foot}</Text> : null}
    </View>
  );
}
function Bars({ p }: { p: any }) {
  return (
    <View style={[card(), { padding: 16, gap: 18 }]}>
      {p.title ? <Text style={[T.section, { color: C.text }]}>{p.title}</Text> : null}
      {(p.items || []).map((b: any) => {
        const f = Math.max(0, Math.min(1, (b.done || 0) / (b.need || 1)));
        return (
          <View key={b.name} style={{ gap: 8 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
              <Text style={[T.row, { color: C.text, flexShrink: 1 }]}>{b.name}</Text>
              <Text style={[T.meta, { color: C.dim, fontWeight: "500", ...NUM }]}>{b.right}</Text>
            </View>
            <View accessibilityLabel={`${b.done} of ${b.need}`} style={{ height: 6, borderRadius: 3, backgroundColor: C.card2 }}>
              {f > 0 ? <View style={{ width: `${Math.round(100 * f)}%`, height: 6, borderRadius: 3, backgroundColor: C.text }} /> : null}
            </View>
            {b.note ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{b.note}</Text> : null}
          </View>
        );
      })}
    </View>
  );
}
function Split({ p }: { p: any }) {
  const shade = (s: string) => (s === "ink" ? C.text : s === "dim" ? C.faint : C.card2);
  return (
    <View style={{ gap: 4 }}>
      {p.title ? <Text style={[T.section, { color: C.text, minHeight: 32 }]}>{p.title}</Text> : null}
      <View style={[card(), { paddingHorizontal: 16, paddingTop: 16 }]}>
        <View style={{ flexDirection: "row", gap: 2, height: 10, borderRadius: 5, overflow: "hidden", marginBottom: 8 }}>
          {(p.parts || []).map((x: any, i: number) => <View key={i} style={{ width: `${Math.round(100 * x.share)}%`, backgroundColor: shade(x.shade) }} />)}
        </View>
        {(p.parts || []).map((x: any, i: number) => (
          <View key={x.label} style={{ flexDirection: "row", alignItems: "center", gap: 10, minHeight: 48, borderBottomWidth: i === p.parts.length - 1 ? 0 : 1, borderBottomColor: C.line2 }}>
            <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: shade(x.shade), borderWidth: x.shade === "faint" ? 1 : 0, borderColor: C.faint }} />
            <Text style={[T.body, { color: C.text, flex: 1 }]}>{x.label}</Text>
            <Text style={[T.row, { color: C.text, ...NUM }]}>{x.value}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}
function Chart({ p }: { p: any }) {
  const [w, setW] = useState(0);
  const h = 138;
  const all = (p.lines || []).flatMap((l: any) => l.values || []).concat(p.baseline != null ? [p.baseline] : []);
  const lo = Math.min(...all), hi = Math.max(...all), span = hi - lo || 1;
  const col = (c?: string) => (c === "bronze" ? C.gold : c === "dim" ? C.faint : C.text);
  const pts = (v: number[]) => v.map((x, i) => [2 + (i * (w - 6)) / Math.max(1, v.length - 1), 6 + (h - 12) * (1 - (x - lo) / span)]);
  const line = (q: number[][]) => q.map((x, i) => `${i ? "L" : "M"}${x[0].toFixed(1)} ${x[1].toFixed(1)}`).join("");
  return (
    <View style={[card(), { padding: 16, gap: 10 }]} onLayout={(e) => setW(e.nativeEvent.layout.width - 32)}>
      {w > 20 ? (
        <Svg width={w} height={h} accessibilityLabel={p.label}>
          {p.baseline != null ? <Path d={`M0 ${(6 + (h - 12) * (1 - (p.baseline - lo) / span)).toFixed(1)}H${w}`} stroke={C.line} strokeDasharray="2 4" /> : null}
          {(p.lines || []).map((l: any, i: number) => {
            const q = pts(l.values || []);
            const cut = l.last_dash ? q.length - l.last_dash : q.length;
            const dash = l.style === "dash" ? "5 4" : l.style === "dot" ? "1 5" : undefined;
            const end = q[q.length - 1];
            return (
              <G key={i}>
                <Path d={line(q.slice(0, cut))} stroke={col(l.color)} strokeWidth={l.style === "main" ? 2 : 1.5} strokeDasharray={dash} fill="none" strokeLinejoin="round" strokeLinecap="round" />
                {l.last_dash ? <Path d={line(q.slice(cut - 1))} stroke={col(l.color)} strokeWidth={2} strokeDasharray="3 4" fill="none" /> : null}
                {l.style === "main" && end ? <Circle cx={end[0]} cy={end[1]} r={4} fill={col(l.color)} stroke={C.card} strokeWidth={2} /> : null}
              </G>
            );
          })}
        </Svg>
      ) : <View style={{ height: h }} />}
      {p.left || p.right ? <View style={{ flexDirection: "row", justifyContent: "space-between" }}><Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{p.left}</Text><Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{p.right}</Text></View> : null}
      {p.legend ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 14 }}>
          {p.legend.map((l: any) => (
            <View key={l.label} style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
              <View style={{ width: 14, height: 0, borderTopWidth: 2, borderStyle: l.style === "main" ? "solid" : l.style === "dot" ? "dotted" : "dashed", borderColor: col(l.color) }} />
              <Text style={[T.meta, { color: l.style === "main" ? C.text : C.dim }]}>{l.label}</Text>
            </View>
          ))}
        </View>
      ) : null}
      {p.caption ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{p.caption}</Text> : null}
    </View>
  );
}
function Counts({ p }: { p: any }) {
  return (
    <Pressable onPress={() => go(p.to)} accessibilityRole="button" style={[card(), { padding: 16, gap: 12 }]}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}><Text style={[T.row, { color: C.text }]}>{p.title}</Text><Chev /></View>
      <View style={{ flexDirection: "row", gap: 8 }}>
        {(p.items || []).map((x: any) => (
          <View key={x.label} style={{ flex: 1 }}>
            <Text style={{ fontSize: 20, lineHeight: 26, fontWeight: "700", color: x.accent ? C.gold : C.text, ...NUM }}>{x.n}</Text>
            <Text style={[T.small, { color: C.dim }]}>{x.label}</Text>
          </View>
        ))}
      </View>
    </Pressable>
  );
}

// ---------------------------------------------------------------------------------------------------- 9 · notice card (closable; this device remembers)
const DKEY = "ananta_notices_closed";
let closed: string[] | null = null;
function useClosed(): [string[], (id: string) => void] {
  const [v, setV] = useState<string[]>(closed ?? []);
  useEffect(() => {
    if (closed) return;
    SecureStore.getItemAsync(DKEY).then((s) => { closed = s ? JSON.parse(s) : []; setV(closed!); }).catch(() => { closed = []; });
  }, []);
  const add = (id: string) => { closed = [...(closed ?? []), id].slice(-80); setV(closed); SecureStore.setItemAsync(DKEY, JSON.stringify(closed)).catch(() => {}); };
  return [v, add];
}
function Notices({ p }: { p: any }) {
  const [gone, close] = useClosed();
  const items = (p.items || []).filter((n: any) => !gone.includes(n.id));
  if (!items.length) return null;
  return (
    <View style={{ gap: 8, marginTop: 4 }}>
      {items.map((n: any) => (
        <View key={n.id} style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingLeft: 16, paddingRight: 6, paddingVertical: 6, borderRadius: 16, backgroundColor: C.card, borderWidth: 1, borderColor: C.line }}>
          <Pressable onPress={() => go(n.to)} accessibilityRole="button" style={{ flex: 1, minHeight: 32, justifyContent: "center" }}>
            <Text style={{ color: C.text, fontSize: 14, lineHeight: 20, fontWeight: "500" }}>{n.line}</Text>
          </Pressable>
          <Pressable onPress={() => close(n.id)} accessibilityRole="button" accessibilityLabel="Close this notice" style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}>
            <Icon name="close" size={18} />
          </Pressable>
        </View>
      ))}
    </View>
  );
}

// ---------------------------------------------------------------------------------------------------- 11 · bottom sheet (one thing at a time)
let sheet: any = null;
const sheetSubs = new Set<() => void>();
export function openSheet(s: any) { sheet = s; sheetSubs.forEach((f) => f()); }
export function closeSheet() { if (sheet) { sheet = null; sheetSubs.forEach((f) => f()); } }
export function SheetHost() {
  const [, bump] = useState(0);
  useEffect(() => { const f = () => bump((n) => n + 1); sheetSubs.add(f); return () => { sheetSubs.delete(f); }; }, []);
  if (!sheet) return null;
  const s = sheet;
  return (
    <View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }}>
      <Pressable onPress={closeSheet} accessibilityLabel="Close" style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, backgroundColor: C.overlay }} />
      <View accessibilityViewIsModal style={{ position: "absolute", left: 0, right: 0, bottom: 0, paddingTop: 10, paddingHorizontal: 16, paddingBottom: 28, borderTopLeftRadius: 24, borderTopRightRadius: 24,
        backgroundColor: C.card, borderTopWidth: 1, borderColor: C.line, gap: 16, maxWidth: 720, alignSelf: "center", width: "100%" }}>
        <View style={{ alignSelf: "center", width: 40, height: 4, borderRadius: 2, backgroundColor: C.faint }} />
        <IconTile name={s.icon === "you" ? "you" : s.icon || "you"} tint="bronze" size={48} />
        <View style={{ gap: 8 }}>
          <Text style={{ color: C.text, fontSize: 22, lineHeight: 28, fontWeight: "700", letterSpacing: -0.2 }} accessibilityRole="header">{s.title}</Text>
          <Text style={[T.body, { color: C.dim }]}>{s.text}</Text>
        </View>
        {s.advice ? (
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12, padding: 12, borderRadius: 16, backgroundColor: C.card2 }}>
            <AnantaMark size={32} />
            <Text style={{ color: C.text, fontSize: 14, lineHeight: 20, flex: 1 }}><Text style={{ fontWeight: "600" }}>Ananta's advice: </Text>{s.advice}</Text>
          </View>
        ) : null}
        <View style={{ gap: 4 }}>
          {s.primary ? <MainButton label={s.primary.label} onPress={() => { const t = s.primary.to; closeSheet(); go(t); }} /> : null}
          <Pressable onPress={closeSheet} accessibilityRole="button" style={{ height: 48, alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>{s.secondary || "Not now"}</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

export function MainButton({ label, onPress }: { label: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={{ height: 52, borderRadius: 16, backgroundColor: C.gold, alignItems: "center", justifyContent: "center" }}>
      <Text style={{ color: C.onGold, fontSize: 16, fontWeight: "600" }}>{label}</Text>
    </Pressable>
  );
}
export function Pinned({ p }: { p: any }) {
  if (!p) return null;
  return (
    <View style={{ paddingHorizontal: 16, paddingTop: 12, paddingBottom: 12, gap: 4, backgroundColor: C.bg }}>
      {p.ask ? <MainButton label="Ask Ananta about this" onPress={() => go({ ask: p.ask })} /> : null}
      {p.second ? (
        <Pressable onPress={() => go(p.second.ask ? { ask: p.second.ask } : p.second.route ? { route: p.second.route } : p.second.to)} accessibilityRole="button" style={{ height: 48, alignItems: "center", justifyContent: "center" }}>
          <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>{p.second.label}</Text>
        </Pressable>
      ) : null}
    </View>
  );
}

// ---------------------------------------------------------------------------------------------------- the search box on Markets
function Search({ s }: { s: any }) {
  const [q, setQ] = useState("");
  const submit = () => { const v = q.trim().toUpperCase().replace(/[^A-Z0-9&-]/g, ""); if (v) router.push(((s.route || "/coin/") + v) as any); };
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10, height: 48, paddingHorizontal: 14, borderRadius: 16, backgroundColor: C.card, borderWidth: 1, borderColor: C.line }}>
      <Icon name="search" size={20} />
      <TextInput value={q} onChangeText={setQ} onSubmitEditing={submit} placeholder={s.hint} placeholderTextColor={C.dim} autoCapitalize="characters" autoCorrect={false}
        returnKeyType="search" accessibilityLabel={s.hint} style={{ flex: 1, height: 44, color: C.text, fontSize: 15, ...(Platform.OS === "web" ? ({ outlineStyle: "none" } as any) : {}) }} />
    </View>
  );
}

// ---------------------------------------------------------------------------------------------------- the parts, in order
export function Parts({ data, needs }: { data: any; needs?: any }) {
  const parts: any[] = data?.parts || [];
  const chipPart = parts.find((p) => p.t === "chips");
  const [on, setOn] = useState<string>(chipPart?.items?.[0]?.id || "all");
  const first = chipPart?.items?.[0]?.id || "all";
  const shown = (p: any) => {
    if (!chipPart || p.t === "chips") return true;
    if (p.tags) return p.tags.includes(on) || (on === first && p.tags.includes("all"));
    return on === first || (p.t === "rows" && (p.rows || []).some((r: any) => r.tag === on));
  };
  const out: React.ReactNode[] = [];
  if (data?.search) out.push(<Search key="search" s={data.search} />);
  parts.forEach((p, i) => {
    if (!shown(p)) return;
    const k = `${p.t}${i}`;
    switch (p.t) {
      case "hero": out.push(<Hero key={k} p={p} />); break;
      case "today": out.push(<TodayCard key={k} p={p} />); break;
      case "boxes": out.push(<View key={k} style={{ flexDirection: "row", gap: 12 }}>{(p.items || []).map((b: any, j: number) => <Box key={j} b={b} />)}</View>); break;
      case "peek": out.push(<Peek key={k} p={p} />); break;
      case "rows": {
        const rows = chipPart && on !== first && !p.tags ? (p.rows || []).filter((r: any) => r.tag === on) : p.rows;
        out.push(<Section key={k} p={p} rows={rows} />);
        break;
      }
      case "needs": out.push(<Section key={k} p={{ ...p, count: needs?.count }} rows={(needs?.rows || []).slice(0, p.tags ? 40 : 3)} needs={needs?.count} />); break;
      case "chips": out.push(<Chips key={k} p={p} on={on} set={setOn} />); break;
      case "tiles": out.push(<Tiles key={k} p={p} needs={needs} />); break;
      case "pill": out.push(<Pill key={k} p={p} />); break;
      case "heading": out.push(<Text key={k} accessibilityRole="header" style={[T.title, { color: C.text }]}>{p.text}</Text>); break;
      case "line": out.push(<Text key={k} style={[T.body, { color: C.dim }]}>{p.text}</Text>); break;
      case "points": out.push(<Points key={k} p={p} />); break;
      case "trust": out.push(<Text key={k} style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{p.text}</Text>); break;
      case "kv": out.push(<KV key={k} p={p} />); break;
      case "notices": out.push(<Notices key={k} p={p} />); break;
      case "bars": out.push(<Bars key={k} p={p} />); break;
      case "split": out.push(<Split key={k} p={p} />); break;
      case "chart": out.push(<Chart key={k} p={p} />); break;
      case "counts": out.push(<Counts key={k} p={p} />); break;
      case "link": out.push(<Pressable key={k} onPress={() => go(p.to)} accessibilityRole="link" style={{ minHeight: 44, justifyContent: "center", paddingHorizontal: 4 }}><Text style={[T.row, { color: C.gold }]}>{p.label}</Text></Pressable>); break;
      case "identity": out.push(
        <View key={k} style={[card(), { flexDirection: "row", alignItems: "center", gap: 14, paddingVertical: 14, paddingHorizontal: 16 }]}>
          <AnantaMark size={52} />
          <View style={{ gap: 2, flex: 1 }}><Text style={{ color: C.text, fontSize: 15, fontWeight: "700", letterSpacing: 2.4 }}>ANANTA</Text><Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{p.line}</Text></View>
        </View>); break;
      default: break;
    }
  });
  return <>{out}</>;
}

export const useKeepRef = <T,>(v: T) => { const r = useRef(v); r.current = v; return r; };
