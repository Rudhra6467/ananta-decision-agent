import { Stack, router, usePathname, useRootNavigationState } from "expo-router";
import { StatusBar } from "expo-status-bar";
import { useEffect, useRef } from "react";
import { Platform, Pressable, Text, View } from "react-native";
import { token } from "../src/api";
import { Toast, loadMe } from "../src/visitor";
import { loadNames } from "../src/names";
import { HomeScreenHint } from "../src/homescreen";
import { goTab, tourCommand, useHere, useTour, useVoiceLive } from "../src/context";
import * as TTS from "../src/tts";
import { C, deviceTheme, setTheme, useThemeVersion } from "../src/theme";

export default function Root() {
  const path = usePathname();
  const nav = useRootNavigationState();                // wait until the app's navigation is ready, or the move to sign-in is lost
  const checked = useRef(false);
  useEffect(() => {
    if (!nav?.key || checked.current) return;
    checked.current = true;
    if (path.startsWith("/join") || path.startsWith("/login")) return;   // an invite link opens without a sign-in
    token().then(async (t) => {
      if (!t) { router.replace("/login"); return; }
      loadNames();                                       // display names for internal codes (plan 2.3)
      const m = await loadMe();                          // a visitor who has not finished setup continues it
      const th = m?.profile?.theme;                       // a new device takes the account's theme; this device's own choice wins after that
      if (!deviceTheme() && (th === "bat" || th === "light")) setTheme(th);
      if (m?.guest && ["name", "coins", "capital"].includes(String(m.stage)) && !path.startsWith("/welcome")) router.replace("/welcome");
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
    </View>
  );
}

// While voice mode is on and Ananta has moved you to another screen, this pill shows it is still listening.
function VoicePill() {
  const live = useVoiceLive();
  const here = useHere();
  if (!live || here?.screen === "ananta") return null;
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", top: 56, left: 0, right: 0, alignItems: "center" }}>
      <Pressable onPress={() => goTab("/(tabs)/ask")} style={{ flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: C.text,
        borderRadius: 999, paddingHorizontal: 14, paddingVertical: 7, shadowColor: "#000", shadowOpacity: 0.2, shadowRadius: 6 }}>
        <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: C.bad }} />
        <Text style={{ color: C.onInk, fontWeight: "600", fontSize: 13 }}>Ananta is listening · tap to return</Text>
      </Pressable>
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
