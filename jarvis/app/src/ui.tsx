// The shared pieces every screen is built from (plan 2.4), redrawn Oct 14 to one grammar (Madhav: "consistent, easy to understand,
// max usability"; docs/design/GRAMMAR.md):
//  · type: 32 the one number · 24 screen title · 17 card title · 15 body · 13 meta and labels · 11 tab labels (theme.ts TYPE)
//  · a card is title / one number / one line / one action (StatCard); three lines above the fold, the rest behind More
//  · every list has four states: empty (one line, one action), loading (the shape), error (what happened, Retry), content (ListState)
//  · gold is for actions only; green and red for numbers and health dots only; every tappable row is 44 tall; numbers are tabular
import React, { useCallback, useEffect, useRef, useState } from "react";
import { useFocusEffect } from "expo-router";
import { Spot, setScroller, useSpotActive } from "./spotlight";
import { ActivityIndicator, Pressable, RefreshControl, ScrollView, StyleSheet, Text, View } from "react-native";
import { C, LINE, NUM, RADIUS, SPACE, TAP, TYPE, live, pnlColor } from "./theme";
import { VoiceBtn, VoiceStrip, type VoiceSpec } from "./sectionvoice";

// a card's title-row end: the section voice button (Oct 16) before the card's own action
const Ends = ({ voice, right }: { voice?: VoiceSpec; right?: React.ReactNode }) =>
  voice ? <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}><VoiceBtn v={voice} />{right}</View> : <>{right}</>;

export function Screen({ children, loading, onRefresh, pad = true }: { children: React.ReactNode; loading: boolean; onRefresh: () => void; pad?: boolean }) {
  const ref = useRef<ScrollView>(null);
  const st = useRef({ offset: { y: 0 }, height: { h: 0 }, content: { h: 0 } }).current;
  useFocusEffect(useCallback(() => { setScroller({ ref, ...st }); return () => {}; }, []));
  return (
    <ScrollView ref={ref} style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: pad ? SPACE.screen : 0, gap: SPACE.gap, paddingBottom: 40 }}
      onScroll={(e) => { st.offset.y = e.nativeEvent.contentOffset.y; }} scrollEventThrottle={64}
      onLayout={(e) => { st.height.h = e.nativeEvent.layout.height; }} onContentSizeChange={(_, h) => { st.content.h = h; }}
      refreshControl={<RefreshControl refreshing={loading} onRefresh={onRefresh} tintColor={C.dim} />}>
      {children}
    </ScrollView>
  );
}

export function Card({ title, children, right, sub, onPress, voice }: { title?: string; sub?: string; children?: React.ReactNode; right?: React.ReactNode; onPress?: () => void; voice?: VoiceSpec }) {
  const body = (
    <View style={s.card}>
      {title ? (
        <View style={[s.row, { marginBottom: 2 }]}>
          <View style={{ flex: 1 }}>
            <Text style={s.h}>{title}</Text>
            {sub ? <Text style={s.small}>{sub}</Text> : null}
          </View>
          <Ends voice={voice} right={right} />
        </View>
      ) : null}
      {children}
      {voice ? <VoiceStrip id={voice.id} /> : null}
    </View>
  );
  return onPress ? <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.75 : 1 })}>{body}</Pressable> : body;
}

// The decision line (Oct 16, Madhav: "every screen makes the agent's decision obvious in under three seconds"). The first thing
// on a screen, on the ground and not in a card: what Ananta is doing here, as one sentence. The verb and its object at the title
// size, the one reason at body size in dim, one action. It is read by size and position, never by colour: colour stays with
// numbers, health dots and actions (grammar rule 2). Every number on the screen is detail under this line.
export function Decision({ verb, rest, why, action, spot }: {
  verb: string; rest?: string; why?: string; action?: { label: string; onPress: () => void }; spot?: string;
}) {
  const body = (
    <View style={{ gap: 4, paddingHorizontal: 2, paddingTop: 2 }} accessibilityRole="header" accessibilityLabel={`${verb}${rest ? ` ${rest}` : ""}. ${why ?? ""}`}>
      <Text style={s.title}>
        {verb}
        {rest ? <Text style={{ fontWeight: "400", color: C.dim, letterSpacing: 0 }}> {rest}</Text> : null}
      </Text>
      {why ? <Text style={[s.t, { color: C.dim }]}>{why}</Text> : null}
      {action ? <Act label={action.label} onPress={action.onPress} tight /> : null}
    </View>
  );
  return spot ? <Spot id={spot} style={{ margin: 0, borderRadius: 12 }}>{body}</Spot> : body;
}

// A section label: 13, dim, sentence case ("Open · 2"), never shouting
export const Section = ({ title, right }: { title: string; right?: React.ReactNode }) => (
  <View style={[s.row, { marginTop: 2, paddingHorizontal: 2, minHeight: 24 }]}>
    <Text style={s.section}>{title}</Text>
    {right}
  </View>
);

// Gold is for actions: a text action with a 44-tall tap target (the right end of a card's action row, a section's right)
// `tight` for a card's title row (the row stays slim; hitSlop keeps the target 44)
export function Act({ label, onPress, color, tight }: { label: string; onPress: () => void; color?: string; tight?: boolean }) {
  return (
    <Pressable onPress={onPress} hitSlop={tight ? 12 : 6} accessibilityRole="button"
      style={({ pressed }) => ({ minHeight: tight ? 20 : TAP, justifyContent: "center", opacity: pressed ? 0.6 : 1 })}>
      <Text style={[s.act, color ? { color } : null]}>{label}</Text>
    </Pressable>
  );
}

// "11 Oct" from "2026-10-11" (no time-zone shift: the day is read as written)
const MONTHS = ["Jan", "Feb", "Mar", "Apr", "May", "Jun", "Jul", "Aug", "Sep", "Oct", "Nov", "Dec"];
export const dayOf = (iso?: string | null) => {
  if (!iso) return "";
  const m = String(iso).match(/^(\d{4})-(\d{2})-(\d{2})/);
  return m ? `${Number(m[3])} ${MONTHS[Number(m[2]) - 1]}` : String(iso);
};

// The card grammar: title · one number · one line · one action. Three lines above the fold; `more` opens the rest in place.
// `right` is the title row's action (e.g. "Books ›"); `meta` is the one-line footnote on the left of the action row.
export function StatCard({ title, right, value, valueColor, aside, asideColor, line, meta, action, children, more, onPress, label, voice }: {
  title: string; right?: React.ReactNode; value?: string; valueColor?: string; aside?: string; asideColor?: string; line?: React.ReactNode;
  meta?: string; action?: { label: string; onPress: () => void }; children?: React.ReactNode; more?: React.ReactNode; onPress?: () => void; label?: string;
  voice?: VoiceSpec;
}) {
  const [open, setOpen] = useState(false);
  const body = (
    <View style={s.card} accessibilityLabel={label}>
      <View style={s.row}>
        <Text style={[s.small, { flex: 1 }]} numberOfLines={1}>{title}</Text>
        <Ends voice={voice} right={right} />
      </View>
      {value != null ? (
        <View style={{ flexDirection: "row", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
          <Text style={[s.big, valueColor ? { color: valueColor } : null]}>{value}</Text>
          {aside ? <Text style={[s.aside, asideColor ? { color: asideColor } : null]}>{aside}</Text> : null}
        </View>
      ) : null}
      {typeof line === "string" ? <Text style={s.t}>{line}</Text> : line ?? null}
      {children}
      {meta || action || more ? (
        <View style={[s.row, { marginTop: -4 }]}>
          <Text style={[s.small, { flex: 1 }]} numberOfLines={open ? undefined : 1}>{meta ?? ""}</Text>
          {more ? <Act label={open ? "Show less" : "More"} onPress={() => setOpen(!open)} /> : action ? <Act label={action.label} onPress={action.onPress} /> : null}
        </View>
      ) : null}
      {open ? <View style={{ gap: 6 }}>{more}</View> : null}
      {voice ? <VoiceStrip id={voice.id} /> : null}
    </View>
  );
  return onPress ? <Pressable onPress={onPress} style={({ pressed }) => ({ opacity: pressed ? 0.75 : 1 })}>{body}</Pressable> : body;
}

// Every list has four states. Empty: one line and one action. Loading: the shape of a row, not a spinner. Error: what happened, one Retry.
export function ListState({ state, text, action, lines = 2 }: {
  state: "empty" | "loading" | "error"; text?: string; action?: { label: string; onPress: () => void }; lines?: number;
}) {
  if (state === "loading") {
    return (
      <View style={{ gap: 12, paddingVertical: 8 }} accessibilityLabel="Loading">
        {Array.from({ length: lines }).map((_, i) => (
          <View key={i} style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
            <View style={{ flex: 1, gap: 6 }}>
              <View style={[s.bone, { width: i % 2 ? "45%" : "60%" }]} />
              <View style={[s.bone, { width: i % 2 ? "70%" : "40%", height: 10 }]} />
            </View>
            <View style={[s.bone, { width: 56 }]} />
          </View>
        ))}
      </View>
    );
  }
  return (
    <View style={[s.row, { minHeight: TAP }]}>
      <Text style={[state === "error" ? s.err : s.t, { flex: 1 }]}>{text ?? (state === "error" ? "Couldn't reach the engine." : "Nothing here yet.")}</Text>
      {action ? <Act label={action.label} onPress={action.onPress} /> : null}
    </View>
  );
}

export function Line({ label, value, color, sub }: { label: string; value: React.ReactNode; color?: string; sub?: string }) {
  return (
    <View style={[s.row, { paddingVertical: 5 }]}>
      <View style={{ flex: 1 }}>
        <Text style={s.dim}>{label}</Text>
        {sub ? <Text style={s.small}>{sub}</Text> : null}
      </View>
      <Text style={[s.t, { fontWeight: "600" }, s.num, color ? { color } : null]}>{value}</Text>
    </View>
  );
}

// A tappable list row (brokerage style): left title/sub, right value/sub, chevron. 44 tall at least.
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
        {value ? <Text style={[s.rowTitle, s.num, valueColor ? { color: valueColor } : null]}>{value}</Text> : null}
        {valueSub ? <Text style={[s.small, s.num, valueSubColor ? { color: valueSubColor } : null]}>{valueSub}</Text> : null}
      </View>
      {onPress ? <Text style={{ color: C.dim, fontSize: 18, marginLeft: 6 }}>›</Text> : null}
    </Pressable>
  );
}

export const Divider = () => <View style={{ height: 1, backgroundColor: C.line }} />;

export function Btn({ label, onPress, kind = "primary", small }: { label: string; onPress: () => void; kind?: "primary" | "secondary" | "danger"; small?: boolean }) {
  const bg = kind === "primary" ? C.accent : kind === "danger" ? C.bad : C.card2;
  const fg = kind === "secondary" ? C.text : C.onInk;
  return (
    <Pressable onPress={onPress} style={({ pressed }) => [s.btn, small && { minHeight: 36, paddingVertical: 7, paddingHorizontal: 12 },
      { backgroundColor: bg, borderColor: kind === "secondary" ? C.card2 : bg, opacity: pressed ? 0.7 : 1 }]}>
      <Text style={[s.btnT, { color: fg }, small && { fontSize: 13 }]}>{label}</Text>
    </Pressable>
  );
}

export const T = ({ children, dim, small, faint, style, numberOfLines }: { children: React.ReactNode; dim?: boolean; small?: boolean; faint?: boolean; style?: any; numberOfLines?: number }) => (
  <Text numberOfLines={numberOfLines} style={[faint ? s.faint : small ? s.small : dim ? s.dim : s.t, style]}>{children}</Text>
);

export function Big({ value, label, change, changeLabel }: { value: string; label?: string; change?: number | null; changeLabel?: string }) {
  return (
    <View style={{ gap: 2 }}>
      {label ? <Text style={s.small}>{label}</Text> : null}
      <Text style={s.big}>{value}</Text>
      {changeLabel ? <Text style={[s.aside, { color: pnlColor(change) }]}>{changeLabel}</Text> : null}
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

// A small tag: words, 11 bold. Colour pairs differ in lightness, never hue alone.
export function Pill({ text, color = C.dim, bg = C.card2 }: { text: string; color?: string; bg?: string }) {
  return (
    <View style={{ backgroundColor: bg, borderRadius: 6, paddingHorizontal: 7, paddingVertical: 3, alignSelf: "flex-start" }}>
      <Text style={{ color, fontSize: TYPE.tab, lineHeight: LINE.tab, fontWeight: "700", letterSpacing: 0.3 }}>{text}</Text>
    </View>
  );
}
export const Chip = ({ text, color }: { text: string; color: string }) => <Pill text={text} color={color} />;

// A chip in a row of chips (holdings, filters): one word and one number; selected = gold border and text.
export function Tag({ text, value, valueColor, on, onPress }: { text: string; value?: string; valueColor?: string; on?: boolean; onPress?: () => void }) {
  const inner = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 6, minHeight: 32, paddingHorizontal: 11, borderRadius: RADIUS.pill, borderWidth: 1,
      borderColor: on ? C.accent : C.card2, backgroundColor: on ? C.accentSoft : C.card2 }}>
      <Text style={{ color: on ? C.accent : C.text, fontSize: TYPE.meta, lineHeight: LINE.meta, fontWeight: "600" }}>{text}</Text>
      {value ? <Text style={[{ color: valueColor ?? C.dim, fontSize: TYPE.meta, lineHeight: LINE.meta, fontWeight: "600" }, s.num]}>{value}</Text> : null}
    </View>
  );
  return onPress ? <Pressable onPress={onPress} hitSlop={4} style={({ pressed }) => ({ opacity: pressed ? 0.6 : 1 })}>{inner}</Pressable> : inner;
}

// The selected segment is gold on its soft tint; `size="lg"` for the two-way control at the top of a screen.
export function Segmented({ options, value, onChange, size = "md" }: { options: { key: string; label: string }[]; value: string; onChange: (k: string) => void; size?: "md" | "lg" }) {
  return (
    <View style={s.seg}>
      {options.map((o) => (
        <Pressable key={o.key} onPress={() => onChange(o.key)} accessibilityRole="tab" accessibilityState={{ selected: value === o.key }} style={[s.segI, value === o.key && s.segOn]}>
          <Text style={{ color: value === o.key ? C.accent : C.dim, fontWeight: value === o.key ? "700" : "600", fontSize: size === "lg" ? TYPE.body : TYPE.meta }}>{o.label}</Text>
        </Pressable>
      ))}
    </View>
  );
}

// Tap to open: keeps long explanations out of the way until asked for.
export function Expand({ title, sub, right, children, start = false, onLongPress, openWhen }: { title: string; sub?: string; right?: React.ReactNode; children: React.ReactNode; start?: boolean; onLongPress?: () => void; openWhen?: string }) {
  const [open, setOpen] = useState(start);
  const lit = useSpotActive(openWhen);
  useEffect(() => { if (lit) setOpen(true); }, [lit]);
  return (
    <View>
      <Pressable onPress={() => setOpen(!open)} onLongPress={onLongPress} delayLongPress={350} accessibilityRole="button" accessibilityState={{ expanded: open }} style={[s.rowItem]}>
        <View style={{ flex: 1 }}>
          <Text style={s.rowTitle}>{title}</Text>
          {sub ? <Text style={s.small}>{sub}</Text> : null}
        </View>
        {right}
        <Text style={{ color: C.dim, fontSize: 14, marginLeft: 8 }}>{open ? "⌃" : "⌄"}</Text>
      </Pressable>
      {open ? <View style={{ paddingBottom: 10, gap: 6 }}>{children}</View> : null}
    </View>
  );
}

export const Bullet = ({ children }: { children: React.ReactNode }) => (
  <View style={{ flexDirection: "row", gap: 8 }}>
    <Text style={s.dim}>•</Text>
    <Text style={[s.t, { flex: 1 }]}>{children}</Text>
  </View>
);

export const Dot = ({ color }: { color: string }) => <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: color }} />;

export const Busy = () => <ActivityIndicator color={C.dim} style={{ marginTop: 60 }} />;
export const ErrorBox = ({ err, onRetry }: { err: string; onRetry?: () => void }) => (
  <View style={[s.card, { backgroundColor: C.badSoft, borderColor: C.badSoft }]}>
    <ListState state="error" text={err} action={onRetry ? { label: "Retry", onPress: onRetry } : undefined} />
  </View>
);

// Money: one currency per screen. US$ for the lab's books, C$ for the account (the $500 NDAX book).
export const usd = (x?: number | null, d = 2) =>
  x == null ? "–" : `${x < 0 ? "-" : ""}$${Math.abs(x).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const usdSigned = (x?: number | null) => (x == null ? "–" : `${x >= 0 ? "+" : "-"}$${Math.abs(x).toFixed(2)}`);
export const cad = (x?: number | null, d = 2) =>
  x == null ? "–" : `${x < 0 ? "-" : ""}C$${Math.abs(x).toLocaleString(undefined, { minimumFractionDigits: d, maximumFractionDigits: d })}`;
export const cadSigned = (x?: number | null) => (x == null ? "–" : `${x >= 0 ? "+" : "-"}C$${Math.abs(x).toFixed(2)}`);
export const money = (ccy?: string | null) => (ccy === "CAD" ? cad : usd);
export const moneySigned = (ccy?: string | null) => (ccy === "CAD" ? cadSigned : usdSigned);
export const pct = (x?: number | null) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${x.toFixed(2)}%`);
export const price = (x?: number | null, ccy?: string | null) => {
  const u = ccy === "CAD" ? "C$" : "$";
  return x == null ? "–" : x >= 10 ? `${u}${x.toLocaleString(undefined, { minimumFractionDigits: 2, maximumFractionDigits: 2 })}` : x >= 0.1 ? `${u}${x.toFixed(4)}` : `${u}${x.toFixed(5)}`;
};
// "13 Oct 09:30": no seconds, no time zones in the words (the phone's own clock)
export const when = (t?: number | string | null) => {
  if (t == null || t === "") return "";
  const d = typeof t === "number" ? new Date(t * 1000) : new Date(t);
  if (isNaN(d.getTime())) return String(t);
  return d.toLocaleString(undefined, { day: "numeric", month: "short", hour: "numeric", minute: "2-digit" });
};

export const s = live(() => StyleSheet.create({
  card: { backgroundColor: C.card, borderRadius: RADIUS.card, padding: SPACE.card, gap: SPACE.line, borderWidth: 1, borderColor: C.line },
  row: { flexDirection: "row", justifyContent: "space-between", alignItems: "center", gap: 8 },
  rowItem: { flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10, minHeight: TAP },
  rowTitle: { color: C.text, fontSize: TYPE.body, lineHeight: 20, fontWeight: "600" },
  h: { color: C.text, fontSize: TYPE.card, lineHeight: LINE.card, fontWeight: "600" },
  title: { color: C.text, fontSize: TYPE.title, lineHeight: LINE.title, fontWeight: "700", letterSpacing: -0.2 },
  section: { color: C.dim, fontSize: TYPE.meta, lineHeight: LINE.meta, fontWeight: "600" },
  big: { color: C.text, fontSize: TYPE.number, lineHeight: LINE.number, fontWeight: "700", letterSpacing: -0.5, ...NUM },
  aside: { color: C.dim, fontSize: TYPE.body, lineHeight: 20, fontWeight: "600", ...NUM },
  statV: { color: C.text, fontSize: TYPE.card, lineHeight: LINE.card, fontWeight: "700", ...NUM },
  t: { color: C.text, fontSize: TYPE.body, lineHeight: 21 },
  dim: { color: C.dim, fontSize: TYPE.body, lineHeight: 21 },
  small: { color: C.dim, fontSize: TYPE.meta, lineHeight: LINE.meta },
  faint: { color: C.faint, fontSize: TYPE.meta, lineHeight: LINE.meta },
  act: { color: C.accent, fontSize: TYPE.meta, lineHeight: LINE.meta, fontWeight: "700" },
  err: { color: C.bad, fontSize: TYPE.body, lineHeight: 21 },
  num: { ...NUM },
  bone: { height: 12, borderRadius: 6, backgroundColor: C.card2 },
  btn: { minHeight: TAP, paddingVertical: 11, paddingHorizontal: 18, borderRadius: RADIUS.button, alignItems: "center", justifyContent: "center", borderWidth: 1 },
  btnT: { fontWeight: "700", fontSize: TYPE.body },
  seg: { flexDirection: "row", backgroundColor: C.card2, borderRadius: RADIUS.button, padding: 3 },
  segI: { flex: 1, alignItems: "center", justifyContent: "center", paddingVertical: 9, borderRadius: 9, minHeight: 38 },
  segOn: { backgroundColor: C.accentSoft },
}));
