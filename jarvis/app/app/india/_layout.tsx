// The India pack's frame: its own header (saffron rule, its own name), "Switch market" always one tap away. The screens under
// /india read only the India service (api.livetrading247.com/india) with the same sign-in; nothing here touches a crypto screen or table.
import { Stack, router } from "expo-router";
import { Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, TYPE } from "../../src/theme";
import { clearMarket } from "../../src/market";

export const INDIA = { saffron: "#E3761F", green: "#1D7A3A", red: "#B3261E" };

export function IndiaHeader({ title }: { title: string }) {
  const top = useSafeAreaInsets().top;
  return (
    <View style={{ paddingTop: top + 8, paddingBottom: 10, paddingHorizontal: 16, backgroundColor: C.card, borderBottomWidth: 3, borderBottomColor: INDIA.saffron,
      flexDirection: "row", alignItems: "center", gap: 10 }}>
      <View style={{ width: 22, height: 22, borderRadius: 6, backgroundColor: INDIA.saffron, borderWidth: 1, borderColor: C.line, overflow: "hidden" }}>
        <View style={{ position: "absolute", left: 0, right: 0, top: 7, height: 7, backgroundColor: "#fff" }} />
        <View style={{ position: "absolute", left: 0, right: 0, bottom: 0, height: 7, backgroundColor: INDIA.green }} />
      </View>
      <Text style={{ color: C.text, fontSize: TYPE.card, fontWeight: "800", flex: 1 }}>Ananta · {title}</Text>
      <Pressable onPress={async () => { await clearMarket(); router.replace("/market"); }} accessibilityRole="button" accessibilityLabel="Switch market"
        style={{ paddingVertical: 6, paddingHorizontal: 10, borderRadius: 999, backgroundColor: C.card2, borderWidth: 1, borderColor: C.line }}>
        <Text style={{ color: C.text, fontSize: TYPE.meta, fontWeight: "700" }}>Switch market</Text>
      </Pressable>
    </View>
  );
}

export default function IndiaLayout() {
  return <Stack screenOptions={{ headerShown: false, contentStyle: { backgroundColor: C.bg } }} />;
}
