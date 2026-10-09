// Home (plan 3.1): the greeting (local time, "sir" for Madhav) and the health strip; the value card with its Brief button;
// Ananta today; The market as slides (coins with + and Load more, then the market rule chart); findings in simple words with
// details on tap; what needs you; your books; the activity feed folded. The Lab switch, Evidence card and brief card are gone
// (Evidence lives in Cockpit now).
import { Spot, useSpotActive } from "../../src/spotlight";
import { useCallback, useState } from "react";
import { Modal, Pressable, ScrollView, Switch, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { ActionCard } from "../../src/actions";
import { api } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { LineChart, Progress } from "../../src/charts";
import { Btn, Busy, Card, Divider, Dot, ErrorBox, Row, Screen, T, pct, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, live, pnlColor } from "../../src/theme";
import { VisitorHome, useMe } from "../../src/visitor";
import { ConceptCard, Findings, MarketSlides, ValueCard, hello } from "../../src/home";

const KIND: Record<string, { color: string; label: string }> = live(() => ({
  buy: { color: C.accent, label: "BUY" }, sell: { color: C.text, label: "SELL" }, watch: { color: C.faint, label: "ORDER" },
  portfolio: { color: C.accent, label: "PORTFOLIO" }, warn: { color: C.warn, label: "WARNING" }, info: { color: C.faint, label: "YOU" },
  alert: { color: C.warn, label: "ALERT" }, brief: { color: C.accent, label: "BRIEF" }, setup: { color: C.good, label: "YOUR SETUP" },
  request: { color: C.accent, label: "REPAIR SHOP" },
}));
// Findings tags: words, plus a colour pair that differs in lightness, not hue alone.
const TAG: Record<string, [string, string, string]> = live(() => ({
  MISSED: ["MISSED", C.warn, C.warnSoft], SEEN: ["SEEN", C.accent, C.accentSoft], LESSON: ["LESSON", C.text, C.card2],
  SHIFT: ["MARKET", C.warn, C.warnSoft], DOWN: ["DOWN", C.bad, C.badSoft],
}));

export default function Home() {
  const me = useMe();
  if (!me) return <Busy />;
  if (me.guest) return <GuestHome />;
  return <OwnerHome />;
}

// A visitor's Home: their name, their coins, their practice money and trades. Nothing of Madhav's.
function GuestHome() {
  const { data: d, err, loading, reload } = useData("/v3/home", 30000);
  useFocusEffect(useCallback(() => { setScreen({ screen: "home", label: "Home tab: your coins, your practice money, your trades" }); reload(); }, []));
  if (!d && loading) return <Busy />;
  if (!d?.visitor) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  return <VisitorHome d={d} loading={loading} reload={reload} />;
}

function OwnerHome() {
  const { data: d, err, loading, reload } = useData("/v3/home");
  const { data: inbox, reload: reloadInbox } = useData("/v3/inbox");
  const { data: wl } = useData("/v3/watchlists", 60000);
  const { data: bk } = useData("/v3/books", 120000);              // the same total as Books › Trades
  const [all, setAll] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const activityLit = useSpotActive("home.activity");              // Ananta pointing at it opens it
  useFocusEffect(useCallback(() => { setScreen({ screen: "home", label: "Home tab: value, Ananta today, the market, findings, what needs you" }); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  const s = d.summary;
  const m = d.mission ?? {};
  const approveAll = async () => {
    if (!(await confirmWithFaceId("Approve portfolio changes", `${s.portfolio.pending} paper change(s) will be made now.`))) return;
    await api("/portfolio/approve", { ids: "all" });
    reload();
  };
  const feed = all ? d.feed : d.feed.slice(0, 8);
  const actions = inbox?.actions ?? [];
  const needs = actions.length + (s.portfolio.pending ? 1 : 0);
  const change = s.paper_value - s.start_value;
  const actOpen = showActivity || activityLit;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <View style={{ gap: 2 }}>
        <T dim small>{s.date} · paper money</T>
        <Text style={{ color: C.text, fontSize: 24, fontWeight: "700", letterSpacing: -0.3 }}>{hello(undefined, true)}</Text>
      </View>

      <Spot id="home.status">
        <HealthStrip h={m.health} />
      </Spot>
      <ConceptCard />

      <Spot id="home.value">
        <ValueCard label="All paper books" value={bk?.summary?.value ?? null} change={bk ? bk.summary.value - bk.summary.start : null}
          sub={bk ? `Started with ${usd(bk.summary.start, 0)} · ${bk.summary.open_count} open trades · no real money` : "Adding up every book…"} />
      </Spot>

      <Spot id="home.jarvis">
        <JarvisCard jv={m.jarvis} />
      </Spot>

      <Spot id="home.market">
        <MarketSlides coins={wl?.coins ?? []} market={m.market} />
      </Spot>

      <Spot id="home.findings">
        <Findings items={m.findings ?? []} />
      </Spot>

      <Spot id="home.inbox">
        <Card title="Needs you" sub={needs ? "Nothing happens until you confirm." : undefined}>
          {needs === 0 ? <T>Nothing right now. Ananta's evening review comes at 8:30 pm.</T> : null}
          {actions.map((a: any) => <ActionCard key={a.id} a={a} onDone={() => { reloadInbox(); reload(); }} />)}
          {s.portfolio.pending ? (
            <View style={{ gap: 8 }}>
              <T>{s.portfolio.pending} trend-portfolio change(s) wait for your approval.</T>
              <View style={{ flexDirection: "row", gap: 10 }}>
                <View style={{ flex: 1 }}><Btn label="Review" kind="secondary" onPress={() => router.push("/(tabs)/portfolio")} /></View>
                <View style={{ flex: 1 }}><Btn label="Approve all" onPress={approveAll} /></View>
              </View>
            </View>
          ) : null}
        </Card>
      </Spot>

      <Spot id="home.books">
        <Card title="Your books" sub="Tap a row for the full book">
          <Row title="Ananta's book" sub={`${m.jarvis?.open?.length ?? 0} open · against its random twins`} value={m.jarvis?.verdict ?? "–"}
            onPress={() => router.push("/jarvis")} />
          <Divider />
          <Row title="Trend portfolio" sub={`${s.portfolio.holding} coins held · ${s.portfolio.mode === "AUTO" ? "Autopilot on" : "Suggests, you approve"}`}
            value={usd(s.portfolio.value)} valueSub={pct(s.portfolio.return_pct)} valueSubColor={pnlColor(s.portfolio.return_pct)}
            onPress={() => router.push("/(tabs)/portfolio")} />
          <Divider />
          <Row title="Explorer" sub={`${s.explorer.open} open · checks 10 coins every 15 min`} value={usd(s.explorer.value)}
            valueSub={`${s.explorer.opened_today} bought · ${s.explorer.closed_today} sold today`}
            onPress={() => router.push({ pathname: "/(tabs)/portfolio", params: { tab: "explorer", t: String(Date.now()) } })} />
          <Divider />
          <Row title="Hourly watch" sub="Hunter and Squeeze strategies" value={`${s.hourly_watch.looks_today}`} valueSub="looks today" />
        </Card>
      </Spot>

      <Spot id="home.activity">
        <Pressable onPress={() => setShowActivity(!actOpen)} style={{ flexDirection: "row", alignItems: "center", backgroundColor: C.card, borderColor: C.line,
          borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12 }}>
          <Text style={{ color: C.text, fontWeight: "700", fontSize: 15, flex: 1 }}>Activity</Text>
          <T small>{d.feed.length} in the last 3 days</T>
          <Text style={{ color: C.accent, fontWeight: "700", marginLeft: 10 }}>{actOpen ? "Hide ⌃" : "Show ⌄"}</Text>
        </Pressable>
        {actOpen ? (
          <Card>
            {feed.length === 0 ? <T dim>Nothing happened yet.</T> : null}
            {feed.map((it: any, i: number) => (
              <View key={i}>
                {i ? <Divider /> : null}
                <Pressable onPress={() => it.trade_id && router.push(`/trade/${it.trade_id}`)} delayLongPress={350}
                  onLongPress={() => askAbout({ screen: "activity", label: `${it.title} (${it.time})`, coin: it.coin, id: it.trade_id, item: it }, `Explain this: ${it.title}`)} style={{ flexDirection: "row", gap: 12, paddingVertical: 11 }}>
                  <View style={{ paddingTop: 6 }}><Dot color={KIND[it.kind]?.color ?? C.faint} /></View>
                  <View style={{ flex: 1, gap: 2 }}>
                    <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                      <Text style={{ color: it.kind === "sell" && it.good != null ? pnlColor(it.good ? 1 : -1) : C.text, fontWeight: "600", fontSize: 15, flex: 1 }}>{it.title}</Text>
                      <Text style={{ color: C.dim, fontSize: 12 }}>{it.time}</Text>
                    </View>
                    <Text style={{ color: C.dim, fontSize: 13, lineHeight: 18 }}>{it.body}</Text>
                  </View>
                  {it.trade_id ? <Text style={{ color: C.faint, fontSize: 18, alignSelf: "center" }}>›</Text> : null}
                </Pressable>
              </View>
            ))}
            {d.feed.length > 8 ? <Text onPress={() => setAll(!all)} style={{ color: C.accent, fontWeight: "600", paddingTop: 6 }}>{all ? "Show less" : `Show all ${d.feed.length}`}</Text> : null}
          </Card>
        ) : null}
      </Spot>
    </Screen>
  );
}

// Every part of Ananta, checked every 2 minutes (the health watchdog).
function HealthStrip({ h }: { h: any }) {
  if (!h) return null;
  const ok = h.all_ok;
  const ago = h.checked_s_ago == null ? "" : h.checked_s_ago < 90 ? " · checked just now" : ` · checked ${Math.round(h.checked_s_ago / 60)} min ago`;
  return (
    <Pressable onPress={() => askAbout({ screen: "home", label: "System health" }, "Is everything running?")} accessibilityRole="button"
      style={{ flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: ok ? C.goodSoft : C.badSoft, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10 }}>
      <Dot color={ok ? C.good : C.bad} />
      <Text style={{ color: ok ? C.goodDeep : C.badDeep, fontWeight: "700", fontSize: 14 }}>
        {ok ? `All ${h.of} parts running` : `${h.down.length} part${h.down.length === 1 ? "" : "s"} down`}
      </Text>
      <Text style={{ color: ok ? C.goodDeep : C.badDeep, fontSize: 13, flex: 1 }} numberOfLines={1}>{ok ? ago : `: ${h.down.join(", ")}`}</Text>
    </Pressable>
  );
}

// Ananta's day: what it decided, what it holds, how far from a verdict against its random twins.
function JarvisCard({ jv }: { jv: any }) {
  if (!jv) return null;
  const take = jv.today?.TAKE ?? 0, pass = jv.today?.PASS ?? 0;
  const open = jv.open ?? [];
  const sentence = take || pass
    ? `Today I took ${take} paper trade${take === 1 ? "" : "s"} and passed on ${pass}. ${jv.left} decisions left.`
    : open.length ? `No new decisions today. ${open.length} of my trades are open.` : "No decisions yet today. I wake when a coin enters a zone or a setup fires.";
  return (
    <Card onPress={() => router.push("/jarvis")}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <T dim small>Ananta today</T>
        <Text style={{ color: C.accent, fontWeight: "600", fontSize: 13 }}>Open book ›</Text>
      </View>
      <Text style={{ color: C.text, fontSize: 17, fontWeight: "600", lineHeight: 23 }}>{sentence}</Text>
      {open.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
          {open.slice(0, 8).map((o: any) => (
            <View key={o.id} style={{ backgroundColor: C.card2, borderRadius: 10, paddingVertical: 7, paddingHorizontal: 10, alignItems: "center", minWidth: 62 }}>
              <Text style={{ color: C.text, fontWeight: "700", fontSize: 13 }}>{o.coin}</Text>
              <Text style={{ color: pnlColor(o.pnl_pct), fontSize: 12 }}>{o.pnl_pct == null ? "–" : `${o.pnl_pct >= 0 ? "+" : ""}${o.pnl_pct.toFixed(1)}%`}</Text>
            </View>
          ))}
        </View>
      ) : null}
      <View style={{ gap: 6 }}>
        <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
          <T small dim>Score against random twins</T>
          <T small>{jv.verdict} · {jv.events} of 10 events</T>
        </View>
        <Progress value={jv.events ?? 0} of={10} />
      </View>
    </Card>
  );
}
