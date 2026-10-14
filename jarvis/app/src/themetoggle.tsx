// The sun/moon switch (plan 2.4a): light ⇄ Bat Mode. Saved on this device and to the account, so a new device starts the same way.
import { Platform, Pressable, Text } from "react-native";
import { api } from "./api";
import * as Haptics from "./haptics";
import { C, setTheme, themeName } from "./theme";

export function flipTheme() {
  const next = themeName() === "bat" ? "light" : "bat";
  Haptics.tap();
  setTheme(next);
  api("/v3/me/setup", { theme: next }).catch(() => {});
  // the website starts again in the new colours (the phone app redraws in place)
  if (Platform.OS === "web" && typeof window !== "undefined") setTimeout(() => window.location.reload(), 120);
}

export function ThemeToggle() {
  const bat = themeName() === "bat";
  return (
    <Pressable onPress={flipTheme} hitSlop={12} accessibilityRole="switch" accessibilityState={{ checked: bat }}
      accessibilityLabel={bat ? "Bat Mode on. Switch to light" : "Light mode. Switch to Bat Mode"}
      style={{ width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center", backgroundColor: C.card2, borderWidth: 1, borderColor: C.line }}>
      <Text style={{ fontSize: 16, color: bat ? C.accent : C.text }}>{bat ? "☾" : "☀︎"}</Text>
    </Pressable>
  );
}
