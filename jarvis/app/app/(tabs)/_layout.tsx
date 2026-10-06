// The four main tabs (Home, Markets, Books, Ask Jarvis; the research views moved to the Lab page, 2026-10-04), swipeable like YouTube: drag left / right and you see the next page slide in.
// Tab bar stays at the bottom; the page header (title, Cockpit button) is drawn here because swipe tabs have no header of their own.
import { useState } from "react";
import { Alert, Platform, Pressable, Text, View } from "react-native";
import { api } from "../../src/api";
import { router, usePathname } from "expo-router";
import SwipeTabs from "expo-router/js-top-tabs";        // Expo Router's swipeable tabs (react-native-tab-view + pager-view underneath)
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C } from "../../src/theme";
import { BooksIcon, ChartIcon, ChatIcon, GaugeIcon, HomeIcon } from "../../src/icons";
import { OnboardTour, clearMe, useMe } from "../../src/visitor";

const TITLES: Record<string, string> = { today: "Home", markets: "Markets", portfolio: "Books", ask: "Ask Jarvis" };

// Guests (a friend testing the app) get a practice book of their own. A thin strip under the title says so on every tab;
// tap it for the full note. Madhav never sees it.
function PracticeStrip() {
  const me = useMe();
  const [open, setOpen] = useState(false);
  if (!me?.guest) return null;
  const startOver = async () => {
    const ok = Platform.OS === "web" ? window.confirm("Start over? Your practice trades and history are cleared and you get $1,000 again.")
      : await new Promise<boolean>((res) => Alert.alert("Start over?", "Your practice trades and history are cleared and you get $1,000 again.",
        [{ text: "Cancel", onPress: () => res(false) }, { text: "Start over", style: "destructive", onPress: () => res(true) }]));
    if (!ok) return;
    await api("/v3/practice/reset", {});
    clearMe();
    router.replace("/welcome");                          // a fresh account: name, coins, tour, capital again
  };
  return (
    <Pressable onPress={() => setOpen(!open)} style={{ backgroundColor: C.card2, borderBottomWidth: 1, borderBottomColor: C.line, paddingHorizontal: 16, paddingVertical: 6 }}>
      <Text style={{ color: C.warn, fontSize: 12, fontWeight: "700", textAlign: "center" }}>
        PRACTICE ACCOUNT · paper money{open ? "" : " · tap for details"}
      </Text>
      {open ? <Text style={{ color: C.dim, fontSize: 12, textAlign: "center", marginTop: 2 }}>{me.practice_note}</Text> : null}
      {open ? (
        <Text onPress={startOver} style={{ color: C.accent, fontSize: 12, fontWeight: "700", textAlign: "center", marginTop: 6 }}>
          Start over: a fresh account and an empty history
        </Text>
      ) : null}
    </Pressable>
  );
}

function Header() {
  const top = useSafeAreaInsets().top;
  const path = usePathname();
  const key = (path.split("/").filter(Boolean).pop() || "today");
  const title = TITLES[key] ?? (path === "/" ? "Home" : "");
  const me = useMe();
  return (
    <View style={{ paddingTop: top, backgroundColor: C.bg }}>
      <View style={{ height: 44, flexDirection: "row", alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 17 }}>{title}</Text>
        {title === "Home" && me && !me.guest ? (
          <Pressable onPress={() => router.push("/cockpit")} hitSlop={12} style={{ position: "absolute", right: 16 }}>
            <GaugeIcon color={C.text} size={24} />
          </Pressable>
        ) : null}
      </View>
      <PracticeStrip />
    </View>
  );
}

export default function TabsLayout() {
  const bottom = useSafeAreaInsets().bottom;
  const icon = (I: any) => ({ color }: { color: string }) => <I color={String(color)} />;
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <Header />
      <SwipeTabs
        tabBarPosition="bottom"
        initialRouteName="today"
        screenOptions={{
          lazy: true,
          swipeEnabled: true,
          animationEnabled: true,
          tabBarShowIcon: true,
          tabBarActiveTintColor: C.accent, tabBarInactiveTintColor: C.faint,
          tabBarStyle: { backgroundColor: C.card, borderTopColor: C.line, borderTopWidth: 1, paddingBottom: bottom, elevation: 0, shadowOpacity: 0 },
          tabBarLabelStyle: { fontSize: 11, fontWeight: "600", textTransform: "none", margin: 0 },
          tabBarItemStyle: { paddingHorizontal: 0, paddingVertical: 6, minHeight: 52 },
          tabBarIndicatorStyle: { backgroundColor: C.accent, top: 0, height: 2 },
          tabBarPressColor: "transparent",
          sceneStyle: { backgroundColor: C.bg },
        }}>
        <SwipeTabs.Screen name="today" options={{ title: "Home", tabBarIcon: icon(HomeIcon) }} />
        <SwipeTabs.Screen name="markets" options={{ title: "Markets", tabBarIcon: icon(ChartIcon) }} />
        <SwipeTabs.Screen name="portfolio" options={{ title: "Books", tabBarIcon: icon(BooksIcon) }} />
        <SwipeTabs.Screen name="ask" options={{ title: "Ask Jarvis", tabBarIcon: icon(ChatIcon) }} />
      </SwipeTabs>
      <OnboardTour />
    </View>
  );
}
