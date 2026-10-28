// 28 Oct (flag 49, Madhav): "when you're answering, the screen went blank and just went out of control". Nothing in the app caught a
// drawing error, so one bad message or screen blanked everything. Now a message that fails to draw shows as plain text, and a screen
// that fails shows a "Reload conversation" button instead of a blank page.
import { Component, type ReactNode } from "react";
import { Platform, Pressable, Text, View } from "react-native";
import { C } from "./theme";

const reload = () => {
  if (Platform.OS === "web" && typeof window !== "undefined") window.location.reload();
};

export class MsgGuard extends Component<{ text?: string; children: ReactNode }, { bad: boolean }> {
  state = { bad: false };
  static getDerivedStateFromError() { return { bad: true }; }
  componentDidCatch(e: unknown) { console.warn("[Ananta] a message failed to draw", e); }
  render() {
    if (!this.state.bad) return this.props.children;
    return (
      <View style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 16, padding: 14, gap: 6, maxWidth: "96%" }}>
        <Text selectable style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>{String(this.props.text ?? "")}</Text>
        <Text style={{ color: C.faint, fontSize: 11 }}>Shown as plain text: this message could not be drawn.</Text>
      </View>
    );
  }
}

export function ScreenError({ error, retry }: { error: Error; retry: () => Promise<void> }) {
  return (
    <View style={{ flex: 1, backgroundColor: C.bg, alignItems: "center", justifyContent: "center", padding: 24, gap: 12 }}>
      <Text style={{ color: C.text, fontSize: 18, fontWeight: "700", textAlign: "center" }}>The screen hit a problem</Text>
      <Text style={{ color: C.dim, fontSize: 13, textAlign: "center" }}>Your conversation is saved. Reload to bring it back.</Text>
      <Pressable onPress={() => { retry().catch(() => reload()); }} accessibilityRole="button" accessibilityLabel="Reload conversation"
        style={({ pressed }) => ({ backgroundColor: C.accent, borderRadius: 999, paddingHorizontal: 18, paddingVertical: 10, opacity: pressed ? 0.8 : 1 })}>
        <Text style={{ color: C.onInk, fontWeight: "800" }}>Reload conversation</Text>
      </Pressable>
      <Pressable onPress={reload} accessibilityRole="button"><Text style={{ color: C.accent, fontSize: 13 }}>Reload the whole app</Text></Pressable>
      <Text style={{ color: C.faint, fontSize: 11, textAlign: "center" }} numberOfLines={2}>{String(error?.message ?? "").slice(0, 160)}</Text>
    </View>
  );
}
