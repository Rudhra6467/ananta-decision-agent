import { Stack, router, usePathname, useRootNavigationState } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useRef } from "react";
import { Platform, Pressable, Text, View } from "react-native";
import { token } from "../src/api";
import { Toast, loadMe } from "../src/visitor";
import { loadNames } from "../src/names";
import { HomeScreenHint } from "../src/homescreen";
import { getVoiceApi, goTab, tourCommand, useHere, useNarrating, useTour, useVoiceLive, useVoicePhase } from "../src/context";
import * as TTS from "../src/tts";
import { C, deviceTheme, setTheme, useThemeVersion } from "../src/theme";

export default function Root() {
  const path = usePathname();
  const nav = useRootNavigationState();                // wait until the app's navigation is ready, or the move to sign-in is lost
  const checked = useRef(false);
  useEffect(() => {
    if (!nav?.key || checked.current) return;
    checked.current = true;
    if (path.startsWith("/join") || path.startsWith("/login") || path.startsWith("/feedback")) return;   // invite link, sign-in, feedback form
    token().then(async (t) => {
      if (!t) { router.replace("/login"); return; }
      loadNames();                                       // display names for internal codes (plan 2.3)
      const m = await loadMe();                          // a visitor who has not finished setup continues it
      const th = m?.profile?.theme;                       // a new device takes the account's theme; this device's own choice wins after that
      if (!deviceTheme() && (th === "bat" || th === "light")) setTheme(th);
      TTS.useAccountVoice(m?.profile?.voice);            // plan 3.7: Deep for Madhav unless this device picked another voice
      if (m?.guest && m.onboard && m.onboard !== "done" && !path.startsWith("/ask")) goTab("/(tabs)/ask");   // Phase 5: the first conversation
    });
  }, [nav?.key]);
  const v = useThemeVersion();                           // a theme change redraws everything with the new colours
  if (Platform.OS === "web" && typeof document !== "undefined") document.documentElement.style.background = C.bg;
  return (
    <View key={v} style={{ flex: 1, backgroundColor: C.bg }}>
      <StatusBar style={C.bar} />
      <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }} />
      <VoicePill />
      <TourBar />
      <Toast />
      <HomeScreenHint />
      {/* the ⚑ Flag button left every screen on 25 Oct (Madhav): flags are said to Ananta, and "show my flags" opens My flags */}
    </View>
  );
}

// While voice mode is on and you are on another screen, this pill shows what Ananta is doing; tap it to return to the
// conversation, or End to stop voice right here (Oct 16: voice can be handled from anywhere in the app).
function VoicePill() {
  const live = useVoiceLive();
  const here = useHere();
  const phase = useVoicePhase();
  const narr = useNarrating();
  if ((!live && !narr) || here?.screen === "ananta") return null;
  const word = narr ? `Explaining ${narr.label}` : phase === "thinking" ? "Ananta is thinking" : phase === "speaking" ? "Ananta is speaking" : "Ananta is listening";
  const dot = phase === "speaking" ? C.good : phase === "thinking" ? C.warn : C.bad;
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", top: 56, left: 0, right: 0, alignItems: "center" }}>
      <View style={{ flexDirection: "row", alignItems: "center", backgroundColor: C.text, borderRadius: 999, paddingLeft: 14, paddingRight: 4,
        shadowColor: "#000", shadowOpacity: 0.2, shadowRadius: 6 }}>
        <Pressable onPress={() => goTab("/(tabs)/ask")} accessibilityRole="button" accessibilityLabel={`${word}, tap to return`}
          style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 7 }}>
          <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: dot }} />
          <Text style={{ color: C.onInk, fontWeight: "600", fontSize: 13 }}>{word} · tap to return</Text>
        </Pressable>
        <Pressable onPress={() => getVoiceApi()?.end()} accessibilityRole="button" accessibilityLabel="End voice" hitSlop={6}
          style={{ marginLeft: 10, backgroundColor: C.bad, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 5 }}>
          <Text style={{ color: C.onInk, fontWeight: "800", fontSize: 12 }}>End</Text>
        </Pressable>
      </View>
    </View>
  );
}

// Caption bar during a tour: what Ananta is saying, with Skip and Stop.
function TourBar() {
  const t = useTour();
  if (!t.active) return null;
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", left: 12, right: 12, bottom: 96 }}>
      <View style={{ backgroundColor: C.ink, borderRadius: 16, padding: 14, gap: 10, shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 10 }}>
        <Text style={{ color: C.inkDim, fontSize: 11, fontWeight: "700", letterSpacing: 0.6 }}>TOUR · {t.i} OF {t.n}</Text>
        <Text style={{ color: C.onInk, fontSize: 15, lineHeight: 21 }}>{t.text}</Text>
        {t.deeper ? (
          <Pressable onPress={() => { tourCommand("deeper"); TTS.stop(); }} style={{ backgroundColor: C.onInk, borderRadius: 10, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.ink, fontWeight: "800" }}>Go deeper ›</Text>
          </Pressable>
        ) : null}
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Pressable onPress={() => { tourCommand("next"); TTS.stop(); }} style={{ flex: 1, backgroundColor: C.inkBtn, borderRadius: 10, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.onInk, fontWeight: "700" }}>Skip ›</Text>
          </Pressable>
          <Pressable onPress={() => { tourCommand("stop"); TTS.stop(); }} style={{ flex: 1, backgroundColor: C.accent, borderRadius: 10, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.onInk, fontWeight: "700" }}>Stop tour</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}
