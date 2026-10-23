// Home (plan 3.1), redrawn Oct 14 to one grammar and again on Oct 15 (Madhav): "how is my account, and does anything need me?"
//  the greeting with the Ananta button (the mark; a number when something waits) · the health strip · the account (one number,
//  one line, the holdings, the dial; More opens the rest) · the account's trades (the old Books tab) · the activity feed, folded.
// Needs you, Ananta's note, the lab and findings moved into the Ananta button (src/ananta.tsx). The coins and the market rule live
// on Markets; the lab's books under Markets › Ananta market.
import { Spot, focusSpot, useSpotActive } from "../../src/spotlight";
import { useCallback, useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { Progress } from "../../src/charts";
import { Act, Busy, Card, Decision, Divider, Dot, ErrorBox, ListState, Screen, StatCard, T, Tag, cad, cadSigned, dayOf, pct, s as st, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, live, pnlColor } from "../../src/theme";
import { VisitorHome, useMe } from "../../src/visitor";
import { ConceptCard, ValueCard, hello } from "../../src/home";
import { AnantaButton, AnantaSheet, useAnantaCount } from "../../src/ananta";
import { RecentDecisions } from "../../src/decisions";
import { OptionsCard } from "../../src/options";
import { getMarket, W } from "../../src/market";
import { sayMoney, upDown, type VoiceSpec } from "../../src/sectionvoice";

const COIN_WORD: Record<string, string> = { BTC: "Bitcoin", ETH: "Ethereum", SOL: "Solana", XRP: "XRP", ADA: "Cardano", DOGE: "Dogecoin",
  AVAX: "Avalanche", LINK: "Chainlink", LTC: "Litecoin", BCH: "Bitcoin Cash" };
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
  const { data: bk } = useData("/v3/books", 120000);                           // the fallback value card before the account started
  const [all, setAll] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const [ananta, setAnanta] = useState(false);                                 // Oct 15: the Ananta button's space
  const p = useLocalSearchParams<{ ananta?: string; t?: string }>();
  useEffect(() => { if (p.ananta) setAnanta(true); }, [p.ananta, p.t]);
  const activityLit = useSpotActive("home.activity");              // Ananta pointing at it opens it
  const count = useAnantaCount(d?.summary?.portfolio?.pending ?? 0, (d?.mission?.findings ?? []).slice(0, 5));
  useFocusEffect(useCallback(() => { setScreen({ screen: "home", label: "Home tab: the account and its trades; the Ananta button holds what needs you, Ananta's note, the lab and findings" }); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} onRetry={reload} /></Screen>;
  const s = d.summary;
  const m = d.mission ?? {};
  const feed = all ? d.feed : d.feed.slice(0, 8);
  const actOpen = showActivity || activityLit;
  const dec = homeDecision(m, count.total);
  return (
    <Screen loading={loading} onRefresh={reload}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
        <View style={{ gap: 2, flex: 1 }}>
          <T small>{s.date} · paper money</T>
          <Text style={st.h}>{hello(undefined, true)}</Text>
        </View>
        <AnantaButton count={count.total} onPress={() => setAnanta(true)} />
      </View>
      <AnantaSheet open={ananta} onClose={() => setAnanta(false)} home={d} onChanged={reload} />

      <Decision spot="home.decision" verb={dec.verb} rest={dec.rest} why={dec.why}
        action={count.total ? { label: `${count.total} thing${count.total === 1 ? "" : "s"} need${count.total === 1 ? "s" : ""} you ›`, onPress: () => setAnanta(true) }
          : { label: "Trades ›", onPress: () => router.push({ pathname: "/(tabs)/watchlists", params: { tab: "ananta", sub: "mine" } } as any) }} />

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

      <Spot id="home.books">
        <RecentDecisions />
      </Spot>
      {getMarket() === "india" ? <Spot id="home.options"><OptionsCard /></Spot> : null}

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

// What Ananta is doing with the account, in one sentence (the decision line on Home)
function homeDecision(m: any, needs: number): { verb: string; rest?: string; why: string } {
  const a = m.account;
  if (!a?.started) {
    const jv = m.jarvis;
    const open = jv?.open?.length ?? 0;
    return { verb: open ? `Holding ${open} paper trade${open === 1 ? "" : "s"}` : "Holding nothing", rest: "in the lab",
      why: "The account starts at the next daily close." };
  }
  const pos = Object.keys(a.positions ?? {});
  const names = pos.map((c) => COIN_WORD[c] ?? c);
  const dialOpen = /open/i.test(String(a.dial?.state ?? ""));
  const fired = Object.entries(a.brakes?.fired ?? {}).filter(([, n]) => (n as number) > 0).map(([k]) => k.replace(/_/g, " "));
  const verb = pos.length ? `Holding ${names.length <= 3 ? names.join(" and ") : `${names.length} ${W().coins}`}` : dialOpen ? "Holding nothing yet" : "In cash";
  const rest = pos.length ? "in the account" : undefined;
  const why = a.brakes?.paused ? "Brakes paused it after a 15% fall; only you can resume."
    : fired.length ? `Brakes fired (${fired.join(", ")}): no new buys for now.`
    : dialOpen ? W().dial_open_why
    : W().dial_closed_why;
  return { verb, rest, why: needs ? why : `${why} Nothing needs you.` };
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
  const voice: VoiceSpec = { id: "home.account", label: "the account", back: "home", spot: "home.value", screen: "home",
    questions: [change < 0 ? "Why is the account down?" : "Why is the account up?", "When does it buy or sell next?", "What are the brakes?", "Show me the trades"],
    say: () => `This is the account: ${W().account_say}. It is worth ${sayMoney(a.value_cad, W().account_ccy)},`
      + ` ${upDown(change)} ${sayMoney(change, W().account_ccy)} since ${dayOf(a.started)}.`
      + (pos.length ? ` It holds ${pos.map(([c, p]) => { const q = pnlPct(p); return `${COIN_WORD[c] ?? c}${q == null ? "" : `, ${q >= 0 ? "up" : "down"} ${Math.abs(q).toFixed(1)} percent`}`; }).join(", and ")},` : ` It holds no ${W().coins},`)
      + ` with ${sayMoney(a.cash_cad, W().account_ccy)} in cash. The dial is ${dial.toLowerCase()}, and ${brakes}. ${W().next_decision}.` };
  return (
    <StatCard voice={voice} title={W().account_title} label="The account"
      right={<Act tight label="Trades ›" onPress={() => router.push({ pathname: "/(tabs)/watchlists", params: { tab: "ananta", sub: "mine" } } as any)} />}
      value={a.value_cad == null ? "…" : cad(a.value_cad)} aside={`${cadSigned(change)} · ${pct(a.return_pct)} since ${dayOf(a.started)}`} asideColor={pnlColor(change)}
      line={`${pos.length} holding${pos.length === 1 ? "" : "s"} · ${cad(a.cash_cad, 0)} cash · ${W().next_line}`}
      meta={`Dial ${dial} · ${brakes}`}
      more={<>
        {(a.dial?.why ?? []).map((w: string, i: number) => <T key={i} small>· {w}</T>)}
        <T small>{a.next}. Last step {a.last_step} UTC. Fills inside {W().exchange}'s bid and ask: {ex?.inside_bid_ask ?? 0} of {ex?.fills ?? 0}.</T>
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
    : open.length ? `No new decisions today. ${open.length} of my trades are open.` : `No decisions yet today. ${W().wake}`;
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
