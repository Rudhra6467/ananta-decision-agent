// The redesign's five places (Madhav, 10 Nov 2026: "yes for all your recommendations"): Home · Markets · Ask (the orb) · Activity · More,
// on one floating bar (block 12 of the design canvas). The old new look's Today, Money, Proof and People moved down a level: Money is the
// account page opened from Home, Proof and People sit under More; nothing was removed (jarvis/service/places.py and jarvis/india/places.py
// write every place). Swiping left and right between the places stays (9 Nov, TestFlight).
import SwipeTabs from "expo-router/js-top-tabs";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "../../src/theme";
import { Orb } from "../../src/newui";
import { Icon } from "../../src/place";
import { ScreenError } from "../../src/safe";
import { pressOrb, useTyping } from "../../src/once";

export const ErrorBoundary = ScreenError;

const TABS: { name: string; label: string }[] = [
  { name: "home", label: "Home" }, { name: "markets", label: "Markets" }, { name: "ask", label: "" }, { name: "activity", label: "Activity" }, { name: "more", label: "More" },
];

function Bar({ state, navigation }: any) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  const active = state.routes[state.index]?.name;
  const typing = useTyping();
  if (typing && active === "ask") return null;             // 3 Nov: while he types in Ask the bar steps aside
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", left: 0, right: 0, bottom: Math.max(ins.bottom, 12), alignItems: "center" }}>
      <View accessibilityRole="tablist" style={{ width: "100%", maxWidth: 520, paddingHorizontal: 16 }}>
        <View style={{ height: 64, borderRadius: 32, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, flexDirection: "row", alignItems: "center",
          shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 8 }}>
          {TABS.map((t) => {
            if (!t.label) {
              return (
                <View key={t.name} style={{ flex: 1, alignItems: "center", marginTop: -26 }}>
                  {/* 7 Nov (Madhav): first press opens Ask; on Ask already, the same press starts the voice */}
                  <Orb size={56} mic={active === "ask"} label={active === "ask" ? "Talk to Ananta" : "Ask Ananta"}
                    onPress={() => { if (active === "ask") pressOrb(); else navigation.navigate("ask"); }} />
                </View>
              );
            }
            const on = active === t.name;
            const col = on ? C.text : C.dim;
            return (
              <Pressable key={t.name} accessibilityRole="tab" accessibilityLabel={t.label} accessibilityState={{ selected: on }}
                onPress={() => {
                  // 7 Nov: the place's own button, pressed while on it, takes the page back to the top (useScrollToTop)
                  const route = state.routes.find((r: any) => r.name === t.name);
                  const ev = navigation.emit({ type: "tabPress", target: route?.key, canPreventDefault: true });
                  if (!on && !ev.defaultPrevented) navigation.navigate(t.name);
                }} style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 2, minHeight: 48 }}>
                <Icon name={t.name} size={24} color={col} />
                <Text style={{ color: col, fontSize: 11, lineHeight: 14, fontWeight: "700" }}>{t.label}</Text>
              </Pressable>
            );
          })}
        </View>
      </View>
    </View>
  );
}

export default function NewLayout() {
  useThemeVersion();
  return (
    <SwipeTabs tabBarPosition="bottom" initialRouteName="home" tabBar={(p: any) => <Bar {...p} />}
      screenOptions={{ lazy: true, swipeEnabled: true, animationEnabled: true, sceneStyle: { backgroundColor: C.bg } } as any}>
      <SwipeTabs.Screen name="home" />
      <SwipeTabs.Screen name="markets" />
      <SwipeTabs.Screen name="ask" />
      <SwipeTabs.Screen name="activity" />
      <SwipeTabs.Screen name="more" />
    </SwipeTabs>
  );
}
