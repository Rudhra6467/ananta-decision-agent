// Today (the new look, gate 2 "all looks good"): the quiet top - one short headline, two boxes, what waits, everything running - and the
// morning view's cards beneath on scroll. Before the open the cards are the morning view; after the close the first card is what the managed
// book did. Data: /india/v3/today (jarvis/india/surfaces.py).
// 4 Nov (Madhav): the headline is one line ("No change today") with Details; each box holds two numbers, swiped up inside the box (Nifty 50 /
// Bank Nifty; stocks / options); every card is short points, two shown, "Show more" for the rest.
import { useEffect, useRef, useState } from "react";
import { Platform, Pressable, ScrollView, Text, View, type NativeScrollEvent, type NativeSyntheticEvent } from "react-native";
import { router } from "expo-router";
import { useScrollToTop } from "expo-router";
import { NScreen, askHref, useSurface } from "../../src/newscreen";
import { Body, Dot, G, H, Meta, NCard, PillLink, RowLink, TY } from "../../src/newui";
import { C } from "../../src/theme";
import { ScreenError } from "../../src/safe";
import { ChartSheet, chartFor, type ChartKind } from "../../src/newcharts";
import { useMarket } from "../../src/market";

export const ErrorBoundary = ScreenError;

type Page = { label: string; value: string; sub?: string; sub2?: string; tone?: "good" | "bad" | null; tone2?: "good" | "bad" | null; focus?: string };
type Tile = { id: string; pages: Page[] };

export default function Today() {
  const { data: d, err, loading, reload } = useSurface("today", 60000);
  const askIt = (q: string) => router.navigate(askHref(q));
  const openMoney = (focus?: string) => router.navigate({ pathname: "/new/money", params: { focus: focus || "holdings", t: String(Date.now()) } } as any);
  const scrollRef = useRef<ScrollView>(null);
  useScrollToTop(scrollRef);                    // 7 Nov: the Today button, pressed again, goes back to the top
  const mk = useMarket();
  // 7 Nov (Madhav): the index box opens the Nifty 50 / Bank Nifty chart, the portfolio box its performance over time (India; crypto's boxes
  // still open Money)
  const [chart, setChart] = useState<{ kind: ChartKind; which: string; focus?: string } | null>(null);
  const openTile = (p: Page) => { if (mk === "india") setChart({ ...chartFor(p.label), focus: p.focus }); else openMoney(p.focus); };
  // older surfaces (the crypto one) still send two single numbers: each becomes a one-page box
  const tiles: Tile[] = d?.tiles || (d?.numbers || []).map((n: any, i: number) => ({ id: n.label, pages: [{ ...n, focus: n.focus || (i === 1 ? "holdings" : "options") }] }));
  return (
    <NScreen title="Today" loading={loading} onRefresh={reload} err={err} scrollRef={scrollRef}>
      {chart ? <ChartSheet kind={chart.kind} which={chart.which} onClose={() => setChart(null)} onAsk={askIt} onOpenMoney={() => openMoney(chart.focus)} /> : null}
      {d ? (
        <>
          <Meta>{d.now_words}{d.when ? ` · ${d.when}` : ""}</Meta>
          {d.headline ? <Headline short={d.headline} full={d.decision} source={d.decision_source} /> : (
            <>
              <Text style={{ fontSize: 24, lineHeight: 32, fontWeight: "600", letterSpacing: -0.2, color: C.text, marginTop: 4 }}>{d.decision}</Text>
              <Meta faint>{d.decision_source}</Meta>
            </>
          )}
          <View style={{ flexDirection: "row", gap: 12, marginTop: 4 }}>
            {tiles.map((t, i) => <SwipeTile key={t.id} pages={t.pages} hint={i === 0} onOpen={openTile} />)}
          </View>
          <RowLink onPress={() => askIt("What's waiting for my yes?")} left={<><Dot color={d.waiting?.count ? C.warn : C.faint} /><H>{d.waiting?.count ? `${d.waiting.count} thing${d.waiting.count === 1 ? "" : "s"} wait${d.waiting.count === 1 ? "s" : ""} for your yes` : "Nothing waits for your yes"}</H></>} />
          <RowLink onPress={() => askIt("Is everything running?")} left={<><Dot color={d.running?.ok ? C.good : C.bad} /><H>{d.running?.words}</H></>} right={<Meta>{d.running?.checked}</Meta>} />
          {d.evening ? <PointsCard c={{ ...d.evening, accent: true }} /> : null}
          {(d.cards || []).map((c: any) => <PointsCard key={c.kind} c={c} />)}
          {d.clock ? <Meta faint>{d.clock}</Meta> : null}
          {d.next_view ? <Meta faint>{d.next_view}</Meta> : null}
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 4 }}>
            {(d.suggested || []).map((q: string) => <PillLink key={q} label={q} onPress={() => askIt(q)} />)}
          </View>
        </>
      ) : null}
    </NScreen>
  );
}

// "No change today … load more for details. One line." The full sentence and where it came from open under it.
function Headline({ short, full, source }: { short: string; full?: string; source?: string }) {
  const [open, setOpen] = useState(false);
  return (
    <Pressable onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }}
      accessibilityLabel={`${short}. ${open ? "Hide details" : "Show details"}`} style={{ marginTop: 2 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12, minHeight: 40 }}>
        <Text numberOfLines={1} style={{ flex: 1, fontSize: 22, lineHeight: 30, fontWeight: "600", letterSpacing: -0.3, color: C.text }}>{short}</Text>
        <View style={{ borderRadius: 999, borderWidth: 1, borderColor: C.line, paddingHorizontal: 12, paddingVertical: 5 }}>
          <Text style={[TY.meta, { color: G.gold() }]}>{open ? "Less" : "Details"}</Text>
        </View>
      </View>
      {open ? (
        <View style={{ marginTop: 6, gap: 4 }}>
          {full && full !== short ? <Body>{full}</Body> : null}
          {source ? <Meta faint>{source}</Meta> : null}
        </View>
      ) : null}
    </Pressable>
  );
}

// One box, two numbers: swipe up inside it for the second (paging, so it always rests on one); the dots show which, and tap to switch.
const TILE_H = 128;
// a half-width box on a phone has about 120 px for the number: "23,961" fits at full size, "₹84,598" and "₹1,62,212" step down, never cut
const fit = (v: string) => (v.length <= 6 ? null : v.length === 7 ? { fontSize: 27, lineHeight: 34 } : v.length === 8 ? { fontSize: 24, lineHeight: 32 } : { fontSize: 21, lineHeight: 30 });
let hintShown = false;   // the box nudges up once, so the second number is found; once per app start, and once per browser on the web

function SwipeTile({ pages, hint, onOpen }: { pages: Page[]; hint?: boolean; onOpen: (p: Page) => void }) {
  const [at, setAt] = useState(0);
  const ref = useRef<ScrollView>(null);
  const many = pages.length > 1;
  const go = (i: number) => ref.current?.scrollTo({ y: i * TILE_H, animated: true });
  const onScroll = (e: NativeSyntheticEvent<NativeScrollEvent>) => {
    const i = Math.max(0, Math.min(pages.length - 1, Math.round(e.nativeEvent.contentOffset.y / TILE_H)));
    if (i !== at) setAt(i);
  };
  useEffect(() => {
    if (!hint || !many || hintShown) return;
    let seen = false;
    try { seen = Platform.OS === "web" && window.localStorage.getItem("ananta.tiles.hinted") === "1"; } catch { /* storage blocked */ }
    hintShown = true;
    if (seen) return;
    const a = setTimeout(() => ref.current?.scrollTo({ y: 30, animated: true }), 1100);
    const b = setTimeout(() => ref.current?.scrollTo({ y: 0, animated: true }), 1600);
    try { if (Platform.OS === "web") window.localStorage.setItem("ananta.tiles.hinted", "1"); } catch { /* storage blocked */ }
    return () => { clearTimeout(a); clearTimeout(b); };
  }, [hint, many]);
  return (
    <View style={{ flex: 1, minWidth: 0, height: TILE_H, backgroundColor: C.card, borderRadius: 16, overflow: "hidden" }}>
      <ScrollView ref={ref} style={{ height: TILE_H }} pagingEnabled={many} scrollEnabled={many} nestedScrollEnabled showsVerticalScrollIndicator={false}
        onScroll={onScroll} scrollEventThrottle={16} decelerationRate="fast">
        {pages.map((p, i) => (
          <Pressable key={p.label + i} onPress={() => onOpen(p)} accessibilityRole="button"
            accessibilityLabel={`${p.label} ${p.value}${p.sub ? ", " + p.sub : ""}${p.sub2 ? ", " + p.sub2 : ""}${many ? `. ${i + 1} of ${pages.length}, swipe up for more` : ""}`}
            style={{ height: TILE_H, paddingHorizontal: 16, paddingRight: many ? 22 : 16, justifyContent: "center" }}>
            <Meta numberOfLines={1}>{p.label} ›</Meta>
            <Text numberOfLines={1} style={[TY.number, fit(String(p.value)), { color: C.text, marginTop: 2 }]}>{p.value}</Text>
            {p.sub ? <Meta numberOfLines={1} color={p.tone === "good" ? C.good : p.tone === "bad" ? C.bad : C.dim} style={{ marginTop: 2 }}>{p.sub}</Meta> : null}
            {p.sub2 ? <Meta faint={!p.tone2} color={p.tone2 === "good" ? C.good : p.tone2 === "bad" ? C.bad : undefined} numberOfLines={1}>{p.sub2}</Meta> : null}
          </Pressable>
        ))}
      </ScrollView>
      {many ? (
        <View style={{ position: "absolute", right: 10, top: 0, bottom: 0, justifyContent: "center", gap: 6 }}>
          {pages.map((p, i) => (
            <Pressable key={p.label + "dot"} onPress={() => go(i)} hitSlop={10} accessibilityRole="button" accessibilityLabel={`Show ${p.label}`}>
              <View style={{ width: 5, height: i === at ? 16 : 5, borderRadius: 3, backgroundColor: i === at ? G.gold() : C.faint, opacity: i === at ? 1 : 0.5 }} />
            </Pressable>
          ))}
        </View>
      ) : null}
    </View>
  );
}

// "Only point to point. Simple readable points. We show first 2 points and add show more buttons."
function PointsCard({ c }: { c: any }) {
  const [open, setOpen] = useState(false);
  const pts: string[] = Array.isArray(c.points) && c.points.length ? c.points : [];
  if (!pts.length) return <MoreCard c={c} />;
  const more = pts.length - 2;
  return (
    <NCard>
      <Meta color={c.accent ? G.gold() : undefined}>{c.label}</Meta>
      <View style={{ marginTop: 10, gap: 10 }}>
        {(open ? pts : pts.slice(0, 2)).map((p, i) => (
          <View key={i} style={{ flexDirection: "row", gap: 10 }}>
            <View style={{ width: 5, height: 5, borderRadius: 3, backgroundColor: G.gold(), marginTop: 9 }} />
            <Body style={{ flex: 1 }}>{p}</Body>
          </View>
        ))}
      </View>
      {more > 0 ? (
        <Pressable onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }} hitSlop={6}
          style={{ marginTop: 8, minHeight: 32, justifyContent: "center", alignSelf: "flex-start" }}>
          <Text style={[TY.meta, { color: G.gold() }]}>{open ? "Show less" : `Show ${more} more`}</Text>
        </Pressable>
      ) : null}
      {c.foot && (open || more <= 0) ? <Meta faint style={{ marginTop: 8 }}>{c.foot}</Meta> : null}
    </NCard>
  );
}

// a card that came as one paragraph (the crypto surface): about five lines, then "Read more"
function MoreCard({ c }: { c: any }) {
  const [open, setOpen] = useState(false);
  const long = String(c.text || "").length > 260;
  return (
    <NCard>
      <Meta color={c.accent ? G.gold() : undefined}>{c.label}</Meta>
      <Body style={{ marginTop: 4 }} numberOfLines={open || !long ? undefined : 5}>{c.text}</Body>
      {long ? (
        <Pressable onPress={() => setOpen(!open)} accessibilityRole="button" style={{ marginTop: 6, minHeight: 32, justifyContent: "center" }}>
          <Text style={[TY.meta, { color: G.gold() }]}>{open ? "Show less" : "Read more"}</Text>
        </Pressable>
      ) : null}
      {c.foot ? <Meta faint style={{ marginTop: 8 }}>{c.foot}</Meta> : null}
    </NCard>
  );
}
