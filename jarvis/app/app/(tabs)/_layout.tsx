import { Tabs } from "expo-router";
import { C } from "../../src/theme";

export default function TabsLayout() {
  return (
    <Tabs screenOptions={{
      headerStyle: { backgroundColor: C.bg }, headerTintColor: C.text,
      tabBarStyle: { backgroundColor: C.card, borderTopColor: C.line },
      tabBarActiveTintColor: C.accent, tabBarInactiveTintColor: C.dim,
      tabBarIconStyle: { display: "none" }, tabBarLabelStyle: { fontSize: 14, fontWeight: "600", paddingBottom: 12 },
    }}>
      <Tabs.Screen name="today" options={{ title: "Today" }} />
      <Tabs.Screen name="portfolio" options={{ title: "Portfolio" }} />
      <Tabs.Screen name="evidence" options={{ title: "Evidence" }} />
      <Tabs.Screen name="safety" options={{ title: "Safety" }} />
    </Tabs>
  );
}
