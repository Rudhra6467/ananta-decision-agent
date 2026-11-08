// The frame every new-look surface sits in: safe-area top, the title left, the avatar (More) right, pull to refresh, the 16px gutter.
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "../src/theme";
import { AnantaMark } from "./logo";
import { Body, G, Title } from "./newui";
import { useMarket } from "./market";
import { useData } from "./useData";

export function NScreen({ title, children, loading, onRefresh, err, scrollRef }: { title: string; children: React.ReactNode; loading?: boolean; onRefresh?: () => void; err?: string | null; scrollRef?: React.RefObject<ScrollView | null> }) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  const mk = useMarket();
  return (
    <ScrollView ref={scrollRef as any} style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ paddingTop: ins.top + 12, paddingHorizontal: 16, paddingBottom: 120, gap: 12 }}
      refreshControl={onRefresh ? <RefreshControl refreshing={!!loading} onRefresh={onRefresh} tintColor={C.dim} /> : undefined}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
          <Title>{title}</Title>
          {/* 1 Nov (Madhav: "where is the market switch button?"): the same switch as the classic header */}
          <Pressable onPress={() => router.push("/market" as any)} accessibilityRole="button" accessibilityLabel="Switch market"
            style={{ flexDirection: "row", alignItems: "center", gap: 6, backgroundColor: C.card2, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5, minHeight: 30 }}>
            <View style={{ width: 6, height: 6, borderRadius: 999, backgroundColor: mk === "crypto" ? G.twin() : C.india }} />
            <Text style={{ color: C.dim, fontSize: 11, fontWeight: "700", letterSpacing: 0.3 }}>{mk === "crypto" ? "CRYPTO" : "INDIAN MARKET"} ⇄</Text>
          </Pressable>
        </View>
        {/* 7 Nov 2026 (Madhav): Ananta's mark here instead of the letter M; it still opens More (settings, the market, sign-out) */}
        <Pressable onPress={() => router.push("/more" as any)} accessibilityRole="button" accessibilityLabel="More"
          style={{ width: 40, height: 40, borderRadius: 999, alignItems: "center", justifyContent: "center" }}>
          <AnantaMark color={G.gold()} grey={C.faint} ink={C.bg} size={40} />
        </Pressable>
      </View>
      {err ? <View style={{ backgroundColor: C.badSoft, borderRadius: 16, padding: 14 }}><Body>{err}</Body></View> : null}
      {children}
    </ScrollView>
  );
}

// 1 Nov: both markets read /v3/surface/<name> (crypto service, or India through /india); the market rides in the address so a
// switch of market reloads every mounted tab instead of showing the other market's numbers
export function useSurface(name: "today" | "money" | "proof" | "people", refreshMs: number) {
  const mk = useMarket();
  return useData<any>(mk ? `/v3/surface/${name}?m=${mk}` : null, refreshMs);
}

// 1 Nov (Madhav): a link into a surface opens it AT the section asked for, with the question sent when it is Ask
export const askHref = (q: string) => ({ pathname: "/new/ask", params: { q, t: String(Date.now()) } }) as any;
