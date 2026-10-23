// The side drawer (Madhav, Oct 15, "like Gmail"): the menu button in every tab's header opens it. It lists the four tabs with
// what each holds, then the pages that live above the tabs. A tap goes there and closes the drawer; nothing else changes.
import { Modal, Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { goTab } from "./context";
import { focusSpot } from "./spotlight";
import { C } from "./theme";
import { HomeIcon, SlidersIcon, TrendIcon, VoiceIcon } from "./icons";
import { AnantaMark } from "./logo";
import { useMe } from "./visitor";

type Item = { label: string; go: () => void };
type Group = { title: string; icon: (p: { color: string }) => React.ReactNode; path: string; items: Item[] };

const tab = (pathname: string, params?: Record<string, string>) => () => goTab(params ? ({ pathname, params: { ...params, t: String(Date.now()) } } as any) : (pathname as any));
const spot = (pathname: string, id: string) => () => { goTab({ pathname, params: { t: String(Date.now()) } } as any); setTimeout(() => { focusSpot(id, 2500); }, 500); };
const page = (p: string) => () => router.push(p as any);

function groups(guest: boolean): Group[] {
  const home: Group = {
    title: "Home", icon: HomeIcon, path: "/(tabs)/today",
    items: guest
      ? [{ label: "My coins and money", go: tab("/(tabs)/today") }]
      : [{ label: "The account", go: spot("/(tabs)/today", "home.value") }, { label: "Trades", go: spot("/(tabs)/today", "books.trades") },
        { label: "Activity", go: spot("/(tabs)/today", "home.activity") }, { label: "Ananta: needs you, the note, the lab, findings", go: tab("/(tabs)/today", { ananta: "1" }) }],
  };
  const ask: Group = {
    title: "Ask Ananta", icon: VoiceIcon, path: "/(tabs)/ask",
    items: [{ label: "Chat", go: tab("/(tabs)/ask", { view: "chat" }) }, { label: "Ananta now", go: tab("/(tabs)/ask", { view: "now" }) },
      { label: "Sessions", go: tab("/(tabs)/ask", { view: "chat", sessions: "1" }) }],
  };
  const markets: Group = {
    title: "Markets", icon: TrendIcon, path: "/(tabs)/watchlists",
    items: guest
      ? [{ label: "The market and my watches", go: tab("/(tabs)/watchlists", { tab: "markets" }) }, { label: "My book", go: tab("/(tabs)/watchlists", { tab: "ananta" }) }]
      : [{ label: "The dial, watches, coins, the whole market", go: tab("/(tabs)/watchlists", { tab: "markets" }) },
        { label: "Ananta market · the lab's books", go: tab("/(tabs)/watchlists", { tab: "ananta", sub: "lab" }) },
        { label: "Ananta market · trend portfolio", go: tab("/(tabs)/watchlists", { tab: "ananta", sub: "portfolio" }) },
        { label: "Ananta market · Explorer", go: tab("/(tabs)/watchlists", { tab: "ananta", sub: "explorer" }) },
        { label: "Ananta market · my trades", go: tab("/(tabs)/watchlists", { tab: "ananta", sub: "mine" }) },
        { label: "Ananta market · my setups", go: tab("/(tabs)/watchlists", { tab: "ananta", sub: "setups" }) }],
  };
  const more: Group = {
    title: "More", icon: SlidersIcon, path: "/(tabs)/cockpit",
    items: guest
      ? [{ label: "Controls and voice", go: tab("/(tabs)/cockpit") }]
      : [{ label: "Controls", go: spot("/(tabs)/cockpit", "cockpit.controls") }, { label: "Evidence", go: spot("/(tabs)/cockpit", "cockpit.evidence") },
        { label: "Additional features", go: page("/more") },
        { label: "Switch market · Indian market", go: () => { import("./market").then(({ clearMarket }) => clearMarket().then(() => router.replace("/market"))); } }],
  };
  return [home, ask, markets, more];
}

const PAGES: (guest: boolean) => Item[] = (guest) => guest ? [] : [
  { label: "Ananta's book", go: page("/jarvis") }, { label: "Evidence and reviews", go: page("/evidence") }, { label: "The repair loop", go: page("/lab") },
  { label: "Missed moves", go: page("/missed") }, { label: "Reconstruction", go: page("/reconstruction") }, { label: "All coins", go: page("/coins") },
  { label: "The mandate", go: page("/mandate") }, { label: "People", go: page("/people") }, { label: "Feedback", go: page("/feedback") },
];

export function AppDrawer({ open, onClose }: { open: boolean; onClose: () => void }) {
  const me = useMe();
  const top = useSafeAreaInsets().top;
  const guest = !!me?.guest;
  const go = (f: () => void) => { onClose(); setTimeout(f, Platform.OS === "web" ? 0 : 80); };
  return (
    <Modal visible={open} transparent animationType="fade" onRequestClose={onClose}>
      <View style={{ flex: 1, flexDirection: "row" }}>
        <View style={{ width: "82%", maxWidth: 360, backgroundColor: C.bg, paddingTop: top + 12, borderRightWidth: 1, borderRightColor: C.line }}>
          <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 16, paddingBottom: 12 }}>
            <AnantaMark color={C.accent} size={40} grey={C.faint} ink={C.bg} />
            <Text style={{ color: C.text, fontWeight: "800", fontSize: 18, flex: 1 }}>Ananta</Text>
            <Pressable onPress={onClose} hitSlop={10} accessibilityLabel="Close the menu"><Text style={{ color: C.dim, fontSize: 18 }}>✕</Text></Pressable>
          </View>
          <ScrollView contentContainerStyle={{ paddingHorizontal: 8, paddingBottom: 40, gap: 4 }}>
            {groups(guest).map((g) => (
              <View key={g.title} style={{ paddingBottom: 6 }}>
                <Pressable onPress={() => go(tab(g.path))} accessibilityRole="button"
                  style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 12, paddingHorizontal: 10, minHeight: 44, borderRadius: 12, opacity: pressed ? 0.6 : 1 })}>
                  <g.icon color={C.accent} />
                  <Text style={{ color: C.text, fontWeight: "700", fontSize: 16 }}>{g.title}</Text>
                </Pressable>
                {g.items.map((it) => (
                  <Pressable key={it.label} onPress={() => go(it.go)} accessibilityRole="button"
                    style={({ pressed }) => ({ paddingLeft: 46, paddingRight: 10, minHeight: 38, justifyContent: "center", borderRadius: 10, backgroundColor: pressed ? C.card2 : "transparent" })}>
                    <Text style={{ color: C.dim, fontSize: 14 }}>{it.label}</Text>
                  </Pressable>
                ))}
              </View>
            ))}
            {PAGES(guest).length ? (
              <View style={{ borderTopWidth: 1, borderTopColor: C.line, paddingTop: 8 }}>
                <Text style={{ color: C.faint, fontSize: 12, fontWeight: "700", paddingHorizontal: 10, paddingBottom: 4, letterSpacing: 0.5 }}>PAGES</Text>
                {PAGES(guest).map((it) => (
                  <Pressable key={it.label} onPress={() => go(it.go)} accessibilityRole="button"
                    style={({ pressed }) => ({ paddingHorizontal: 10, minHeight: 40, justifyContent: "center", borderRadius: 10, backgroundColor: pressed ? C.card2 : "transparent" })}>
                    <Text style={{ color: C.text, fontSize: 15 }}>{it.label}</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
          </ScrollView>
        </View>
        <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.45)" }} accessibilityLabel="Close the menu" />
      </View>
    </Modal>
  );
}
