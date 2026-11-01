// The frame every new-look surface sits in: safe-area top, the title left, the avatar (More) right, pull to refresh, the 16px gutter.
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "../src/theme";
import { Body, Title } from "./newui";

export function NScreen({ title, children, loading, onRefresh, err, scrollRef }: { title: string; children: React.ReactNode; loading?: boolean; onRefresh?: () => void; err?: string | null; scrollRef?: React.RefObject<ScrollView | null> }) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  return (
    <ScrollView ref={scrollRef as any} style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ paddingTop: ins.top + 12, paddingHorizontal: 16, paddingBottom: 120, gap: 12 }}
      refreshControl={onRefresh ? <RefreshControl refreshing={!!loading} onRefresh={onRefresh} tintColor={C.dim} /> : undefined}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", marginBottom: 8 }}>
        <Title>{title}</Title>
        <Pressable onPress={() => router.push("/more" as any)} accessibilityRole="button" accessibilityLabel="More"
          style={{ width: 36, height: 36, borderRadius: 999, backgroundColor: C.card2, alignItems: "center", justifyContent: "center" }}>
          <Text style={{ color: C.text, fontSize: 15, fontWeight: "700" }}>M</Text>
        </Pressable>
      </View>
      {err ? <View style={{ backgroundColor: C.badSoft, borderRadius: 16, padding: 14 }}><Body>{err}</Body></View> : null}
      {children}
    </ScrollView>
  );
}

// 1 Nov (Madhav): a link into a surface opens it AT the section asked for, with the question sent when it is Ask
export const askHref = (q: string) => ({ pathname: "/new/ask", params: { q, t: String(Date.now()) } }) as any;
