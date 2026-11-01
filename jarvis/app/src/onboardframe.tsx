// The frame both onboarding flows share (canvas 'Your first run' / 'An invited person'): progress dots, a quiet top-right action,
// the step's title in 32px, its lines in 17px, the step's own picture, and the actions at the bottom (gold first, surface second).
// "Listen" reads the step aloud in Ananta's voice (the voice is the interface); nothing plays until it is tapped.
import { useEffect, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "./theme";
import { Btn, G, Meta, MicIcon2, TY } from "./newui";
import * as TTS from "./tts";
import { unlockAudio } from "./webaudio";

export function OnbFrame({ step, total, topRight, onTopRight, onBack, title, lines, extra, cta, onCta, secondary, onSecondary, busy }: {
  step: number; total: number; topRight?: string; onTopRight?: () => void; onBack?: () => void; title: string; lines: string[];
  extra?: React.ReactNode; cta: string; onCta: () => void; secondary?: string; onSecondary?: () => void; busy?: boolean;
}) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  const [speaking, setSpeaking] = useState(false);
  useEffect(() => { TTS.init(); return () => { TTS.stop(); }; }, []);
  useEffect(() => { TTS.stop(); setSpeaking(false); }, [step]);
  const listen = async () => {
    if (speaking) { TTS.stop(); setSpeaking(false); return; }
    unlockAudio();
    setSpeaking(true);
    try { await TTS.speakText([title, ...lines].join(" ")); } finally { setSpeaking(false); }
  };
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <View style={{ paddingTop: ins.top + 14, paddingHorizontal: 16, flexDirection: "row", alignItems: "center", justifyContent: "space-between", minHeight: 44 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
          {onBack ? (
            <Pressable onPress={onBack} accessibilityRole="button" accessibilityLabel="Back" style={{ minHeight: 44, justifyContent: "center", paddingRight: 4 }}>
              <Text style={[TY.meta, { color: C.dim }]}>‹ Back</Text>
            </Pressable>
          ) : null}
          <View style={{ flexDirection: "row", gap: 6 }} accessibilityLabel={`Step ${step + 1} of ${total}`}>
            {Array.from({ length: total }).map((_, i) => (
              <View key={i} style={{ width: i === step ? 24 : 8, height: 8, borderRadius: 999, backgroundColor: i === step ? G.gold() : i < step ? C.dim : C.card2 }} />
            ))}
          </View>
        </View>
        {topRight ? (
          onTopRight ? (
            <Pressable onPress={onTopRight} accessibilityRole="button" style={{ minHeight: 44, justifyContent: "center" }}><Text style={[TY.meta, { color: C.dim }]}>{topRight}</Text></Pressable>
          ) : <Meta>{topRight}</Meta>
        ) : null}
      </View>
      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingHorizontal: 24, paddingTop: 48, paddingBottom: 24, gap: 16, maxWidth: 560, width: "100%", alignSelf: "center" }}>
        <Text style={{ fontSize: 32, lineHeight: 38, fontWeight: "700", letterSpacing: -0.5, color: C.text }} accessibilityRole="header">{title}</Text>
        {lines.map((l) => <Text key={l} style={{ fontSize: 17, lineHeight: 26, color: C.dim }}>{l}</Text>)}
        <Pressable onPress={listen} accessibilityRole="button" accessibilityLabel={speaking ? "Stop" : "Listen"}
          style={{ flexDirection: "row", alignItems: "center", gap: 8, alignSelf: "flex-start", backgroundColor: speaking ? G.goldSoft() : C.card2, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6, minHeight: 36 }}>
          <MicIcon2 color={speaking ? G.gold() : C.dim} size={16} />
          <Text style={[TY.meta, { color: speaking ? G.gold() : C.dim }]}>{speaking ? "Stop" : "Listen"}</Text>
        </Pressable>
        {extra}
      </ScrollView>
      <View style={{ paddingHorizontal: 24, paddingBottom: Math.max(ins.bottom, 16) + 16, paddingTop: 8, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center" }}>
        <Btn label={busy ? "One moment…" : cta} kind="p" onPress={busy ? undefined : onCta} style={{ width: "100%" }} />
        {secondary ? <Btn label={secondary} kind="s" onPress={onSecondary} style={{ width: "100%" }} /> : null}
      </View>
    </View>
  );
}

export function BigOrbArt({ size = 120 }: { size?: number }) {
  return (
    <View style={{ alignItems: "center", marginTop: 16 }}>
      <View style={{ width: size, height: size, borderRadius: 999, backgroundColor: G.gold(), alignItems: "center", justifyContent: "center",
        shadowColor: C.gold, shadowOpacity: 0.35, shadowRadius: 24, shadowOffset: { width: 0, height: 8 } }}>
        <View style={{ position: "absolute", left: -16, top: -16, right: -16, bottom: -16, borderRadius: 999, borderWidth: 2, borderColor: G.glow() }} />
        <MicIcon2 color={G.onGold()} size={Math.round(size * 0.36)} />
      </View>
    </View>
  );
}
