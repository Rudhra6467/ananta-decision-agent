// Home (plan 3.1), redrawn Oct 14 to one grammar: "how is my account, and does anything need me?"
//  the greeting and the health strip · the account (one number, one line, the holdings, the dial; More opens the rest) ·
//  Needs you (a rule that passed and may step up, portfolio changes, the mandate's actions; one line when empty) ·
//  Ananta's note (three lines, More) · one line for the lab · findings · the activity feed, folded.
// The coins and the market rule live on Markets; the lab's books under Books › Details › Lab.
import { Spot, useSpotActive } from "../../src/spotlight";
import { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { ActionCard } from "../../src/actions";
import { api } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { Progress } from "../../src/charts";
import { ExplainSheet, showToast } from "../../src/blocks";
import { Act, Btn, Busy, Card, Divider, Dot, ErrorBox, ListState, Screen, StatCard, T, Tag, cad, cadSigned, dayOf, pct, s as st, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, live, pnlColor } from "../../src/theme";
import { VisitorHome, useMe } from "../../src/visitor";
import { ConceptCard, Findings, ValueCard, hello } from "../../src/home";

const KIND: Record<string, { color: string; label: string }> = live(() => ({
  buy: { color: C.accent, label: "BUY" }, sell: { color: C.text, label: "SELL" }, watch: { color: C.faint, label: "ORDER" },
  portfolio: { color: C.accent, label: "PORTFOLIO" }, warn: { color: C.warn, label: "WARNING" }, info: { color: C.faint, label: "YOU" },
  alert: { color: C.warn, label: "ALERT" }, brief: { color: C.accent, label: "BRIEF" }, setup: { color: C.good, label: "YOUR SETUP" },
  request: { color: C.accent, label: "REPAIR SHOP" },
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
  if (!d?.visitor) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} onRetry={reload} /></Screen>;
  return <VisitorHome d={d} loading={loading} reload={reload} />;
}

function OwnerHome() {
  const { data: d, err, loading, reload } = useData("/v3/home");
  const { data: inbox, reload: reloadInbox } = useData("/v3/inbox");
  const { data: nd, reload: reloadNeeds } = useData("/v3/needs", 300000);      // Oct 14: the decisions waiting for Madhav
  const { data: bk } = useData("/v3/books", 120000);                           // the fallback value card before the account started
  const [all, setAll] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const activityLit = useSpotActive("home.activity");              // Ananta pointing at it opens it
  useFocusEffect(useCallback(() => { setScreen({ screen: "home", label: "Home tab: the account, what needs you, Ananta's note, the lab, findings" }); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} onRetry={reload} /></Screen>;
  const s = d.summary;
  const m = d.mission ?? {};
  const approveAll = async () => {
    if (!(await confirmWithFaceId("Approve portfolio changes", `${s.portfolio.pending} paper change(s) will be made now.`))) return;
    await api("/portfolio/approve", { ids: "all" });
    reload();
  };
  const feed = all ? d.feed : d.feed.slice(0, 8);
  const actOpen = showActivity || activityLit;
  const refreshNeeds = () => { reloadInbox(); reloadNeeds(); reload(); };
  return (
    <Screen loading={loading} onRefresh={() => { reload(); reloadNeeds(); }}>
      <View style={{ gap: 2 }}>
        <T small>{s.date} · paper money</T>
        <Text style={st.title}>{hello(undefined, true)}</Text>
      </View>

      <Spot id="home.status">
        <HealthStrip h={m.health} />
      </Spot>
      <ConceptCard />

      <Spot id="home.value">
        {m.account?.started ? <AccountCard a={m.account} /> : (
          <ValueCard label="Paper books that still trade" value={bk?.summary?.value ?? null} change={bk ? bk.summary.value - bk.summary.start : null}
            sub={bk ? `Started with ${usd(bk.summary.start, 0)} · ${bk.summary.open_count} open trades · no real money` : "Adding up every book…"} />
        )}
      </Spot>

      <Spot id="home.inbox">
        <NeedsYou items={nd?.items ?? []} actions={inbox?.actions ?? []} pending={s.portfolio.pending} onDone={refreshNeeds} approveAll={approveAll} />
      </Spot>

      <Spot id="home.jarvis">
        {m.account?.note ? <OfficerNote note={m.account.note} /> : <JarvisCard jv={m.jarvis} />}
      </Spot>

      <Spot id="home.books">
        <LabLine lab={m.account?.lab ?? []} s={s} />
      </Spot>

      <Spot id="home.findings">
        <Findings items={(m.findings ?? []).slice(0, 3)} />
      </Spot>

      <Spot id="home.activity">
        <Pressable onPress={() => setShowActivity(!actOpen)} accessibilityRole="button" accessibilityState={{ expanded: actOpen }}
          style={{ flexDirection: "row", alignItems: "center", backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 16, paddingHorizontal: 14, minHeight: 52 }}>
          <Text style={[st.h, { flex: 1 }]}>Activity</Text>
          <T small>{d.feed.length} in the last 3 days</T>
          <Text style={[st.act, { marginLeft: 10 }]}>{actOpen ? "Hide" : "Show"}</Text>
        </Pressable>
        {actOpen ? (
          <Card>
            {feed.length === 0 ? <ListState state="empty" text="Nothing happened yet." /> : null}
            {feed.map((it: any, i: number) => (
              <View key={i}>
                {i ? <Divider /> : null}
                <Pressable onPress={() => it.trade_id && router.push(`/trade/${it.trade_id}`)} delayLongPress={350}
                  onLongPress={() => askAbout({ screen: "activity", label: `${it.title} (${it.time})`, coin: it.coin, id: it.trade_id, item: it }, `Explain this: ${it.title}`)} style={{ flexDirection: "row", gap: 12, paddingVertical: 11 }}>
                  <View style={{ paddingTop: 6 }}><Dot color={KIND[it.kind]?.color ?? C.faint} /></View>
                  <View style={{ flex: 1, gap: 2 }}>
                    <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                      <Text style={[st.rowTitle, { flex: 1 }, it.kind === "sell" && it.good != null ? { color: pnlColor(it.good ? 1 : -1) } : null]}>{it.title}</Text>
                      <T small>{it.time}</T>
                    </View>
                    <T small>{it.body}</T>
                  </View>
                  {it.trade_id ? <Text style={{ color: C.dim, fontSize: 18, alignSelf: "center" }}>›</Text> : null}
                </Pressable>
              </View>
            ))}
            {d.feed.length > 8 ? <Act label={all ? "Show less" : `Show all ${d.feed.length}`} onPress={() => setAll(!all)} /> : null}
          </Card>
        ) : null}
      </Spot>
    </Screen>
  );
}

// The account (Madhav, Oct 13): the $500 NDAX book is what he and Ananta look at; everything else is the lab.
// One number (its value), one line (holdings, cash, the next decision), the holdings as chips, the dial and brakes in one line; More opens why.
function AccountCard({ a }: { a: any }) {
  const change = (a.value_cad ?? 0) - (a.start_cad ?? 500);
  const pos = Object.entries(a.positions ?? {}) as [string, any][];
  const fired = Object.entries(a.brakes?.fired ?? {}).filter(([, n]) => (n as number) > 0);
  const brakes = a.brakes?.paused ? "brakes PAUSED after a 15% fall; only you can resume" : fired.length ? `brakes fired: ${fired.map(([k]) => k.replace(/_/g, " ")).join(", ")}` : "no brake fired";
  const dial = String(a.dial?.state ?? "…").split(":")[0];
  const pnlPct = (p: any) => (p.qty && p.last && p.paid ? 100 * ((p.qty * p.last) / p.paid - 1) : null);
  const ex = a.execution_check;
  return (
    <StatCard title="The account · $500 NDAX book · paper, real NDAX prices" label="The account"
      right={<Act tight label="Books ›" onPress={() => router.push({ pathname: "/(tabs)/portfolio", params: { t: String(Date.now()) } })} />}
      value={a.value_cad == null ? "…" : cad(a.value_cad)} aside={`${cadSigned(change)} · ${pct(a.return_pct)} since ${dayOf(a.started)}`} asideColor={pnlColor(change)}
      line={`${pos.length} holding${pos.length === 1 ? "" : "s"} · ${cad(a.cash_cad, 0)} cash · next decision at the daily close`}
      meta={`Dial ${dial} · ${brakes}`}
      more={<>
        {(a.dial?.why ?? []).map((w: string, i: number) => <T key={i} small>· {w}</T>)}
        <T small>{a.next}. Last step {a.last_step} UTC. Fills inside NDAX's bid and ask: {ex?.inside_bid_ask ?? 0} of {ex?.fills ?? 0}.</T>
      </>}>
      {pos.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {pos.map(([c, p]) => {
            const q = pnlPct(p);
            return <Tag key={c} text={`${c} · ${String(p.rule ?? p.sleeve ?? "").toLowerCase()}`} value={q == null ? cad(p.paid, 0) : pct(q)} valueColor={pnlColor(q)}
              onPress={() => router.push(`/coin/${c}`)} />;
          })}
        </View>
      ) : null}
    </StatCard>
  );
}

// Needs you: the decisions waiting for Madhav. A rule that passed its forward test (Review opens the evidence; Step up or Keep measuring),
// the mandate's actions, the trend portfolio's suggested changes. One line when nothing waits.
function NeedsYou({ items, actions, pending, onDone, approveAll }: { items: any[]; actions: any[]; pending: number; onDone: () => void; approveAll: () => void }) {
  const [open, setOpen] = useState<any>(null);
  const n = items.length + actions.length + (pending ? 1 : 0);
  const word = (step: string) => String(step).toLowerCase().replace(/_/g, " ");
  const decide = async (it: any, decision: "approve" | "later") => {
    try {
      await api("/v3/needs/decide", { id: it.id, decision });
      showToast(decision === "approve" ? `${it.rule} steps up to ${word(it.to)} ✓` : "Hidden for a week ✓");
    } catch (e: any) { showToast(e?.message ?? "Not changed"); }
    setOpen(null);
    onDone();
  };
  return (
    <Card>
      <View style={st.row}>
        <T small>Needs you{n ? ` · ${n}` : ""}</T>
        {n ? <T small>Nothing happens until you confirm</T> : null}
      </View>
      {n === 0 ? <ListState state="empty" text="Nothing right now. The next review comes at the daily close." /> : null}
      {items.map((it: any) => (
        <View key={it.id} style={{ gap: 6 }}>
          <Text style={st.h}>{it.title}</Text>
          <T>{it.line}</T>
          <View style={{ flexDirection: "row", gap: 8, paddingTop: 2 }}>
            <Btn label="Review" onPress={() => setOpen(it)} />
            <Btn label="Later" kind="secondary" onPress={() => decide(it, "later")} />
          </View>
        </View>
      ))}
      {actions.map((a: any) => <ActionCard key={a.id} a={a} onDone={onDone} />)}
      {pending ? (
        <View style={{ gap: 8 }}>
          <T>{pending} trend-portfolio change{pending === 1 ? "" : "s"} wait{pending === 1 ? "s" : ""} for your approval.</T>
          <View style={{ flexDirection: "row", gap: 8 }}>
            <Btn label="Review" kind="secondary" onPress={() => router.push({ pathname: "/(tabs)/portfolio", params: { tab: "portfolio", t: String(Date.now()) } })} />
            <Btn label="Approve all" onPress={approveAll} />
          </View>
        </View>
      ) : null}
      <ExplainSheet open={!!open} onClose={() => setOpen(null)} title={open?.title ?? ""}>
        {open ? (
          <>
            <T>{open.why}.</T>
            <T dim>{open.to === "PROMOTED" ? "Promoted" : "Live candidate"} means: {open.meaning}.</T>
            <T small>{open.note}</T>
            <Btn label={`Step up to ${word(open.to)}`} onPress={() => decide(open, "approve")} />
            <Btn label="Keep measuring · ask me again in a week" kind="secondary" onPress={() => decide(open, "later")} />
          </>
        ) : null}
      </ExplainSheet>
    </Card>
  );
}

// The officer's note: the brain's plain account of the day, written once after the close. Three lines, then More.
function OfficerNote({ note }: { note: any }) {
  const [more, setMore] = useState(false);
  return (
    <Card>
      <View style={st.row}>
        <T small>Ananta's note · {dayOf(note.day) || note.day}</T>
        <Act tight label="Ask ›" onPress={() => askAbout({ screen: "home", label: "The officer's note" }, "Tell me more about today's note on the account.")} />
      </View>
      <Text style={[st.t, { fontSize: 16, lineHeight: 23 }]} numberOfLines={more ? undefined : 3}>{note.note}</Text>
      <View style={[st.row, { marginTop: -4 }]}>
        <T faint>From the database, not from memory</T>
        <Act label={more ? "Show less" : "More"} onPress={() => setMore(!more)} />
      </View>
    </Card>
  );
}

// One line for the lab: every other book keeps measuring in the background; Details opens Books › Details › Lab.
function LabLine({ lab, s }: { lab: any[]; s: any }) {
  const measuring = lab.filter((x) => x.status === "EVIDENCE").length;
  const counted = lab.filter((x) => x.status === "ACTIVE" || x.status === "UNDER_REVIEW").length;
  const go = () => router.push({ pathname: "/(tabs)/portfolio", params: { tab: "lab", t: String(Date.now()) } });
  return (
    <Card onPress={go}>
      <View style={st.row}>
        <T small>The lab · measuring in the background</T>
        <Act tight label="Details ›" onPress={go} />
      </View>
      <T>{lab.length} strategies · {measuring} measuring · {counted} counted · Explorer {s.explorer?.opened_today ?? 0} bought, {s.explorer?.closed_today ?? 0} sold today</T>
    </Card>
  );
}

// Every part of Ananta, checked every 2 minutes (the health watchdog).
function HealthStrip({ h }: { h: any }) {
  if (!h) return null;
  const ok = h.all_ok;
  const ago = h.checked_s_ago == null ? "" : h.checked_s_ago < 90 ? " · checked just now" : ` · checked ${Math.round(h.checked_s_ago / 60)} min ago`;
  return (
    <Pressable onPress={() => askAbout({ screen: "home", label: "System health" }, "Is everything running?")} accessibilityRole="button"
      style={{ flexDirection: "row", alignItems: "center", gap: 8, backgroundColor: ok ? C.goodSoft : C.badSoft, borderRadius: 12, paddingHorizontal: 12, minHeight: 44 }}>
      <Dot color={ok ? C.good : C.bad} />
      <Text style={{ color: ok ? C.goodDeep : C.badDeep, fontWeight: "700", fontSize: 15 }}>
        {ok ? `All ${h.of} parts running` : `${h.down.length} part${h.down.length === 1 ? "" : "s"} down`}
      </Text>
      <Text style={{ color: ok ? C.goodDeep : C.badDeep, fontSize: 13, flex: 1 }} numberOfLines={1}>{ok ? ago : `: ${h.down.join(", ")}`}</Text>
    </Pressable>
  );
}

// Before the account started: Ananta's day, what it decided, what it holds, how far from a verdict against its random twins.
function JarvisCard({ jv }: { jv: any }) {
  if (!jv) return null;
  const take = jv.today?.TAKE ?? 0, pass = jv.today?.PASS ?? 0;
  const open = jv.open ?? [];
  const sentence = take || pass
    ? `Today I took ${take} paper trade${take === 1 ? "" : "s"} and passed on ${pass}. ${jv.left} decisions left.`
    : open.length ? `No new decisions today. ${open.length} of my trades are open.` : "No decisions yet today. I wake when a coin enters a zone or a setup fires.";
  return (
    <Card onPress={() => router.push("/jarvis")}>
      <View style={st.row}>
        <T small>Ananta today</T>
        <Act tight label="Open book ›" onPress={() => router.push("/jarvis")} />
      </View>
      <Text style={st.h}>{sentence}</Text>
      {open.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {open.slice(0, 8).map((o: any) => <Tag key={o.id} text={o.coin} value={o.pnl_pct == null ? "–" : pct(o.pnl_pct)} valueColor={pnlColor(o.pnl_pct)} />)}
        </View>
      ) : null}
      <View style={{ gap: 6 }}>
        <View style={st.row}>
          <T small>Score against random twins</T>
          <T small>{jv.verdict} · {jv.events} of 10 events</T>
        </View>
        <Progress value={jv.events ?? 0} of={10} />
      </View>
    </Card>
  );
}
