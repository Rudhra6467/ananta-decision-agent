// A short list of choices in a sheet from the bottom, one ticked (14 Nov 2026, Madhav's YouTube screenshots: the "Accounts ⌄" switch and
// the "Recents ⌄" chip both open this: a grab handle, the rows, a tick beside the one in use; a tap picks and closes, a tap outside closes).
import { Modal, Pressable, Text, View } from "react-native";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import Svg, { Path } from "react-native-svg";
import { C, useThemeVersion } from "./theme";

export type Choice = { id: string; label: string; sub?: string; dot?: string };

const Tick = ({ color }: { color: string }) => (
  <Svg width={24} height={24} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2.25} strokeLinecap="round" strokeLinejoin="round"><Path d="M5 12.5l4.5 4.5L19 7.5" /></Svg>
);
export const ChevDown = ({ color, size = 18 }: { color: string; size?: number }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none" stroke={color} strokeWidth={2} strokeLinecap="round" strokeLinejoin="round"><Path d="M6 9l6 6 6-6" /></Svg>
);

export function ChoiceSheet({ open, title, choices, on, pick, close }: { open: boolean; title?: string; choices: Choice[]; on?: string | null; pick: (id: string) => void; close: () => void }) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  return (
    <Modal visible={open} transparent animationType="slide" onRequestClose={close} statusBarTranslucent>
      <Pressable onPress={close} accessibilityLabel="Close" style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)" }} />
      <View accessibilityViewIsModal style={{ position: "absolute", left: 8, right: 8, bottom: Math.max(ins.bottom, 8), maxWidth: 560, alignSelf: "center",
        backgroundColor: C.sheet, borderRadius: 24, borderWidth: 1, borderColor: C.line, paddingTop: 10, paddingBottom: 10, overflow: "hidden" }}>
        <View style={{ alignSelf: "center", width: 40, height: 5, borderRadius: 3, backgroundColor: C.line, marginBottom: 6 }} />
        {title ? <Text style={{ color: C.dim, fontSize: 13, fontWeight: "600", paddingHorizontal: 20, paddingVertical: 8 }}>{title}</Text> : null}
        {choices.map((c) => {
          const sel = c.id === on;
          return (
            <Pressable key={c.id} onPress={() => { close(); if (!sel) pick(c.id); }} accessibilityRole="button" accessibilityState={{ selected: sel }}
              style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 14, minHeight: 60, paddingHorizontal: 20, backgroundColor: pressed ? C.card2 : "transparent" })}>
              <View style={{ width: 24, alignItems: "center" }}>{sel ? <Tick color={C.text} /> : null}</View>
              {c.dot ? <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: c.dot }} /> : null}
              <View style={{ flex: 1 }}>
                <Text style={{ color: C.text, fontSize: 18, fontWeight: "600" }}>{c.label}</Text>
                {c.sub ? <Text style={{ color: C.dim, fontSize: 13, marginTop: 2 }}>{c.sub}</Text> : null}
              </View>
            </Pressable>
          );
        })}
      </View>
    </Modal>
  );
}
