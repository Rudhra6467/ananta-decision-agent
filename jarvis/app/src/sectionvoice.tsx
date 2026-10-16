// The section voice button (Madhav, Oct 16): "Ask Ananta" in the corner of a section, so voice can be handled from anywhere.
//  · Voice off: one tap opens Ask Ananta, where Ananta says what this section is (from the same numbers it shows) with questions
//    that fit it, then brings him back to the section with voice still on.
//  · Back at the section the same button reads "End voice": he can keep talking, or end it right there.
//  · Voice already on: another section's button talks about that section right where he is (no trip to Ask Ananta).
//  · While voice is on, the section shows what Ananta is doing, what it said last, and the questions (a tap asks it aloud).
// Nothing here talks to the service: the explanation is built from the section's own numbers (free and instant); the questions
// and the follow-ups go through the one voice conversation in the Ask Ananta tab.
import { useEffect, useRef } from "react";
import { Animated, Pressable, Text, View } from "react-native";
import { askSection, getVoiceApi, goTab, useNarrating, useVoiceFeed, useVoiceLive, useVoiceOrigin, useVoicePhase, type SectionReq } from "./context";
import * as Haptics from "./haptics";
import { C } from "./theme";

// what a section hands over: `say` may be a function so it is built from the numbers at the moment of the tap
export type VoiceSpec = Omit<SectionReq, "say"> & { say: string | (() => string) };
const asReq = (v: VoiceSpec): SectionReq => ({ ...v, say: typeof v.say === "function" ? v.say() : v.say });

export function VoiceBtn({ v }: { v: VoiceSpec }) {
  const live = useVoiceLive();
  const origin = useVoiceOrigin();
  const narr = useNarrating();
  const mine = (live && origin?.id === v.id) || narr?.id === v.id;       // End from the moment Ananta starts explaining it
  const tap = () => {
    Haptics.tap();
    const api = getVoiceApi();
    if (mine) { api?.end(); return; }
    if (live && api) { api.section(asReq(v)); return; }
    askSection(asReq(v));
  };
  if (mine) {
    return (
      <Pressable onPress={tap} hitSlop={8} accessibilityRole="button" accessibilityLabel="End voice"
        style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 6, height: 32, paddingHorizontal: 12, borderRadius: 16,
          backgroundColor: C.bad, opacity: pressed ? 0.75 : 1 })}>
        <View style={{ width: 9, height: 9, borderRadius: 2, backgroundColor: C.onInk }} />
        <Text style={{ color: C.onInk, fontSize: 13, fontWeight: "800" }}>End voice</Text>
      </Pressable>
    );
  }
  return (
    <Pressable onPress={tap} hitSlop={8} accessibilityRole="button" accessibilityLabel={`Ask Ananta about ${v.label}`}
      style={({ pressed }) => ({ width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center",
        backgroundColor: live ? C.accent : C.accentSoft, opacity: pressed ? 0.7 : 1 })}>
      <Bars color={live ? C.onInk : C.accent} />
    </Pressable>
  );
}

// Under the section while voice is on and this is the section being talked about.
export function VoiceStrip({ id }: { id: string }) {
  const live = useVoiceLive();
  const origin = useVoiceOrigin();
  const phase = useVoicePhase();
  const feed = useVoiceFeed();
  if (!live || origin?.id !== id) return null;
  const f = feed?.section === id ? feed : null;
  const chips = (f?.chips?.length ? f.chips : origin.questions ?? []).slice(0, 4);
  const word = phase === "thinking" ? "Thinking…" : phase === "speaking" ? "Speaking · tap End voice to stop" : "Listening · just talk, or tap a question";
  const dot = phase === "speaking" ? C.good : phase === "thinking" ? C.warn : C.accent;
  return (
    <View style={{ backgroundColor: C.card2, borderRadius: 12, padding: 10, gap: 8 }} accessibilityLiveRegion="polite">
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <Pulse color={dot} />
        <Text style={{ color: C.text, fontSize: 13, fontWeight: "700", flex: 1 }}>Ananta · {word}</Text>
      </View>
      {f?.heard ? <Text style={{ color: C.dim, fontSize: 12 }} numberOfLines={1}>You: “{f.heard}”</Text> : null}
      {f?.answer ? (
        <Text onPress={() => goTab("/(tabs)/ask")} style={{ color: C.text, fontSize: 14, lineHeight: 20 }} numberOfLines={4}>{f.answer}</Text>
      ) : null}
      {chips.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
          {chips.map((q) => (
            <Pressable key={q} onPress={() => { Haptics.tap(); getVoiceApi()?.ask(q); }} disabled={phase === "thinking"} accessibilityRole="button"
              style={({ pressed }) => ({ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 11, minHeight: 32,
                justifyContent: "center", opacity: pressed || phase === "thinking" ? 0.6 : 1 })}>
              <Text style={{ color: C.accent, fontSize: 13, fontWeight: "600" }}>{q}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

function Pulse({ color }: { color: string }) {
  const a = useRef(new Animated.Value(1)).current;
  useEffect(() => {
    const l = Animated.loop(Animated.sequence([Animated.timing(a, { toValue: 0.35, duration: 600, useNativeDriver: true }),
      Animated.timing(a, { toValue: 1, duration: 600, useNativeDriver: true })]));
    l.start();
    return () => l.stop();
  }, []);
  return <Animated.View style={{ width: 9, height: 9, borderRadius: 5, backgroundColor: color, opacity: a }} />;
}

// the voice wave, small: the same mark as the Ask Ananta tab
export function Bars({ color, h = 1 }: { color: string; h?: number }) {
  return (
    <View style={{ flexDirection: "row", gap: 2, alignItems: "center" }}>
      {[6, 11, 15, 11, 6].map((x, i) => <View key={i} style={{ width: 2.5, height: x * h, backgroundColor: color, borderRadius: 2 }} />)}
    </View>
  );
}

// spoken money: "275 dollars", "7 dollars 50", never "minus dollar sign"
export function sayMoney(v: number | null | undefined, ccy: "USD" | "CAD" = "USD") {
  if (v == null || !isFinite(v)) return "unknown";
  const a = Math.abs(v), unit = ccy === "CAD" ? "Canadian dollars" : "dollars";
  if (a >= 1000) return `${Math.round(a).toLocaleString("en-US")} ${unit}`;
  const d = Math.floor(a), c = Math.round((a - d) * 100);
  return c ? `${d} ${unit} ${c}` : `${d} ${unit}`;
}
export const upDown = (v: number | null | undefined) => (v == null ? "" : v >= 0 ? "up" : "down");

// written facts, read aloud: "2026-10-14" -> "14 October", "average (80,299)" -> "average of 80,299"
const MONTH = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"];
export function spoken(t: string) {
  return String(t ?? "")
    .replace(/(\d{4})-(\d{2})-(\d{2})/g, (_, y, m, d) => `${Number(d)} ${MONTH[Number(m) - 1]}`)
    .replace(/\s*\(([^)]*)\)/g, " of $1")
    .replace(/\s+/g, " ").trim();
}
