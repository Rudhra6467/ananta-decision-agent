// The four main tabs (plan 2.1, D6; five until Oct 15), each answering one question (Oct 14, one grammar): Home "how is my account,
// what did it trade, and does anything need me?" (the Books tab folded into it on Oct 15, Madhav) · Ask Ananta "talk" ·
// Markets (was Watchlists) "what is the market doing?", with Ananta market (the lab's books) as its second page ·
// More (was Cockpit) "settings, evidence, is everything running?". Swipeable like YouTube: drag left / right and the next page slides in.
// The menu button at the top left of every tab opens the side drawer (src/drawer.tsx): every tab and what it holds, like Gmail.
// Tapping the tab you are already on goes back to the top (Ask Ananta: to the latest message), plan 2.2.
// Tab bar stays at the bottom; the page header (title, the bell and theme switch on More) is drawn here because swipe tabs have no header of their own.
// The route names (watchlists, cockpit) stay as they were so every deep link and spoken command still lands.
import { useState } from "react";
import { Alert, Platform, Pressable, Text, View } from "react-native";
import { api } from "../../src/api";
import { router, usePathname } from "expo-router";
import SwipeTabs from "expo-router/js-top-tabs";        // Expo Router's swipeable tabs (react-native-tab-view + pager-view underneath)
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C } from "../../src/theme";
import { scroll } from "../../src/spotlight";
import { ThemeToggle } from "../../src/themetoggle";
import { AlertsBell } from "../../src/alerts";
import { useData } from "../../src/useData";
import { HomeIcon, MenuIcon, SlidersIcon, TrendIcon, VoiceIcon } from "../../src/icons";
import { AppDrawer } from "../../src/drawer";
import { clearMe, useMe } from "../../src/visitor";
import { MARKET_NAME, clearMarket, useMarket } from "../../src/market";

const TITLES: Record<string, string> = { today: "Home", ask: "Ask Ananta", watchlists: "Markets", cockpit: "More", portfolio: "Home" };

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

// Which Ananta is loaded (23 Oct): a small chip beside the title when it is the Indian market; tap it to switch. Crypto shows nothing,
// so the crypto app looks exactly as before.
function MarketChip() {
  const m = useMarket();
  const me = useMe();
  if (!m || me?.guest) return null;                                   // both markets show which Ananta is loaded; a tap switches (Madhav, 23 Oct)
  return (
    <Pressable onPress={async () => { await clearMarket(); router.replace("/market"); }} accessibilityRole="button" accessibilityLabel={`${MARKET_NAME[m]} loaded; tap to switch market`}
      style={{ marginLeft: 8, paddingVertical: 3, paddingHorizontal: 8, borderRadius: 999, backgroundColor: C.card2, borderWidth: 1, borderColor: C.line }}>
      <Text style={{ color: C.dim, fontSize: 11, fontWeight: "700" }}>{MARKET_NAME[m].toUpperCase()} ⇄</Text>
    </Pressable>
  );
}

function Header() {
  const top = useSafeAreaInsets().top;
  const path = usePathname();
  const [menu, setMenu] = useState(false);
  const key = (path.split("/").filter(Boolean).pop() || "today");
  const title = TITLES[key] ?? (path === "/" ? "Home" : "");
  return (
    <View style={{ paddingTop: top, backgroundColor: C.bg }}>
      <View style={{ height: 44, flexDirection: "row", alignItems: "center", justifyContent: "center" }}>
        <Pressable onPress={() => setMenu(true)} hitSlop={10} accessibilityRole="button" accessibilityLabel="Menu"
          style={{ position: "absolute", left: 12, width: 36, height: 36, borderRadius: 10, alignItems: "center", justifyContent: "center" }}>
          <MenuIcon color={C.text} />
        </Pressable>
        <AppDrawer open={menu} onClose={() => setMenu(false)} />
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 17 }}>{title}</Text>
        <MarketChip />
        {title === "More" ? (
          <View style={{ position: "absolute", right: 16, flexDirection: "row", gap: 10 }}><AlertsBell /><ThemeToggle /></View>
        ) : null}
      </View>
      <PracticeStrip />
    </View>
  );
}

export default function TabsLayout() {
  const bottom = useSafeAreaInsets().bottom;
  const { data: meNow } = useData("/v3/me", 60000);               // plan 1.7: a badge on Home while something needs you
  const { data: nd } = useData("/v3/needs", 300000);              // Oct 14: plus the decisions waiting on the Needs-you card
  const needs = Number(meNow?.needs_you ?? 0) + (nd?.items?.length ?? 0);
  const badge = () => needs ? (
    <View style={{ minWidth: 16, height: 16, borderRadius: 8, backgroundColor: C.bad, alignItems: "center", justifyContent: "center", paddingHorizontal: 4, marginTop: 4, marginRight: 14 }}>
      <Text style={{ color: C.onInk, fontSize: 10, fontWeight: "800" }}>{needs}</Text>
    </View>
  ) : null;
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
          tabBarActiveTintColor: C.accent, tabBarInactiveTintColor: C.dim,
          tabBarStyle: { backgroundColor: C.card, borderTopColor: C.line, borderTopWidth: 1, paddingBottom: bottom, elevation: 0, shadowOpacity: 0 },
          tabBarLabelStyle: { fontSize: 11, fontWeight: "600", textTransform: "none", margin: 0, letterSpacing: 0.2 },
          tabBarItemStyle: { paddingHorizontal: 0, paddingVertical: 6, minHeight: 52 },
          tabBarIndicatorStyle: { backgroundColor: C.accent, top: 0, height: 2 },
          tabBarPressColor: "transparent",
          sceneStyle: { backgroundColor: C.bg },
        }}
        screenListeners={({ navigation, route }: any) => ({
          tabPress: () => { if (navigation.isFocused()) scroll(route.name === "ask" ? "bottom" : "top"); },
        })}>
        <SwipeTabs.Screen name="today" options={{ title: "Home", tabBarIcon: icon(HomeIcon), tabBarBadge: badge } as any} />
        <SwipeTabs.Screen name="ask" options={{ title: "Ask Ananta", tabBarIcon: icon(VoiceIcon) }} />
        <SwipeTabs.Screen name="watchlists" options={{ title: "Markets", tabBarIcon: icon(TrendIcon) }} />
        <SwipeTabs.Screen name="cockpit" options={{ title: "More", tabBarIcon: icon(SlidersIcon) }} />
      </SwipeTabs>
    </View>
  );
}
