// One place on the bar (Home, Markets, Activity, More) and one page under it: the same frame for both markets. The parts come from the
// server (/v3/place/<name>), "Needs you" and the bell from the one open list (/v3/place/needs).
import { useRef } from "react";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { router, useScrollToTop } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "./theme";
import { Bell, Icon, MarketChip, Parts, Pinned, useNeeds, usePlace } from "./place";

function Problem({ err, words }: { err?: string | null; words?: string }) {
  return (
    <View style={{ backgroundColor: err ? C.badSoft : C.card, borderRadius: 16, padding: 16, borderWidth: err ? 0 : 1, borderColor: C.line }}>
      <Text style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>{err || words}</Text>
    </View>
  );
}

export function PlaceScreen({ name, title }: { name: string; title: string }) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  const { data, err, loading, reload } = usePlace(name);
  const needs = useNeeds();
  const ref = useRef<ScrollView>(null);
  useScrollToTop(ref);
  const count = needs.data?.count ?? 0;
  return (
    <ScrollView ref={ref} style={{ flex: 1, backgroundColor: C.bg }}
      contentContainerStyle={{ paddingTop: ins.top + 12, paddingHorizontal: 16, paddingBottom: 132, gap: 16, width: "100%", maxWidth: 720, alignSelf: "center" }}
      refreshControl={<RefreshControl refreshing={!!loading && !!data} onRefresh={() => { reload(); needs.reload(); }} tintColor={C.dim} />}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", minHeight: 44 }}>
        {name === "home" ? <MarketChip /> : <Text accessibilityRole="header" style={{ color: C.text, fontSize: 24, lineHeight: 30, fontWeight: "700", letterSpacing: -0.2 }}>{title}</Text>}
        <Bell count={count} />
      </View>
      {err && !data ? <Problem err={err} /> : null}
      {data && data.ready === false ? <Problem words={data.words} /> : null}
      {data && data.ready !== false ? <Parts data={data} needs={needs.data} /> : null}
      {!data && !err ? <Text style={{ color: C.dim, fontSize: 15 }}>Loading…</Text> : null}
    </ScrollView>
  );
}

export function PageScreen({ page, place, onClose }: { page?: any; place?: string; onClose?: () => void }) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  const got = usePlace(place ?? null);
  const needs = useNeeds();
  const data = page ?? got.data;
  const close = onClose ?? (() => (router.canGoBack() ? router.back() : router.replace("/new/home" as any)));
  const isClose = data?.bar === "close";
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <ScrollView style={{ flex: 1 }} contentContainerStyle={{ paddingTop: ins.top + 12, paddingHorizontal: 16, paddingBottom: 24, gap: 16, width: "100%", maxWidth: 720, alignSelf: "center" }}
        refreshControl={place ? <RefreshControl refreshing={!!got.loading && !!got.data} onRefresh={got.reload} tintColor={C.dim} /> : undefined}>
        <View style={{ flexDirection: "row", alignItems: "center", minHeight: 44 }}>
          <Pressable onPress={close} accessibilityRole="button" accessibilityLabel={isClose ? "Close" : "Back"} style={{ width: 44, height: 44, justifyContent: "center" }}>
            <Icon name={isClose ? "close" : "back"} size={24} color={C.text} />
          </Pressable>
          {!isClose ? <Text style={{ flex: 1, textAlign: "center", color: C.text, fontSize: 15, fontWeight: "600" }} numberOfLines={1}>{data?.title || ""}</Text> : <View style={{ flex: 1 }} />}
          <View style={{ width: 44 }} />
        </View>
        {got.err && !data ? <Problem err={got.err} /> : null}
        {data && data.ready === false ? <Problem words={data.words} /> : null}
        {data && data.ready !== false ? <Parts data={data} needs={needs.data} /> : null}
        {!data && !got.err ? <Text style={{ color: C.dim, fontSize: 15 }}>Loading…</Text> : null}
      </ScrollView>
      <View style={{ paddingBottom: Math.max(ins.bottom, 8), width: "100%", maxWidth: 720, alignSelf: "center" }}><Pinned p={data?.pinned} /></View>
    </View>
  );
}
