// 28 Oct (Madhav): "it asks for my approval in evidence layer, but never notifies me when I am using the app". A thin bar under the title on
// every tab while anything waits for his yes (India research drafts, a flag waiting for a pick, a crypto decision), from /v3/waiting
// (jarvis/service/waiting.py). Tap: Ananta lists them and he can say "approve all drafts". "Later" hides the bar until the list changes.
import { useState } from "react";
import { Platform, Pressable, Text, View } from "react-native";
import { goTab } from "./context";
import { C } from "./theme";
import { useData } from "./useData";
import { useMe } from "./visitor";
import { setMarket, useMarket } from "./market";

type W = { items: { id: string; kind: string; title: string; market?: string; route?: string }[]; count: number; key: string; line: string };

const KEY = "ananta.waiting.later";
const readLater = (): string => { try { return Platform.OS === "web" ? window.localStorage.getItem(KEY) ?? "" : mem; } catch { return mem; } };
let mem = "";
const writeLater = (k: string) => { mem = k; try { if (Platform.OS === "web") window.localStorage.setItem(KEY, k); } catch { /* private window */ } };

export function useWaiting(): W | null {
  const me = useMe();
  const { data } = useData<W>(me && !me.guest ? "/v3/waiting" : null, 120000);
  return data && Array.isArray(data.items) ? data : null;
}

export function WaitingBar() {
  const w = useWaiting();
  const market = useMarket() ?? "crypto";
  const [later, setLater] = useState(readLater());
  if (!w || !w.count || !w.line || later === w.key) return null;
  const open = async () => {
    const onlyFlags = w.items.every((x) => x.kind.startsWith("flag"));
    if (onlyFlags) { goTab("/flags"); return; }
    const india = w.items.some((x) => x.market === "india");
    if (india && market !== "india") { try { await setMarket("india"); } catch { /* the chip still switches */ } }
    goTab({ pathname: "/(tabs)/ask", params: { q: "What's waiting for my yes?", t: String(Date.now()) } });
  };
  return (
    <View style={{ flexDirection: "row", alignItems: "center", backgroundColor: C.warnSoft, borderBottomWidth: 1, borderBottomColor: C.line, paddingLeft: 14, paddingRight: 6 }}>
      <Pressable onPress={open} accessibilityRole="button" accessibilityLabel={`${w.line} Tap to review`} style={{ flex: 1, paddingVertical: 7 }}>
        <Text style={{ color: C.text, fontSize: 12, fontWeight: "700" }} numberOfLines={2}>
          <Text style={{ color: C.warn }}>● </Text>{w.line} <Text style={{ color: C.accent }}>Review ›</Text>
        </Text>
      </Pressable>
      <Pressable onPress={() => { writeLater(w.key); setLater(w.key); }} hitSlop={8} accessibilityRole="button" accessibilityLabel="Hide until something new waits"
        style={{ paddingHorizontal: 10, paddingVertical: 7 }}>
        <Text style={{ color: C.dim, fontSize: 12, fontWeight: "600" }}>Later</Text>
      </Pressable>
    </View>
  );
}
