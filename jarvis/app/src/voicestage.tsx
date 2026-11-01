// The voice-first Ask (Madhav, 1 Nov 2026: "first ask voice", gate 2 "all looks good"; the canvas board "Ask · voice-first"). The
// ChatGPT-voice shape on top of the existing voice loop (src/voiceloop.ts, src/tts.ts): his question small and dim, Ananta's answer large
// with the sentence being spoken lit on gold-soft, the big gold orb with its state in words, two or three follow-ups, and the keyboard and
// the full conversation a tap away. Nothing about how voice works changes here: only how it looks in the new look.
import { useEffect, useRef, useState } from "react";
import { Animated, Pressable, ScrollView, Text, View } from "react-native";
import { C } from "./theme";
import { G, MicIcon2, PillLink, TY } from "./newui";
import { getSpoken, sentences, subscribeSpoken } from "./uiagent";
import type { Phase } from "./voiceloop";

export function useSpokenNow() {
  const [s, setS] = useState(getSpoken());
  useEffect(() => subscribeSpoken(() => setS(getSpoken())), []);
  return s;
}

// The answer, sentence by sentence: said = ink, being said = ink on gold-soft, to come = dim. When nothing of this answer is being spoken
// (a typed turn, or speech finished), all of it is ink.
export function SpokenAnswer({ text }: { text: string }) {
  const sp = useSpokenNow();
  const parts = sentences(text || "");
  const live = sp.text && sp.text.trim() === String(text || "").trim() && sp.i >= 0 && sp.i < parts.length;
  return (
    <Text style={[TY.spoken, { color: C.text }]}>
      {parts.map((p, i) => {
        const done = !live || i < sp.i;
        const now = live && i === sp.i;
        return (
          <Text key={i} style={now ? { backgroundColor: G.goldSoft(), color: C.text } : { color: done ? C.text : C.dim }}>
            {p}{i < parts.length - 1 ? " " : ""}
          </Text>
        );
      })}
    </Text>
  );
}

function BigOrb({ phase, hearing, ready, level, onPress, idle }: { phase: Phase | "off"; hearing: boolean; ready: boolean; level: number; onPress: () => void; idle?: boolean }) {
  const pulse = useRef(new Animated.Value(1)).current;
  const fast = phase === "thinking";
  useEffect(() => {
    const d = fast ? 380 : 1200;                       // motion-breath when listening, quicker while thinking
    const a = Animated.loop(Animated.sequence([Animated.timing(pulse, { toValue: fast ? 1.05 : 1.08, duration: d, useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: d, useNativeDriver: true })]));
    if (phase !== "speaking") a.start();
    return () => a.stop();
  }, [fast, phase]);
  const lv = Math.max(0, Math.min(1, (level + 60) / 50));
  const scale = hearing ? 1 + lv * 0.18 : pulse;
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={idle ? "Tap and talk" : "Voice"} hitSlop={20}>
      <Animated.View style={{ transform: [{ scale: scale as any }], width: 112, height: 112, borderRadius: 999, backgroundColor: G.gold(),
        opacity: !idle && phase === "listening" && !ready ? 0.45 : 1, alignItems: "center", justifyContent: "center",
        shadowColor: C.gold, shadowOpacity: 0.4, shadowRadius: 24, shadowOffset: { width: 0, height: 8 }, elevation: 10 }}>
        <View style={{ position: "absolute", left: -16, top: -16, right: -16, bottom: -16, borderRadius: 999, borderWidth: 2, borderColor: G.glow() }} />
        {idle || phase === "listening" ? <MicIcon2 color={G.onGold()} size={40} /> : <Wave color={G.onGold()} busy={phase === "thinking"} />}
      </Animated.View>
    </Pressable>
  );
}

function Wave({ color, busy }: { color: string; busy?: boolean }) {
  const hs = busy ? [10, 14, 10, 14, 10] : [12, 26, 38, 26, 12];
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 5 }}>
      {hs.map((h, i) => <View key={i} style={{ width: 5, height: h, borderRadius: 3, backgroundColor: color }} />)}
    </View>
  );
}

export function VoiceStage({ question, answer, followUps, phase, hearing, ready, level, note, onOrb, onEnd, onPick, onShowChat, talkingWith }: {
  question?: string; answer?: string; followUps?: string[]; phase: Phase | "off"; hearing: boolean; ready: boolean; level: number; note?: string;
  onOrb: () => void; onEnd: () => void; onPick: (q: string) => void; onShowChat: () => void; talkingWith?: string;
}) {
  const scroll = useRef<ScrollView | null>(null);
  const sp = useSpokenNow();
  useEffect(() => { scroll.current?.scrollToEnd({ animated: true }); }, [answer, sp.i]);
  const [name, detail] = phase === "thinking" ? ["Thinking", "tap the orb to cancel"]
    : phase === "speaking" ? ["Speaking", "tap the orb to stop and talk"]
    : hearing ? ["Hearing you", "pause to think · tap the orb when you finish"]
    : !ready ? ["Getting ready", "one moment, then just talk"]
    : ["Listening", "just talk"];
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center", paddingHorizontal: 16, paddingTop: 8 }}>
        <Text style={[TY.meta, { color: C.dim }]}>{talkingWith ? `Talking with ${talkingWith}` : "Voice"}</Text>
        <Pressable onPress={onShowChat} accessibilityRole="button" style={{ minHeight: 36, justifyContent: "center", paddingHorizontal: 6 }}>
          <Text style={[TY.meta, { color: G.gold() }]}>Show the conversation</Text>
        </Pressable>
      </View>
      <ScrollView ref={scroll} style={{ flex: 1 }} contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 24, paddingBottom: 16, gap: 18 }}>
        {question ? (
          <View>
            <Text style={[TY.meta, { color: C.faint }]}>You asked</Text>
            <Text style={{ fontSize: 17, lineHeight: 24, color: C.dim, marginTop: 4 }}>{question}</Text>
          </View>
        ) : (
          <Text style={{ fontSize: 24, lineHeight: 32, fontWeight: "600", color: C.text }}>Ask me anything about the market, your holdings or Monday's plan.</Text>
        )}
        {answer ? <SpokenAnswer text={answer} /> : null}
        {answer && followUps?.length && phase !== "speaking" ? (
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
            {followUps.slice(0, 3).map((q) => <PillLink key={q} label={q} onPress={() => onPick(q)} />)}
          </View>
        ) : null}
      </ScrollView>
      <View style={{ alignItems: "center", gap: 14, paddingTop: 12, paddingBottom: 18 }}>
        <BigOrb phase={phase} hearing={hearing} ready={ready} level={level} onPress={onOrb} />
        <View style={{ alignItems: "center", gap: 2 }}>
          <Text style={[TY.card, { color: C.text }]}>{name}</Text>
          <Text style={[TY.meta, { color: C.dim, textAlign: "center", paddingHorizontal: 24 }]}>{note || detail}</Text>
        </View>
        <Pressable onPress={onEnd} accessibilityRole="button" accessibilityLabel="End voice"
          style={{ backgroundColor: C.card2, borderRadius: 12, minHeight: 44, paddingHorizontal: 22, justifyContent: "center" }}>
          <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>End voice · type instead</Text>
        </Pressable>
      </View>
    </View>
  );
}

// The resting state of the new Ask (no conversation yet): the orb big in the middle, "Tap and talk", a few starters.
export function VoiceIdle({ onTalk, starters, onPick, prevTitle, onPrev }: { onTalk: () => void; starters: string[]; onPick: (q: string) => void; prevTitle?: string; onPrev?: () => void }) {
  return (
    <View style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 22, paddingHorizontal: 24 }}>
      <Text style={{ fontSize: 24, lineHeight: 32, fontWeight: "600", color: C.text, textAlign: "center" }}>What would you like to know?</Text>
      <BigOrb phase="off" hearing={false} ready level={-60} onPress={onTalk} idle />
      <Text style={[TY.meta, { color: C.dim }]}>Tap and talk · or type below</Text>
      <View style={{ flexDirection: "row", flexWrap: "wrap", justifyContent: "center", gap: 8 }}>
        {starters.slice(0, 4).map((q) => <PillLink key={q} label={q} onPress={() => onPick(q)} />)}
      </View>
      {prevTitle && onPrev ? (
        <Pressable onPress={onPrev} accessibilityRole="button" style={{ minHeight: 40, justifyContent: "center" }}>
          <Text style={[TY.meta, { color: G.gold() }]}>Continue: {prevTitle} ›</Text>
        </Pressable>
      ) : null}
    </View>
  );
}
