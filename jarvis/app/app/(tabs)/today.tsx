// Home as mission control (Madhav approved the mock, 2026-10-04). Three depths: this page is the glance (are all parts
// running, the value, the market rule, Jarvis's day, what we found, what needs you); a tap goes one level deeper (Jarvis's
// book, what we missed, a coin or a trade); the Lab switch brings back the research views (the Lab page, the activity feed).
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
import { useLab } from "../../src/lab";
import { C, pnlColor } from "../../src/theme";

const KIND: Record<string, { color: string; label: string }> = {
  buy: { color: C.accent, label: "BUY" }, sell: { color: C.text, label: "SELL" }, watch: { color: C.faint, label: "ORDER" },
  portfolio: { color: C.accent, label: "PORTFOLIO" }, warn: { color: C.warn, label: "WARNING" }, info: { color: C.faint, label: "YOU" },
  alert: { color: C.warn, label: "ALERT" }, brief: { color: C.accent, label: "BRIEF" }, setup: { color: C.good, label: "YOUR SETUP" },
  request: { color: C.accent, label: "REPAIR SHOP" },
};
// Findings tags: words, plus a colour pair that differs in lightness, not hue alone.
const TAG: Record<string, [string, string, string]> = {
  MISSED: ["MISSED", C.warn, C.warnSoft], SEEN: ["SEEN", C.accent, C.accentSoft], LESSON: ["LESSON", C.text, C.card2],
  SHIFT: ["MARKET", C.warn, C.warnSoft], DOWN: ["DOWN", C.bad, C.badSoft],
};

function greeting(): string {
  const h = new Date().getHours();
  return h < 12 ? "Morning, Madhav" : h < 17 ? "Afternoon, Madhav" : "Evening, Madhav";
}

export default function Home() {
  const { data: d, err, loading, reload } = useData("/v3/home");
  const { data: inbox, reload: reloadInbox } = useData("/v3/inbox");
  const { data: br, reload: reloadBrief } = useData("/v3/brief", 300000);
  const { data: me } = useData("/v3/me", 0);
  const [lab, setLab] = useLab();
  const [briefing, setBriefing] = useState(false);
  const [all, setAll] = useState(false);
  const [briefOpen, setBriefOpen] = useState(false);
  const [showActivity, setShowActivity] = useState<boolean | null>(null);   // null = the default: open in Lab view
  const activityLit = useSpotActive("home.activity");              // Ananta pointing at it opens it
  useFocusEffect(useCallback(() => { setScreen({ screen: "home", label: "Home tab: status, value, the market rule, Jarvis today, findings, what needs you" }); }, []));
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
  const actOpen = (showActivity ?? lab) || activityLit;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View style={{ gap: 2, flex: 1 }}>
          <T dim small>{s.date} · paper money</T>
          <Text style={{ color: C.text, fontSize: 24, fontWeight: "700", letterSpacing: -0.3 }}>{greeting()}</Text>
        </View>
        <View style={{ alignItems: "center", gap: 2 }} accessibilityLabel="Lab view">
          <Switch value={lab} onValueChange={setLab} trackColor={{ true: C.accent, false: C.line }} />
          <Text style={{ color: lab ? C.accent : C.dim, fontSize: 11, fontWeight: "600" }}>Lab</Text>
        </View>
      </View>

      <Spot id="home.status">
        <HealthStrip h={m.health} />
      </Spot>

      {me?.guest ? (
        <Card title="Welcome to Ananta" sub="Madhav's trading assistant, in practice mode">
          <T small>Ananta watches 10 coins all day, explains what it sees and why it would or would not trade, and learns from its own record. Everything you do here goes to your own practice book.</T>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {["Show me around", "What are we doing here?", "How do I make a paper trade?"].map((q) => (
              <Pressable key={q} onPress={() => router.push({ pathname: "/(tabs)/ask", params: { q, t: String(Date.now()) } })}
                style={{ backgroundColor: C.accent, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8 }}>
                <Text style={{ color: "#FFF", fontWeight: "700", fontSize: 13 }}>{q}</Text>
              </Pressable>
            ))}
          </View>
        </Card>
      ) : null}

      {lab ? (
        <Card onPress={() => router.push("/lab")} title="Lab" sub="Evidence pipeline, scoreboard, repair shop, requests"
          right={<Text style={{ color: C.accent, fontSize: 18 }}>›</Text>} />
      ) : null}

      <Spot id="home.value">
        <Card>
          <T dim small>All paper books</T>
          <View style={{ flexDirection: "row", alignItems: "baseline", gap: 10, flexWrap: "wrap" }}>
            <Text style={{ color: C.text, fontSize: 32, fontWeight: "700", letterSpacing: -0.6 }}>{usd(s.paper_value, 0)}</Text>
            <Text style={{ color: pnlColor(change), fontSize: 15, fontWeight: "600" }}>{change >= 0 ? "+" : "-"}${Math.abs(change).toFixed(0)} since start</Text>
          </View>
          <T dim small>
            Started with {usd(s.start_value, 0)}{m.value?.since ? ` on ${m.value.since}` : ""}
            {s.today_change != null ? ` · ${s.today_change >= 0 ? "+" : "-"}$${Math.abs(s.today_change).toFixed(2)} today` : ""} · no real money
          </T>
          {m.value?.v?.length > 2 ? (
            <View style={{ marginTop: 8 }}>
              <LineChart height={64} showAxis={false} series={[{ data: m.value.v, color: C.accent, fill: true }]}
                refs={[{ value: m.value.start, color: C.dim, label: "Start" }]} />
            </View>
          ) : null}
        </Card>
      </Spot>

      <Spot id="home.market">
        <MarketCard mk={m.market} />
      </Spot>

      <Spot id="home.jarvis">
        <JarvisCard jv={m.jarvis} />
      </Spot>

      <Spot id="home.findings">
        <Card title="Findings" right={<Text onPress={() => router.push("/missed")} style={{ color: C.accent, fontWeight: "600" }}>Missed moves ›</Text>}>
          {(m.findings ?? []).length === 0 ? <T dim>Nothing new in the last two days. The missed-move check runs half an hour after each daily close.</T> : null}
          {(m.findings ?? []).map((f: any, i: number) => {
            const tg = TAG[f.kind] ?? TAG.LESSON;
            const open = () => (f.link === "missed" ? router.push("/missed") : askAbout({ screen: "home", label: f.title, coin: f.coin, item: f }, `Explain this finding: ${f.title}. ${f.body}`));
            return (
              <View key={i}>
                {i ? <Divider /> : null}
                <Pressable onPress={open} style={{ flexDirection: "row", gap: 12, paddingVertical: 10 }} accessibilityRole="button">
                  <View style={{ backgroundColor: tg[2], borderRadius: 6, paddingHorizontal: 6, paddingVertical: 3, alignSelf: "flex-start" }}>
                    <Text style={{ color: tg[1], fontSize: 11, fontWeight: "700" }}>{tg[0]}</Text>
                  </View>
                  <View style={{ flex: 1, gap: 2 }}>
                    <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>{f.title}</Text>
                    <Text style={{ color: C.dim, fontSize: 13, lineHeight: 18 }} numberOfLines={3}>{f.body}</Text>
                  </View>
                </Pressable>
              </View>
            );
          })}
        </Card>
      </Spot>

      <Spot id="home.inbox">
        <Card title="Needs you" sub={needs ? "Nothing happens until you confirm." : undefined}>
          {needs === 0 ? <T>Nothing right now. Jarvis's evening review comes at 8:30 pm.</T> : null}
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

      <Spot id="home.brief">
        <Card title={br?.brief ? `${br.brief.kind === "morning" ? "Morning" : "Evening"} brief` : "Daily brief"}
          sub={br?.brief ? new Date(br.brief.t * 1000).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" }) : "Written at 8:00 and 21:30"}
          right={<Text onPress={async () => { setBriefing(true); try { await api("/v3/brief/now", {}); reloadBrief(); } catch (e) { } setBriefing(false); }}
            style={{ color: C.accent, fontWeight: "600" }}>{briefing ? "Writing…" : "Brief me now"}</Text>}>
          {br?.brief ? (
            <Pressable onPress={() => setBriefOpen(true)} accessibilityHint="Opens the full brief">
              <Text numberOfLines={2} ellipsizeMode="tail" style={{ color: C.text, fontSize: 15, lineHeight: 21 }}>{br.brief.text}</Text>
              <Text style={{ color: C.accent, fontSize: 13, fontWeight: "600", marginTop: 4 }}>Read the full brief ›</Text>
            </Pressable>
          ) : <T dim>No brief yet today.</T>}
        </Card>
      </Spot>
      <BriefPopup open={briefOpen} onClose={() => setBriefOpen(false)} title={br?.brief ? `${br.brief.kind === "morning" ? "Morning" : "Evening"} brief` : "Brief"}
        when={br?.brief ? new Date(br.brief.t * 1000).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" }) : ""} text={br?.brief?.text ?? ""} />

      <Spot id="home.books">
        <Card title="Our books" sub="Tap a row for the full book">
          <Row title="Jarvis's book" sub={`${m.jarvis?.open?.length ?? 0} open · against its random twins`} value={m.jarvis?.verdict ?? "–"}
            onPress={() => router.push("/jarvis")} />
          <Divider />
          <Row title="Trend portfolio" sub={`${s.portfolio.holding} coins held · ${s.portfolio.mode === "AUTO" ? "Autopilot on" : "Suggests, you approve"}`}
            value={usd(s.portfolio.value)} valueSub={pct(s.portfolio.return_pct)} valueSubColor={pnlColor(s.portfolio.return_pct)}
            onPress={() => router.push("/(tabs)/portfolio")} />
          <Divider />
          <Row title="Explorer" sub={`${s.explorer.open} open · checks 10 coins every 15 min`} value={usd(s.explorer.value)}
            valueSub={`${s.explorer.opened_today} bought · ${s.explorer.closed_today} sold today`}
            onPress={() => router.push({ pathname: "/(tabs)/portfolio", params: { tab: "explorer", t: String(Date.now()) } })} />
          {lab ? (<><Divider /><Row title="Hourly watch" sub="Hunter and Squeeze strategies" value={`${s.hourly_watch.looks_today}`} valueSub="looks today" /></>) : null}
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
      <Text style={{ color: ok ? "#05603A" : "#912018", fontWeight: "700", fontSize: 14 }}>
        {ok ? `All ${h.of} parts running` : `${h.down.length} part${h.down.length === 1 ? "" : "s"} down`}
      </Text>
      <Text style={{ color: ok ? "#05603A" : "#912018", fontSize: 13, flex: 1 }} numberOfLines={1}>{ok ? ago : `: ${h.down.join(", ")}`}</Text>
    </Pressable>
  );
}

// The rule that matters most: Bitcoin against its 50-day average, with the chart that shows it.
function MarketCard({ mk }: { mk: any }) {
  if (!mk) return null;
  const allowed = mk.regime === "ALLOWED";
  const crossing = (allowed && mk.live_side === "below") || (!allowed && mk.live_side === "above");
  return (
    <Card onPress={() => router.push("/coin/BTC")}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <T dim small>The market</T>
        <View style={{ backgroundColor: allowed ? C.goodSoft : C.warnSoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 }}>
          <Text style={{ color: allowed ? "#05603A" : "#7A2E0E", fontWeight: "700", fontSize: 12 }}>{allowed ? "ALLOWED" : "RISK-OFF"}</Text>
        </View>
      </View>
      <Text style={{ color: C.text, fontSize: 17, fontWeight: "600", lineHeight: 23 }}>
        Bitcoin is {Math.abs(mk.vs_pct).toFixed(0)}% {mk.vs_pct >= 0 ? "above" : "below"} its 50-day average. {allowed ? "Buying is allowed." : "We stay careful: the trend portfolio sits in cash."}
      </Text>
      {crossing ? <T small style={{ color: C.warn }}>Bitcoin has crossed the line during the day: the daily close decides.</T> : null}
      <View style={{ marginTop: 6 }}>
        <LineChart height={110} series={[{ data: mk.closes, color: C.text, width: 1.6, label: "Bitcoin" }, { data: mk.ema, color: C.accent, dashed: true, label: "50-day" }]}
          xLabels={["90 days ago", "today"]} />
      </View>
      <T dim small>A daily close on the other side of the dashed line flips the market, and your phone gets a note.</T>
    </Card>
  );
}

// Jarvis's day: what it decided, what it holds, how far from a verdict against its random twins.
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
        <T dim small>Jarvis today</T>
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

// The full brief in a small window: closes with ✕ or a tap anywhere outside it.
function BriefPopup({ open, onClose, title, when, text }: { open: boolean; onClose: () => void; title: string; when: string; text: string }) {
  return (
    <Modal visible={open} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(15,20,35,0.45)", justifyContent: "center", padding: 20 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 18, maxHeight: "75%", overflow: "hidden" }}>
          <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingTop: 14, paddingBottom: 8 }}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.text, fontWeight: "700", fontSize: 17 }}>{title}</Text>
              {when ? <Text style={{ color: C.faint, fontSize: 12 }}>{when}</Text> : null}
            </View>
            <Pressable onPress={onClose} hitSlop={14} accessibilityLabel="Close"
              style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: C.card2, alignItems: "center", justifyContent: "center" }}>
              <Text style={{ color: C.text, fontSize: 15, fontWeight: "700" }}>✕</Text>
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 18 }}>
            <Text style={{ color: C.text, fontSize: 15, lineHeight: 23 }}>{text}</Text>
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
