// The new look's shell (31 Oct 2026, gate 1): five surfaces on a bottom bar - Today, Money, (Ask as the orb), Proof, People - each
// answering one question. The classic tabs (app/(tabs)) stay untouched; More › "New look" switches between them (src/look.ts).
import SwipeTabs from "expo-router/js-top-tabs";        // 9 Nov 2026 (Madhav, TestFlight): swipe left / right between the tabs, as the classic look does
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "../../src/theme";
import { CheckIcon2, DollarIcon, G, Orb, PeopleIcon, RupeeIcon, SunIcon, TY } from "../../src/newui";
import { useMarket } from "../../src/market";
import { ScreenError } from "../../src/safe";
import { pressOrb, useTyping } from "../../src/once";

export const ErrorBoundary = ScreenError;

const TABS: { name: string; label: string; Icon: any }[] = [
  { name: "today", label: "TODAY", Icon: SunIcon }, { name: "money", label: "MONEY", Icon: RupeeIcon }, { name: "ask", label: "", Icon: null },
  { name: "proof", label: "PROOF", Icon: CheckIcon2 }, { name: "people", label: "PEOPLE", Icon: PeopleIcon },
];

function Bar({ state, navigation }: any) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  const active = state.routes[state.index]?.name;
  const mk = useMarket();
  const typing = useTyping();
  // Madhav, 3 Nov: while he types in Ask the bar (and its raised orb) steps aside, so the typing box is never covered
  if (typing && active === "ask") return null;
  return (
    <View style={{ backgroundColor: C.card, borderTopWidth: 1, borderTopColor: C.line, paddingBottom: Math.max(ins.bottom, 10), paddingTop: 10, paddingHorizontal: 8, flexDirection: "row", justifyContent: "space-around" }}>
      {TABS.map((t) => {
        if (!t.Icon) {
          return (
            <View key={t.name} style={{ width: 64, alignItems: "center", marginTop: active === "ask" ? -14 : -34 }}>
              {/* 7 Nov (Madhav): first press opens Ask; on Ask already, the same press starts the voice */}
              <Orb mic={active === "ask"} label={active === "ask" ? "Talk to Ananta" : "Ask Ananta"} onPress={() => { if (active === "ask") pressOrb(); else navigation.navigate("ask"); }} />
            </View>
          );
        }
        const on = active === t.name;
        const col = on ? G.gold() : C.dim;
        const Icon = t.name === "money" && mk === "crypto" ? DollarIcon : t.Icon;   // 1 Nov: crypto's money is in dollars
        return (
          <Pressable key={t.name} accessibilityRole="tab" accessibilityLabel={t.label} accessibilityState={{ selected: on }}
            onPress={() => {
              // 7 Nov (Madhav): the tab's own button, pressed while on that tab, takes the page back to the top (the screens listen with
              // useScrollToTop); the event is the one React Navigation's bar would send, so a screen can also prevent the switch
              const route = state.routes.find((r: any) => r.name === t.name);
              const ev = navigation.emit({ type: "tabPress", target: route?.key, canPreventDefault: true });
              if (!on && !ev.defaultPrevented) navigation.navigate(t.name);
            }} style={{ width: 64, alignItems: "center", gap: 4, minHeight: 44 }}>
            <Icon color={col} />
            <Text style={[TY.tab, { color: col }]}>{t.label}</Text>
          </Pressable>
        );
      })}
    </View>
  );
}

export default function NewLayout() {
  useThemeVersion();
  return (
    <SwipeTabs tabBarPosition="bottom" initialRouteName="today" tabBar={(p: any) => <Bar {...p} />}
      screenOptions={{ lazy: true, swipeEnabled: true, animationEnabled: true, sceneStyle: { backgroundColor: C.bg } } as any}>
      <SwipeTabs.Screen name="today" />
      <SwipeTabs.Screen name="money" />
      <SwipeTabs.Screen name="ask" />
      <SwipeTabs.Screen name="proof" />
      <SwipeTabs.Screen name="people" />
    </SwipeTabs>
  );
}
