import { Tabs } from "expo-router";
import { C } from "../../src/theme";
import { ChatIcon, FlaskIcon, GaugeIcon, HomeIcon, PieIcon } from "../../src/icons";

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{
      headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false, headerTintColor: C.text,
      headerTitleStyle: { fontWeight: "700", fontSize: 17 },
      tabBarStyle: { backgroundColor: C.card, borderTopColor: C.line },
      tabBarActiveTintColor: C.accent, tabBarInactiveTintColor: C.faint,
      tabBarLabelStyle: { fontSize: 11, fontWeight: "600" },
    }}>
      <Tabs.Screen name="today" options={{ title: "Home", tabBarIcon: ({ color }) => <HomeIcon color={String(color)} /> }} />
      <Tabs.Screen name="portfolio" options={{ title: "Portfolio", tabBarIcon: ({ color }) => <PieIcon color={String(color)} /> }} />
      <Tabs.Screen name="ask" options={{ title: "Ask Ananta", tabBarLabel: "Ask", tabBarIcon: ({ color }) => <ChatIcon color={String(color)} /> }} />
      <Tabs.Screen name="evidence" options={{ title: "Evidence", tabBarIcon: ({ color }) => <FlaskIcon color={String(color)} /> }} />
      <Tabs.Screen name="cockpit" options={{ title: "Cockpit", tabBarIcon: ({ color }) => <GaugeIcon color={String(color)} /> }} />
    </Tabs>
  );
}
