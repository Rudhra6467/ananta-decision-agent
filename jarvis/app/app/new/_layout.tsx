// The new look's shell (31 Oct 2026, gate 1): five surfaces on a bottom bar - Today, Money, (Ask as the orb), Proof, People - each
// answering one question. The classic tabs (app/(tabs)) stay untouched; More › "New look" switches between them (src/look.ts).
import { Tabs } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "../../src/theme";
import { CheckIcon2, DollarIcon, G, Orb, PeopleIcon, RupeeIcon, SunIcon, TY } from "../../src/newui";
import { useMarket } from "../../src/market";
import { ScreenError } from "../../src/safe";
import { useTyping } from "../../src/once";

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
              <Orb onPress={() => navigation.navigate("ask")} />
            </View>
          );
        }
        const on = active === t.name;
        const col = on ? G.gold() : C.dim;
        const Icon = t.name === "money" && mk === "crypto" ? DollarIcon : t.Icon;   // 1 Nov: crypto's money is in dollars
        return (
          <Pressable key={t.name} accessibilityRole="tab" accessibilityLabel={t.label} accessibilityState={{ selected: on }}
            onPress={() => navigation.navigate(t.name)} style={{ width: 64, alignItems: "center", gap: 4, minHeight: 44 }}>
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
    <Tabs screenOptions={{ headerShown: false, sceneStyle: { backgroundColor: C.bg } as any }} tabBar={(p) => <Bar {...p} />}>
      <Tabs.Screen name="today" />
      <Tabs.Screen name="money" />
      <Tabs.Screen name="ask" />
      <Tabs.Screen name="proof" />
      <Tabs.Screen name="people" />
    </Tabs>
  );
}
