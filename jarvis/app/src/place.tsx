// The redesign's twelve building blocks (Madhav, 10 Nov 2026: "yes for all your recommendations. lets complete it and test it as planned").
// The design canvas "Ananta redesign: screens and logo" drew every screen from these twelve, and only these:
//   hero number · summary box · row · section with a chevron · chip line · tile grid · information page · receipt · notice card ·
//   the bell · bottom sheet · floating tab bar (the bar is app/new/_layout.tsx)
// The server writes each place as a list of parts in plain words (jarvis/placekit.py checks the eight rules on it); this file only draws
// them, so a wording fix never needs a new app build. A tap ("to") goes to a tab, a place, a page that rode in with the payload, a bottom
// sheet, a question for Ask, or an older screen. Colours come from C (the theme) so dark and light both work; bronze is the one accent.
import { useEffect, useRef, useState } from "react";
import { Animated, Easing, PanResponder, Platform, Pressable, ScrollView, Text, TextInput, View, useWindowDimensions, type LayoutChangeEvent } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Circle, G, Path, Rect } from "react-native-svg";
import * as SecureStore from "expo-secure-store";
import { C, NUM, setTheme, themeName } from "./theme";
import { AnantaMark } from "./logo";
import { goTab } from "./context";
import { useMarket } from "./market";
import { useData } from "./useData";

// ---------------------------------------------------------------------------------------------------- where a tap goes
export type To = { tab?: string; place?: string; page?: any; sheet?: any; ask?: string; route?: string; action?: string; as?: string } | null | undefined;
const PAGES = new Map<string, any>();
let nextId = 1;
export const pageOf = (id: string) => PAGES.get(id);

export function go(to: To) {
  if (!to) return;
  if (to.place && to.as === "sheet") { openSheet({ place: to.place }); return; }     // a place drawn in a tall sheet over this screen
  if (to.tab || to.place || to.page) closeSheet();                                  // leaving for a tab or a page closes an open sheet
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
  eyeoff: "M3 12s3.5-6 9-6 9 6 9 6-3.5 6-9 6-9-6-9-6zM12 9.5a2.5 2.5 0 1 0 0 5a2.5 2.5 0 1 0 0-5zM4 4l16 16",
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

// ---------------------------------------------------------------------------------------------------- hide the amounts
// Madhav, 10 Nov 2026 19:09: "A hide button next to bell symbol, to hide portfolio numbers from being visible to others". The eye beside the
// bell hides every amount in rupees or Canadian dollars (the account's money) and every signed US-dollar amount (a trade's result), on every
// screen; market prices and percentages stay. This device remembers the choice.
const HKEY = "ananta_hide_money";
let hiddenNow: boolean | null = null;
const hiddenSubs = new Set<(v: boolean) => void>();
function readHidden(): Promise<string | null> {
  if (Platform.OS === "web") { try { return Promise.resolve(window.localStorage.getItem(HKEY)); } catch { return Promise.resolve(null); } }
  return SecureStore.getItemAsync(HKEY).catch(() => null);
}
function writeHidden(v: boolean) {
  if (Platform.OS === "web") { try { window.localStorage.setItem(HKEY, v ? "1" : "0"); } catch { /* storage blocked */ } return; }
  SecureStore.setItemAsync(HKEY, v ? "1" : "0").catch(() => {});
}
export function useHidden(): [boolean, () => void] {
  const [h, setH] = useState<boolean>(!!hiddenNow);
  useEffect(() => {
    hiddenSubs.add(setH);
    if (hiddenNow === null) {
      hiddenNow = false;
      readHidden().then((v) => { hiddenNow = v === "1"; hiddenSubs.forEach((f) => f(!!hiddenNow)); });
    } else setH(hiddenNow);
    return () => { hiddenSubs.delete(setH); };
  }, []);
  const toggle = () => { hiddenNow = !hiddenNow; writeHidden(hiddenNow); hiddenSubs.forEach((f) => f(!!hiddenNow)); };
  return [h, toggle];
}
const MONEY = /([+−-]?\s?)(₹|C\$|US\$)\s?\d[\d,]*(?:\.\d+)?(?![\d,.]*\s?(?:cr\b|crore))/g;     // market flows in crore stay
const SIGNED_USD = /([+−-])\s?\$\d[\d,]*(?:\.\d+)?/g;
export const maskMoney = (v: any) => (typeof v === "string" ? v.replace(MONEY, "$1$2••••").replace(SIGNED_USD, "$1$$••••") : v);
const same = (v: any) => v;
export function useMask() { const [h] = useHidden(); return h ? maskMoney : same; }
export function HideButton() {
  const [h, toggle] = useHidden();
  return (
    <Pressable onPress={toggle} accessibilityRole="button" accessibilityLabel={h ? "Show the amounts" : "Hide the amounts"} accessibilityState={{ selected: h }}
      style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}>
      <Icon name={h ? "eyeoff" : "eye"} size={24} color={C.text} />
    </Pressable>
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
  const m = useMask();
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
      <Text style={[T.hero, { color: C.text }, String(p.value).length > 11 ? { fontSize: 32, lineHeight: 40 } : null]} numberOfLines={1} adjustsFontSizeToFit>{m(p.value)}</Text>
      {p.change || p.since ? (
        <Text style={[T.row, { color: toneColor(p.tone) ?? C.text }]}>{p.change ? m(p.change) + " " : ""}<Text style={{ color: C.dim, fontWeight: "500" }}>{p.since}</Text></Text>
      ) : null}
    </View>
  );
}

// the "Today" card: one line, one sentence, a chevron
function TodayCard({ p }: { p: any }) {
  const m = useMask();
  return (
    <Pressable onPress={() => go(p.to)} accessibilityRole="button" style={[card(), { padding: 16, gap: 6 }]}>
      <Text style={[T.meta, { color: C.gold }]}>{p.label}</Text>
      <Text style={[T.today, { color: C.text }]}>{m(p.line)}</Text>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
        <Text style={[T.body, { color: C.dim, flex: 1 }]}>{m(p.sub)}</Text>
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
function BoxBody({ b, w }: { b: any; w: number }) {
  const m = useMask();
  return (
    <>
      <Text style={[T.meta, { color: C.dim }]} numberOfLines={1}>{cap(b.label)}</Text>
      <Text style={[T.box, { color: C.text }, String(b.value).length > 8 ? { fontSize: 20 } : null]} numberOfLines={1}>{m(b.value)}</Text>
      {b.spark ? <Spark values={b.spark} tone={b.tone} w={w} /> : null}
      {b.bar ? (
        <View accessibilityLabel={`${Math.round(100 * ((b.bar[0] || 0) + (b.bar[1] || 0)))}% of the account`} style={{ height: 40, justifyContent: "center" }}>
          <View style={{ flexDirection: "row", gap: 2, height: 8, borderRadius: 4, overflow: "hidden", backgroundColor: C.card2, borderWidth: 1, borderColor: C.line }}>
            {(b.bar as number[]).map((x, i) => x > 0 ? <View key={i} style={{ width: `${Math.round(100 * x)}%`, backgroundColor: i === 0 ? C.text : C.faint }} /> : null)}
          </View>
        </View>
      ) : null}
      {b.change ? <Text style={[T.meta, { color: toneColor(b.tone) ?? C.dim }]} numberOfLines={1}>{m(b.change)} <Text style={{ color: C.dim, fontWeight: "500" }}>{b.since || ""}</Text></Text> : null}
      {b.caption ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]} numberOfLines={1}>{m(b.caption)}</Text> : null}
    </>
  );
}
const BOX_H = 158;            // one height for every box in a row, so the two boxes line up and a page fits exactly
function Box({ b, width, tall }: { b: any; width?: number; tall?: boolean }) {
  const [w, setW] = useState(0);
  if (b.pages && b.pages.length > 1 && !width) return <PagedBox b={b} />;
  return (
    <Pressable onPress={b.to ? () => go(b.to) : undefined} accessibilityRole={b.to ? "button" : undefined}
      style={[card(), { padding: 16, gap: 4 }, width ? { width } : { flex: 1, minWidth: 0 }, tall ? { minHeight: BOX_H } : null]}
      onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width - 32)}>
      <BoxBody b={b} w={w} />
    </Pressable>
  );
}
// Madhav, 10 Nov 14:46: "like we use to show banknifty and nift 50 in one box. Stock and option value in second box": one box, its numbers
// swiped up inside it (paging, so it always rests on one); the dots on the right show which, and a tap on a dot switches. The first box nudges
// up once, so the second number is found (the old Today tiles, 4 Nov).
let nudged = false;
function PagedBox({ b }: { b: any }) {
  const pages: any[] = b.pages;
  const [at, setAt] = useState(0);
  const [w, setW] = useState(0);
  const ref = useRef<ScrollView>(null);
  const H = BOX_H - 2;                                   // inside the card's 1 px line
  useEffect(() => {
    if (nudged) return;
    nudged = true;
    let seen = false;
    try { seen = Platform.OS === "web" && window.localStorage.getItem("ananta.tiles.hinted") === "1"; } catch { /* storage blocked */ }
    if (seen) return;
    const a = setTimeout(() => ref.current?.scrollTo({ y: 30, animated: true }), 1100);
    const c = setTimeout(() => ref.current?.scrollTo({ y: 0, animated: true }), 1600);
    try { if (Platform.OS === "web") window.localStorage.setItem("ananta.tiles.hinted", "1"); } catch { /* storage blocked */ }
    return () => { clearTimeout(a); clearTimeout(c); };
  }, []);
  return (
    <View style={[card(), { flex: 1, minWidth: 0, height: BOX_H, overflow: "hidden" }]} onLayout={(e) => setW(e.nativeEvent.layout.width - 40)}>
      <ScrollView ref={ref} style={{ height: H }} pagingEnabled nestedScrollEnabled showsVerticalScrollIndicator={false} scrollEventThrottle={16}
        decelerationRate="fast" snapToInterval={H} snapToAlignment="start"
        onScroll={(e) => { const i = Math.max(0, Math.min(pages.length - 1, Math.round(e.nativeEvent.contentOffset.y / H))); if (i !== at) setAt(i); }}>
        {pages.map((x, i) => (
          <Pressable key={(x.label || "") + i} onPress={x.to ? () => go(x.to) : undefined} accessibilityRole="button"
            accessibilityLabel={`${x.label} ${x.value}${x.change ? ", " + x.change : ""}${x.caption ? ", " + x.caption : ""}. ${i + 1} of ${pages.length}, ${i + 1 < pages.length ? "swipe up for more" : "swipe down for the first"}`}
            style={{ height: H, paddingVertical: 15, paddingLeft: 16, paddingRight: 24, gap: 4 }}>
            <BoxBody b={x} w={w} />
          </Pressable>
        ))}
      </ScrollView>
      <View style={{ position: "absolute", right: 10, top: 0, bottom: 0, justifyContent: "center", gap: 6 }}>
        {pages.map((x, i) => (
          <Pressable key={(x.label || "") + "dot" + i} onPress={() => ref.current?.scrollTo({ y: i * H, animated: true })} hitSlop={10} accessibilityRole="button" accessibilityLabel={`Show ${x.label}`}>
            <View style={{ width: 5, height: i === at ? 16 : 5, borderRadius: 3, backgroundColor: i === at ? C.gold : C.faint, opacity: i === at ? 1 : 0.5 }} />
          </Pressable>
        ))}
      </View>
    </View>
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
  const m = useMask();
  const left = r.icon ? <IconTile name={r.icon} tint={r.tint} /> : r.letter || r.grade ? <Letter ch={r.letter} grade={r.grade} /> : null;
  const body = (
    <>
      {left}
      <View style={{ flex: 1, minWidth: 0 }}>
        <Text style={[T.row, { color: C.text }]} numberOfLines={1}>{m(cap(r.title))}</Text>
        {r.sub ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]} numberOfLines={1}>{m(r.sub)}</Text> : null}
      </View>
      {r.chip ? <View style={{ paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, borderWidth: 1, borderColor: C.line }}><Text style={[T.small, { color: C.dim, fontWeight: "600" }]}>{r.chip}</Text></View> : null}
      {r.right ? (
        <View style={{ alignItems: "flex-end" }}>
          <Text style={[r.right_tone || /[₹$\d]/.test(r.right) ? T.row : T.meta, { color: (r.right_sub ? undefined : toneColor(r.right_tone)) ?? (/[₹$\d]/.test(r.right) ? C.text : C.dim), ...NUM }]} numberOfLines={1}>{m(r.right)}</Text>
          {r.right_sub ? <Text style={[T.meta, { color: toneColor(r.right_tone) ?? C.dim }]}>{m(r.right_sub)}</Text> : null}
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
  const m = useMask();
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
              {x.value ? <Text style={[T.small, { color: C.dim }]} numberOfLines={1}>{m(x.value)}</Text> : null}
            </View>
          </Pressable>
        ))}
      </View>
    </View>
  );
}

// ---------------------------------------------------------------------------------------------------- 7 · information page pieces, 8 · receipt
function Pill({ p }: { p: any }) {
  const m = useMask();
  const fg = toneColor(p.tone) ?? C.text;
  return (
    <View style={{ alignSelf: "flex-start", flexDirection: "row", alignItems: "center", gap: 6, height: 28, paddingHorizontal: 12, borderRadius: 999,
      backgroundColor: p.tone === "warn" ? C.warnSoft : p.tone === "good" ? C.goodSoft : p.tone === "bad" ? C.badSoft : C.card2 }}>
      {p.icon ? <Icon name={p.icon} size={14} color={fg} stroke={2.2} /> : null}
      <Text style={[T.meta, { color: fg }]}>{m(p.text)}</Text>
    </View>
  );
}
function Points({ p }: { p: any }) {
  const m = useMask();
  return (
    <View style={{ gap: 12 }}>
      {p.title ? <Text style={[T.section, { color: C.text }]}>{p.title}</Text> : null}
      {(p.items || []).map((x: any, i: number) => (
        <View key={i} style={{ flexDirection: "row", gap: 12, alignItems: "flex-start" }}>
          <Icon name={x.icon || (x.tone === "bad" ? "down" : x.tone === "good" ? "up" : "check")} color={toneColor(x.tone) ?? C.dim} />
          <Text style={[T.body, { color: C.text, flex: 1 }]}>{m(x.text)}</Text>
        </View>
      ))}
    </View>
  );
}
function KV({ p }: { p: any }) {
  const m = useMask();
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
              <Text style={[{ fontSize: r.bold ? 16 : 15, fontWeight: r.bold ? "700" : "600", ...NUM }, { color: toneColor(r.tone) ?? C.text, textAlign: "right" }]}>{m(r.v)}</Text>
              {r.v_sub ? <Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{m(r.v_sub)}</Text> : null}
            </View>
          </View>
        ))}
      </View>
      {p.foot ? <Text style={[T.meta, { color: C.dim, fontWeight: "500", paddingHorizontal: 4, paddingTop: 6 }]}>{p.foot}</Text> : null}
    </View>
  );
}
function Bars({ p }: { p: any }) {
  const m = useMask();
  return (
    <View style={[card(), { padding: 16, gap: 18 }]}>
      {p.title ? <Text style={[T.section, { color: C.text }]}>{p.title}</Text> : null}
      {(p.items || []).map((b: any) => {
        const f = Math.max(0, Math.min(1, (b.done || 0) / (b.need || 1)));
        return (
          <View key={b.name} style={{ gap: 8 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline", gap: 12 }}>
              <Text style={[T.row, { color: C.text, flexShrink: 1 }]}>{b.name}</Text>
              <Text style={[T.meta, { color: C.dim, fontWeight: "500", ...NUM }]}>{m(b.right)}</Text>
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
  const m = useMask();
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
            <Text style={[T.row, { color: C.text, ...NUM }]}>{m(x.value)}</Text>
          </View>
        ))}
      </View>
    </View>
  );
}
function Chart({ p }: { p: any }) {
  const m = useMask();
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
      {p.left || p.right ? <View style={{ flexDirection: "row", justifyContent: "space-between" }}><Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{m(p.left)}</Text><Text style={[T.meta, { color: C.dim, fontWeight: "500" }]}>{m(p.right)}</Text></View> : null}
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
// ---------------------------------------------------------------------------------------------------- 13 · price chart with ranges and timeframes
// Madhav, 10 Nov 2026 19:09: "the 4 objects in 2 boxes from home tab has to show their respective charts ... with more filters like
// 1D,5D,1M,3M,6M and timeframes of 5M,15M,30M,1H,4H,1D". The server says what fits (jarvis/chartkit.py: 4 to 300 candles a chart); this
// draws candles or a line, the two rows of chips, and a finger on the chart reads one candle.
const DAYS3 = ["Sun", "Mon", "Tue", "Wed", "Thu", "Fri", "Sat"];
const MON3 = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
const TFW: Record<string, string> = { "5M": "5-minute", "15M": "15-minute", "30M": "30-minute", "1H": "Hourly", "4H": "4-hour", "1D": "Daily" };
function group(n: number, dp: number, indian: boolean) {
  const [i, f] = Math.abs(n).toFixed(dp).split(".");
  const g = indian && i.length > 3 ? i.slice(0, -3).replace(/\B(?=(\d{2})+(?!\d))/g, ",") + "," + i.slice(-3) : i.replace(/\B(?=(\d{3})+(?!\d))/g, ",");
  return f ? `${g}.${f}` : g;
}
export function fmtAmount(v: number | null | undefined, ccy: string, signed = false) {
  if (v == null || !isFinite(v)) return "—";
  const sign = v < 0 ? "−" : signed && v > 0 ? "+" : "";
  if (ccy === "%") return `${sign}${Math.abs(v).toFixed(2)}%`;
  const dp = ccy === "₹" ? 0 : ccy === "C$" ? 2 : ccy === "$" ? (Math.abs(v) >= 1000 ? 0 : 2) : 2;
  return `${sign}${ccy}${group(v, dp, ccy === "₹")}`;
}
function tLabel(t: number, tz: number, intraday: boolean, withDay: boolean) {
  const d = new Date((t + tz * 60) * 1000);
  const day = `${DAYS3[d.getUTCDay()]} ${d.getUTCDate()} ${MON3[d.getUTCMonth()]}`;
  if (!intraday) return day;
  const hm = `${String(d.getUTCHours()).padStart(2, "0")}:${String(d.getUTCMinutes()).padStart(2, "0")}`;
  return withDay ? `${day}, ${hm}` : hm;
}
function ChipRow({ items, on, set, label }: { items: { id: string; ok?: boolean; text?: string }[]; on?: string; set: (id: string) => void; label: string }) {
  return (
    <View accessibilityLabel={label} style={{ flexDirection: "row", gap: 6 }}>
      {items.map((x) => {
        const sel = x.id === on, ok = x.ok !== false;
        return (
          <Pressable key={x.id} disabled={!ok} onPress={() => set(x.id)} accessibilityRole="button" accessibilityState={{ selected: sel, disabled: !ok }}
            accessibilityLabel={`${label} ${x.text ?? x.id}${ok ? "" : ", not offered for this range"}`}
            style={{ flex: 1, height: 32, borderRadius: 10, alignItems: "center", justifyContent: "center", backgroundColor: sel ? C.text : "transparent",
              borderWidth: sel ? 0 : 1, borderColor: C.line, opacity: ok ? 1 : 0.35 }}>
            <Text style={[T.small, { color: sel ? C.bg : C.text, fontWeight: "700" }]}>{x.text ?? x.id}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}
function PriceChart({ p }: { p: any }) {
  const [rng, setRng] = useState<string>(p.range ?? "");
  const [tf, setTf] = useState<string>(p.tf ?? "");
  const [mode, setMode] = useState<"candles" | "line">("candles");
  const { data: d, err, loading } = useData<any>(`/v3/candles/${encodeURIComponent(p.sym)}?range=${rng}&tf=${tf}`, rng === "" || rng === "1D" ? 60000 : 300000);
  const [w, setW] = useState(0);
  const [at, setAt] = useState<number | null>(null);
  const [hidden] = useHidden();
  const H = 190;
  const bars: number[][] = d?.bars ?? [];
  const ccy: string = d?.ccy ?? "";
  const veil = hidden && (ccy === "₹" || ccy === "C$");
  const fmt = (v: number, signed = false) => (veil ? `${ccy}••••` : fmtAmount(v, ccy, signed));
  const isLine = d?.kind === "line" || mode === "line";
  const n = bars.length;
  const lo = n ? Math.min(...bars.map((b) => (isLine ? b[4] : b[3]))) : 0;
  const hi = n ? Math.max(...bars.map((b) => (isLine ? b[4] : b[2]))) : 1;
  const pad = (hi - lo) * 0.08 || Math.abs(hi) * 0.01 || 1;
  const y0 = lo - pad, y1 = hi + pad;
  const Y = (v: number) => 4 + (H - 8) * (1 - (v - y0) / (y1 - y0));
  const step = n ? w / n : 1;
  const X = (i: number) => step * (i + 0.5);
  const cw = Math.max(1, Math.min(9, step * 0.62));
  const pick = (x: number) => (n ? Math.max(0, Math.min(n - 1, Math.floor(x / step))) : null);
  const cur = at != null && bars[at] ? bars[at] : null;
  const tz = d?.tz_min ?? 0, intra = !!d?.intraday;
  const chg = d?.change, pct = d?.change_pct;
  const tone = chg == null || d?.neutral ? undefined : chg > 0 ? "good" : chg < 0 ? "bad" : undefined;
  const ranges: string[] = d?.ranges ?? (p.kind === "line" ? [] : ["1D", "5D", "1M", "3M", "6M"]);
  const tfs: { id: string; ok: boolean }[] = d?.tfs ?? [];
  const head = d ? `${d.name} · ${d.kind === "line" ? (d.fell_back ? "daily closes" : `one point a ${d.market === "india" ? "session" : "night"}`) : `${TFW[d.tf] ?? d.tf} ${mode === "line" ? "closes" : "candles"}`}` : p.name;
  return (
    <View style={[card(), { padding: 16, gap: 12 }]}>
      <View style={{ flexDirection: "row", alignItems: "flex-start", justifyContent: "space-between", gap: 12, minHeight: 40 }}>
        <View style={{ flex: 1, minWidth: 0 }}>
          <Text style={[T.meta, { color: C.dim }]} numberOfLines={1}>{cur ? tLabel(cur[0], tz, intra, true) : head}</Text>
          {cur ? (
            <Text style={[T.row, { color: C.text, ...NUM }]} numberOfLines={1} adjustsFontSizeToFit>
              {isLine ? fmt(cur[4]) : `O ${fmt(cur[1])}  H ${fmt(cur[2])}  L ${fmt(cur[3])}  C ${fmt(cur[4])}`}
            </Text>
          ) : d && chg != null ? (
            <Text style={[T.row, { color: toneColor(tone) ?? C.text, ...NUM }]} numberOfLines={1}>
              {ccy === "%" ? fmtAmount(chg, "%", true) : fmt(chg, true)}{pct != null && ccy !== "%" ? ` (${fmtAmount(pct, "%", true)})` : ""}{" "}
              <Text style={{ color: C.dim, fontWeight: "500" }}>{d.over}</Text>
            </Text>
          ) : null}
        </View>
        {d?.kind === "candles" ? (
          <Pressable onPress={() => setMode(mode === "line" ? "candles" : "line")} accessibilityRole="button" accessibilityLabel={mode === "line" ? "Show candles" : "Show a line"}
            style={{ height: 32, paddingHorizontal: 12, borderRadius: 10, borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" }}>
            <Text style={[T.small, { color: C.text, fontWeight: "700" }]}>{mode === "line" ? "Candles" : "Line"}</Text>
          </Pressable>
        ) : null}
      </View>
      <View style={{ height: H }} onLayout={(e: LayoutChangeEvent) => setW(e.nativeEvent.layout.width)}
        onStartShouldSetResponder={() => n > 0} onMoveShouldSetResponder={() => n > 0}
        onResponderGrant={(e) => setAt(pick(e.nativeEvent.locationX))} onResponderMove={(e) => setAt(pick(e.nativeEvent.locationX))}
        onResponderRelease={() => setAt(null)} onResponderTerminate={() => setAt(null)}
        accessibilityLabel={d && n ? `${head}: from ${fmt(bars[0][isLine ? 4 : 1])} to ${fmt(bars[n - 1][4])}, high ${fmt(hi)}, low ${fmt(lo)}` : "Chart"}>
        {w > 20 && n ? (
          <Svg width={w} height={H} pointerEvents="none">
            {d.kind === "line" ? <Path d={`M0 ${Y(bars[0][4]).toFixed(1)}H${w}`} stroke={C.line} strokeDasharray="2 4" /> : null}
            {isLine ? (
              <Path d={bars.map((b, i) => `${i ? "L" : "M"}${X(i).toFixed(1)} ${Y(b[4]).toFixed(1)}`).join("")} stroke={C.gold} strokeWidth={2} fill="none" strokeLinejoin="round" strokeLinecap="round" />
            ) : bars.map((b, i) => {
              const col = b[4] >= b[1] ? C.good : C.bad;
              const top = Y(Math.max(b[1], b[4])), bot = Y(Math.min(b[1], b[4]));
              return (
                <G key={i}>
                  <Path d={`M${X(i).toFixed(1)} ${Y(b[2]).toFixed(1)}V${Y(b[3]).toFixed(1)}`} stroke={col} strokeWidth={1} />
                  <Rect x={X(i) - cw / 2} y={top} width={cw} height={Math.max(1, bot - top)} fill={col} />
                </G>
              );
            })}
            {isLine && n <= 40 ? bars.map((b, i) => <Circle key={i} cx={X(i)} cy={Y(b[4])} r={2.5} fill={C.gold} />) : null}
            {cur ? <Path d={`M${X(at as number).toFixed(1)} 0V${H}`} stroke={C.dim} strokeWidth={1} strokeDasharray="3 3" /> : null}
            {cur ? <Circle cx={X(at as number)} cy={Y(cur[4])} r={4} fill={C.text} stroke={C.card} strokeWidth={2} /> : null}
          </Svg>
        ) : (
          <View style={{ flex: 1, alignItems: "center", justifyContent: "center", paddingHorizontal: 12 }}>
            <Text style={[T.meta, { color: C.dim, fontWeight: "500", textAlign: "center" }]}>{err ? err : loading ? "Loading the chart…" : d?.fell_back || "Nothing to draw yet."}</Text>
          </View>
        )}
        {w > 20 && n ? <Text pointerEvents="none" style={[T.small, { position: "absolute", left: 0, top: 0, color: C.dim, ...NUM }]}>{fmt(hi)}</Text> : null}
        {w > 20 && n ? <Text pointerEvents="none" style={[T.small, { position: "absolute", left: 0, bottom: 0, color: C.dim, ...NUM }]}>{fmt(lo)}</Text> : null}
      </View>
      {n ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <Text style={[T.small, { color: C.dim }]}>{tLabel(bars[0][0], tz, intra, d.range !== "1D")}</Text>
          <Text style={[T.small, { color: C.dim }]}>{tLabel(bars[n - 1][0], tz, intra, d.range !== "1D")}</Text>
        </View>
      ) : null}
      {ranges.length > 1 ? <ChipRow label="Range" items={ranges.map((r) => ({ id: r, text: r === "ALL" ? "All" : r }))} on={d?.range ?? rng} set={(r) => { setAt(null); setRng(r); }} /> : null}
      {d?.kind === "candles" && tfs.length ? <ChipRow label="Candle" items={tfs.map((x) => ({ id: x.id, ok: x.ok }))} on={d?.tf ?? tf} set={(x) => { setAt(null); setTf(x); }} /> : null}
      {d?.fell_back && n ? <Text style={[T.meta, { color: C.warn, fontWeight: "500" }]}>{d.fell_back}</Text> : null}
      {d?.note ? <Text style={[T.small, { color: C.dim }]}>{d.note}</Text> : null}
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
  if (s.place) return <PlaceSheet key={s.place} name={s.place} />;
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

// Madhav, 10 Nov 22:12: a number on Home opens in a sheet over Home, "up to 75-80% of screen ... easy to close or swipe down to continue
// using in the same screen". It draws the same place as its page (/v3/place/<name>). It closes with a swipe down on its top (the handle
// row), a pull down past the top of its content (iPhone), a tap on the dimmed Home above it, or the X; Ask and the portfolio close it too.
const NATIVE = Platform.OS !== "web";
function PlaceSheet({ name }: { name: string }) {
  const { height } = useWindowDimensions();
  const ins = useSafeAreaInsets();
  const H = Math.round(Math.min(height * 0.78, height - ins.top - 8));
  const got = usePlace(name);
  const needs = useNeeds();
  const data = got.data;
  const y = useRef(new Animated.Value(H)).current;
  const fade = useRef(new Animated.Value(0)).current;
  const leaving = useRef(false);
  useEffect(() => {
    Animated.parallel([Animated.timing(y, { toValue: 0, duration: 260, easing: Easing.out(Easing.cubic), useNativeDriver: NATIVE }),
                       Animated.timing(fade, { toValue: 1, duration: 260, useNativeDriver: NATIVE })]).start();
  }, []);
  const dismiss = () => {
    if (leaving.current) return;
    leaving.current = true;
    Animated.parallel([Animated.timing(y, { toValue: H, duration: 200, easing: Easing.in(Easing.cubic), useNativeDriver: NATIVE }),
                       Animated.timing(fade, { toValue: 0, duration: 200, useNativeDriver: NATIVE })]).start(() => closeSheet());
  };
  const keep = useKeepRef({ dismiss, H });
  const pan = useRef(PanResponder.create({
    onStartShouldSetPanResponder: () => true,
    onMoveShouldSetPanResponder: (_e, g) => g.dy > 4 && Math.abs(g.dy) > Math.abs(g.dx),
    onPanResponderMove: (_e, g) => y.setValue(Math.max(0, g.dy)),
    onPanResponderRelease: (_e, g) => {
      if (g.dy > keep.current.H * 0.18 || g.vy > 0.8) keep.current.dismiss();
      else Animated.spring(y, { toValue: 0, bounciness: 4, useNativeDriver: NATIVE }).start();
    },
    onPanResponderTerminationRequest: () => false,
    onPanResponderTerminate: () => Animated.spring(y, { toValue: 0, bounciness: 4, useNativeDriver: NATIVE }).start(),
  })).current;
  return (
    <View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0 }}>
      <Animated.View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, opacity: fade }}>
        <Pressable onPress={dismiss} accessibilityLabel="Close" style={{ flex: 1, backgroundColor: C.overlay }} />
      </Animated.View>
      <Animated.View accessibilityViewIsModal style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: H, transform: [{ translateY: y }],
        borderTopLeftRadius: 24, borderTopRightRadius: 24, backgroundColor: C.bg, borderTopWidth: 1, borderColor: C.line, overflow: "hidden",
        maxWidth: 720, alignSelf: "center", width: "100%" }}>
        <View {...pan.panHandlers} style={[{ flexDirection: "row", alignItems: "center", height: 52, paddingHorizontal: 8 },
          NATIVE ? null : ({ userSelect: "none", cursor: "grab", touchAction: "none" } as any)]}>
          <View style={{ width: 88 }} />
          <View style={{ flex: 1, alignItems: "center" }}><View style={{ width: 40, height: 5, borderRadius: 3, backgroundColor: C.faint }} /></View>
          <HideButton />
          <Pressable onPress={dismiss} accessibilityRole="button" accessibilityLabel="Close" style={{ width: 44, height: 44, alignItems: "center", justifyContent: "center" }}>
            <Icon name="close" size={22} color={C.text} />
          </Pressable>
        </View>
        <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingHorizontal: 16, paddingTop: 4, paddingBottom: 16, gap: 16 }}
          scrollEventThrottle={16} onScrollEndDrag={(e) => { if (e.nativeEvent.contentOffset.y < -64) dismiss(); }}>
          {got.err && !data ? <Text style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>{got.err}</Text> : null}
          {data && data.ready === false ? <Text style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>{data.words}</Text> : null}
          {data && data.ready !== false ? <Parts data={data} needs={needs.data} /> : null}
          {!data && !got.err ? <Text style={{ color: C.dim, fontSize: 15 }}>Loading…</Text> : null}
        </ScrollView>
        <View style={{ paddingBottom: Math.max(ins.bottom, 8) }}><Pinned p={data?.pinned} /></View>
      </Animated.View>
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
const sheetTo = (to: any) => (to && to.place ? { ...to, as: "sheet" } : to);
const inSheet = (b: any) => ({ ...b, to: sheetTo(b.to), pages: b.pages ? b.pages.map((x: any) => ({ ...x, to: sheetTo(x.to) })) : b.pages });
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
      case "boxes": {
        const overHome = data?.name === "home";          // Madhav, 10 Nov 22:12: Home's two boxes open each number in a tall sheet over Home
        out.push(<View key={k} style={{ flexDirection: "row", gap: 12 }}>{(p.items || []).map((b: any, j: number) => <Box key={j} b={overHome ? inSheet(b) : b} tall={(p.items || []).some((x: any) => x.pages && x.pages.length > 1)} />)}</View>);
        break;
      }
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
      case "pricechart": out.push(<PriceChart key={`${k}${p.sym}`} p={p} />); break;
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
