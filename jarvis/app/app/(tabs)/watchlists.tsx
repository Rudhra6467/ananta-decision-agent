// Markets (was Watchlists; plan 3.5, D9), for Madhav and visitors alike. "What is the market doing, and what are we watching?"
//  1. the trend dial first (OPEN or CLOSED, one line of why, the brakes; Why › opens the rest) — Oct 14, one grammar
//  2. the watches: this account's watches (coins or a group, a setup kind, a mode, a state), + Watch to add one; then the coins
//  3. the whole market (every coin Ananta watches live), Ananta's reasoning (one line per coin; a tap shows the whole chain),
//     nearing a trade (coins closest to passing, with what is still missing), reconstruction (Madhav only)
// Zones and "Your setups" live on each coin's page and in Ananta market.
// Oct 15 (Madhav): two pages under one top switch. "Markets" is the market as before; "Ananta market" is what the old Books ›
// Details held (Ananta's book, the lab's books, the trend portfolio, the Explorer, your trades, your setups; src/books.tsx).
// A visitor's second page is "My book". The `tab` param (markets | ananta) and `sub` pick the page, for the drawer and deep links.
import { Spot } from "../../src/spotlight";
import { useCallback, useEffect, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { api } from "../../src/api";
import { Progress } from "../../src/charts";
import { Act, Btn, Busy, Card, Divider, ErrorBox, ListState, Screen, Section, T, Tag } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME } from "../../src/theme";
import { ChainLadder } from "../../src/chain";
import { ExplainSheet, showToast } from "../../src/blocks";
import { CoinLine } from "../../src/home";
import { useMe } from "../../src/visitor";
import { ExposureDial, WholeMarket } from "../../src/universe";
import { AnantaMarket, GuestBook } from "../../src/books";
import { Segmented } from "../../src/ui";
import { VoiceBtn, VoiceStrip, type VoiceSpec } from "../../src/sectionvoice";

const GROUP: Record<string, string> = { my_coins: "My coins", all: "All 10 coins", large: "The large coins" };
const watchWho = (w: any) => (w.group ? GROUP[w.group] ?? w.group : (w.coins ?? []).map((c: string) => COIN_NAME[c] ?? c).join(", "));

const MODE: Record<string, string> = { tell: "Tell me", ask: "Ask me first", auto: "Auto" };
const NEXT_MODE: Record<string, string> = { tell: "ask", ask: "auto", auto: "tell" };
const STATE: Record<string, [string, string]> = { WATCHING: ["Watching", "dim"], CLOSE: ["Getting close", "warn"], FIRED: ["Fired", "good"], PAUSED: ["Paused", "faint"] };

export default function Watchlists() {
  const me = useMe();
  const own = !!me && !me.guest;
  const p = useLocalSearchParams<{ tab?: string; sub?: string; t?: string }>();
  const [top, setTop] = useState(p.tab === "ananta" ? "ananta" : "markets");
  useEffect(() => { if (p.tab === "ananta" || p.tab === "markets") setTop(p.tab); }, [p.tab, p.t]);
  const header = (
    <View style={{ paddingHorizontal: 16, paddingTop: 10, paddingBottom: 2 }}>
      <Segmented size="lg" value={top} onChange={setTop} options={[{ key: "markets", label: "Markets" }, { key: "ananta", label: me?.guest ? "My book" : "Ananta market" }]} />
    </View>
  );
  if (top === "ananta") return <View style={{ flex: 1, backgroundColor: C.bg }}>{header}{me?.guest ? <GuestBook /> : <AnantaMarket sub={p.sub} t={p.t} />}</View>;
  return <View style={{ flex: 1, backgroundColor: C.bg }}>{header}<MarketPage me={me} own={own} /></View>;
}

function MarketPage({ me, own }: { me: any; own: boolean }) {
  const { data: d, err, loading, reload } = useData(me ? "/v3/coins" : null, 60000);
  const { data: w, reload: reloadW } = useData(me ? "/v3/watches/mine" : null, 60000);
  const { data: ch } = useData(me ? "/v3/chain" : null, 300000);
  const { data: ev } = useData(own ? "/v3/evidence/live" : null, 600000);
  const [add, setAdd] = useState(false);
  const { glow } = useLocalSearchParams<{ glow?: string }>();          // Phase 5: the watch just made glows when Watchlists opens
  useFocusEffect(useCallback(() => { setScreen({ screen: "markets", label: "Markets tab: the trend dial, your watches, the coins, Ananta's reasoning, nearing a trade" }); reloadW(); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} onRetry={reload} /></Screen>;
  const myCoins: string[] = me?.guest ? (me?.profile?.coins ?? []) : [];
  const coins = (d.coins ?? []).filter((c: any) => !myCoins.length || myCoins.includes(c.coin));
  const near = [...(d.coins ?? [])].filter((c: any) => c.closest).sort((a: any, b: any) => b.closest.met / b.closest.of - a.closest.met / a.closest.of).slice(0, 5);
  const rb = ev?.rebuild;
  const watches: any[] = w?.watches ?? [];
  const watchVoice: VoiceSpec = { id: "markets.watches", label: "your watches", back: "markets:markets", spot: "markets.watches", screen: "markets",
    questions: watches.length ? ["Which of my watches is closest to firing?", "What does each watch mode do?", "What should I watch today?"]
      : ["What is a watch?", "Which setups can I watch for?", "What should I watch today?"],
    say: () => "These are your watches: coins or a group you asked me to keep an eye on, for a kind of setup."
      + (watches.length
        ? ` You have ${watches.length}: ${watches.slice(0, 3).map((x) => `${watchWho(x)}, ${(STATE[x.state] ?? [String(x.state).toLowerCase()])[0].toLowerCase()}`).join("; ")}${watches.length > 3 ? `, and ${watches.length - 3} more` : ""}.`
        : " You have none yet. Tap plus Watch to add one: the coins, the setup, and whether I just tell you, ask you first, or act on paper.")
      + " A watch tells you when its setup gets close, and when it fires." };
  const coinsVoice: VoiceSpec = { id: "markets.coins", label: "the coins Ananta watches", back: "markets:markets", spot: "markets.coins", screen: "markets",
    questions: ["Which coin looks strongest right now?", "Which coins are near support?", "Why these ten coins?"],
    say: () => `These are the ${coins.length} coins Ananta watches most closely: ${coins.slice(0, 10).map((c: any) => COIN_NAME[c.coin] ?? c.coin).join(", ")}.`
      + " Each line shows the price, today's change and the one-hour trend. Tap a coin for its page, or plus to watch it." };
  return (
    <Screen loading={loading} onRefresh={() => { reload(); reloadW(); }}>
      <Spot id="markets.summary">
        <ExposureDial own={own} />
        <Spot id="markets.watches">
        <Section title={w ? `Watches · ${watches.length}` : "Watches"} right={
          <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}><VoiceBtn v={watchVoice} /><Act tight label="+ Watch" onPress={() => setAdd(true)} /></View>} />
        <Card>
          {!w ? <ListState state="loading" lines={1} /> : null}
          {w && watches.length === 0 ? <ListState state="empty" text="No watches yet." action={{ label: "+ Watch", onPress: () => setAdd(true) }} /> : null}
          {watches.map((x: any, i: number) => <View key={x.id}>{i ? <Divider /> : null}<WatchRow w={x} reload={reloadW} glow={!!glow && glow === x.id} /></View>)}
          <VoiceStrip id="markets.watches" />
        </Card>
        </Spot>
        <Spot id="markets.coins">
        <Section title={myCoins.length ? `Your coins · ${coins.length}` : `Coins Ananta watches · ${coins.length}`} right={
          <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}><T small>tap for the page · + to watch</T><VoiceBtn v={coinsVoice} /></View>} />
        <Card>
          <VoiceStrip id="markets.coins" />
          {coins.length === 0 ? <ListState state="empty" text="No coins yet." action={{ label: "+ Watch", onPress: () => setAdd(true) }} /> : null}
          {coins.map((c: any, i: number) => <View key={c.coin}>{i ? <Divider /> : null}<Spot id={`markets.coin:${c.coin}`}><CoinLine c={c} /></Spot></View>)}
        </Card>
        </Spot>
        <WholeMarket />
      </Spot>

      {ch?.coins?.length ? (
        <Spot id="markets.chain">
          <Section title="Ananta's reasoning" right={<T small>tap a coin for every step</T>} />
          <Card><Reasoning rows={ch.coins} /></Card>
        </Spot>
      ) : null}

      {near.length ? (
        <Spot id="markets.near">
          <Section title="Nearing a trade" right={<View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}><T small>closest to all conditions</T><VoiceBtn v={{
            id: "markets.near", label: "nearing a trade", back: "markets:markets", spot: "markets.near", screen: "markets",
            questions: [`What is ${COIN_NAME[near[0].coin] ?? near[0].coin} still missing?`, "Would you take any of these today?", "How do the conditions work?"],
            say: () => "These are the coins closest to a trade: how many of a setup's conditions each one meets right now. "
              + near.slice(0, 3).map((c: any) => `${COIN_NAME[c.coin] ?? c.coin}, ${c.closest.name}: ${c.closest.met} of ${c.closest.of}${c.closest.missing?.[0] ? `, still missing ${c.closest.missing[0]}` : ""}`).join(". ")
              + ". Close is not a trade: every condition has to pass, and the dial has to allow it." }} /></View>} />
          <Card>
            <VoiceStrip id="markets.near" />
            {near.map((c: any, i: number) => (
              <View key={c.coin}>
                {i ? <Divider /> : null}
                <Pressable onPress={() => router.push(`/coin/${c.coin}`)} style={{ paddingVertical: 9, gap: 5 }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                    <Text style={{ color: C.text, fontWeight: "700" }}>{COIN_NAME[c.coin] ?? c.coin} · <Text style={{ fontWeight: "400", color: C.dim }}>{c.closest.name}</Text></Text>
                    <Text style={{ color: C.dim, fontSize: 12 }}>{c.closest.met} of {c.closest.of}</Text>
                  </View>
                  <Progress value={c.closest.met} of={c.closest.of} color={c.closest.met === c.closest.of ? C.good : C.accent} />
                  {c.closest.missing?.length ? <Text style={{ color: C.faint, fontSize: 12 }} numberOfLines={1}>Still missing: {c.closest.missing[0]}</Text> : null}
                </Pressable>
              </View>
            ))}
          </Card>
        </Spot>
      ) : null}

      {rb ? (
        <Spot id="markets.reconstruction">
          <Card onPress={() => router.push("/reconstruction")} title="Reconstruction" right={<Text style={{ color: C.accent, fontSize: 18 }}>›</Text>}
            sub={`${rb.total} rebuilds · ${rb.mismatches} mismatch${rb.mismatches === 1 ? "" : "es"} · ${(rb.chain ?? []).length} findings · ${(rb.chain ?? []).filter((c: any) => /watch/i.test(`${c.step} ${c.what}`)).length} watch additions`} />
        </Spot>
      ) : null}
      <AddWatch open={add} onClose={() => setAdd(false)} kinds={w?.kinds ?? []} groups={w?.groups ?? {}} coins={(d.coins ?? []).map((c: any) => c.coin)}
        onDone={() => { setAdd(false); reloadW(); }} />
    </Screen>
  );
}

function WatchRow({ w, reload, glow }: { w: any; reload: () => void; glow?: boolean }) {
  const who = w.group ? ({ my_coins: "My coins", all: "All 10 coins", large: "The large coins" } as any)[w.group] ?? w.group
    : w.coins.map((c: string) => COIN_NAME[c] ?? c).join(", ");
  const st = STATE[w.state] ?? [w.state, "dim"];
  const close = w.detail?.met && w.detail?.of ? ` · ${w.detail.met} of ${w.detail.of}` : "";
  const mode = async () => { await api(`/v3/watches/mine/${w.id}`, { mode: NEXT_MODE[w.mode] }); showToast(`Now: ${MODE[NEXT_MODE[w.mode]]}`); reload(); };
  const stop = async () => { await api(`/v3/watches/mine/${w.id}`, { state: "DELETED" }); showToast("Watch removed ✓"); reload(); };
  return (
    <View style={{ paddingVertical: 10, gap: 4, ...(glow ? { backgroundColor: C.accentSoft, borderRadius: 12, paddingHorizontal: 10, borderWidth: 2, borderColor: C.accent } : {}) }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        {glow ? <Text style={{ color: C.accent, fontSize: 11, fontWeight: "800" }}>NEW</Text> : null}
        <Text style={{ color: C.text, fontWeight: "600", fontSize: 15, flex: 1 }}>{who}</Text>
        <Text style={{ color: (C as any)[st[1]] ?? C.dim, fontSize: 13, fontWeight: "600" }}>{st[0]}{close}</Text>
      </View>
      <T small>{w.kind_name}</T>
      <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
        <Tag text={`${MODE[w.mode] ?? w.mode} ⇄`} on onPress={mode} />
        <View style={{ flex: 1 }} />
        <Act label="Remove" color={C.dim} onPress={stop} />
      </View>
    </View>
  );
}

// one simple line per coin; a tap shows the whole chain
function Reasoning({ rows }: { rows: any[] }) {
  const [open, setOpen] = useState<any>(null);
  return (
    <>
      {rows.map((r: any, i: number) => (
        <View key={r.coin}>
          {i ? <Divider /> : null}
          <Pressable onPress={() => setOpen(r)} delayLongPress={350}
            onLongPress={() => askAbout({ screen: "markets", label: `Decision chain for ${r.coin}: ${r.summary}` }, `Why does ${r.coin} stop where it does?`)}
            style={{ flexDirection: "row", gap: 10, paddingVertical: 9, alignItems: "center" }}>
            <Text style={{ color: C.text, fontWeight: "700", width: 46 }}>{r.coin}</Text>
            <Text style={{ color: r.verdict === "NO TRADE" ? C.dim : C.good, fontSize: 13, flex: 1 }} numberOfLines={2}>{plainLine(r)}</Text>
            <Text style={{ color: C.faint, fontSize: 16 }}>›</Text>
          </Pressable>
        </View>
      ))}
      <ExplainSheet open={!!open} onClose={() => setOpen(null)} title={open ? `${COIN_NAME[open.coin] ?? open.coin}: every step` : ""}>
        {open ? <ChainLadder row={open} /> : null}
        {open ? <Btn label={`Open ${COIN_NAME[open.coin] ?? open.coin}`} kind="secondary" onPress={() => { const c = open.coin; setOpen(null); router.push(`/coin/${c}`); }} /> : null}
      </ExplainSheet>
    </>
  );
}

const WAIT: Record<string, string> = {
  REGIME: "Waiting for Bitcoin's market rule to open", TREND: "Waiting for its own uptrend", LOCATION: "Waiting for a price at a zone",
  TRIGGER: "Waiting for a setup to complete", INVALIDATION: "No clear place it would be wrong yet", RISK: "Can't be sized sensibly yet",
  EXPOSURE: "Would add to bets already held",
};
function plainLine(r: any): string {
  const g = (r.gates ?? []).find((x: any) => x.status === "FAIL");
  if (!g) return r.verdict === "NO TRADE" ? r.summary : "Every step passes: a trade is possible.";
  return `${WAIT[g.gate] ?? String(g.question).replace(/\?$/, "")}: ${g.why}`;
}

function AddWatch({ open, onClose, kinds, groups, coins, onDone }: { open: boolean; onClose: () => void; kinds: any[]; groups: Record<string, string>; coins: string[]; onDone: () => void }) {
  const [pick, setPick] = useState<string[]>([]);
  const [grp, setGrp] = useState<string | null>(null);
  const [kind, setKind] = useState<string | null>(null);
  const [mode, setMode] = useState("ask");
  const k = kind ?? kinds.find((x) => x.default)?.kind ?? kinds[0]?.kind;
  const save = async () => {
    try {
      await api("/v3/watches/mine", { coins: grp ? null : pick, group: grp, kind: k, mode });
      showToast("Watch added ✓");
      setPick([]); setGrp(null);
      onDone();
    } catch (e: any) { showToast(e?.message ?? "Could not add it"); }
  };
  const chip = (on: boolean, label: string, press: () => void) => (
    <Pressable key={label} onPress={press} style={{ borderRadius: 999, paddingHorizontal: 11, paddingVertical: 6, borderWidth: 1,
      borderColor: on ? C.accent : C.line, backgroundColor: on ? C.accentSoft : C.card }}>
      <Text style={{ color: on ? C.accent : C.text, fontWeight: "600", fontSize: 13 }}>{label}</Text>
    </Pressable>
  );
  return (
    <ExplainSheet open={open} onClose={onClose} title="Watch for me">
      <T dim small>Which coins?</T>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {Object.entries(groups).map(([g, l]) => chip(grp === g, String(l).split(" (")[0], () => { setGrp(grp === g ? null : g); setPick([]); }))}
      </View>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {coins.map((c) => chip(!grp && pick.includes(c), COIN_NAME[c] ?? c, () => { setGrp(null); setPick(pick.includes(c) ? pick.filter((x) => x !== c) : [...pick, c]); }))}
      </View>
      <T dim small>For what?</T>
      {kinds.map((x) => (
        <Pressable key={x.kind} onPress={() => setKind(x.kind)} style={{ borderRadius: 12, borderWidth: 1, borderColor: k === x.kind ? C.accent : C.line,
          backgroundColor: k === x.kind ? C.accentSoft : C.card, padding: 10, gap: 2 }}>
          <Text style={{ color: k === x.kind ? C.accent : C.text, fontWeight: "700" }}>{x.name}{x.default ? "  ·  best evidence so far" : ""}</Text>
          <Text style={{ color: C.dim, fontSize: 12 }}>{x.plain}</Text>
        </Pressable>
      ))}
      <T dim small>When it comes?</T>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {Object.entries(MODE).map(([m, l]) => chip(mode === m, l, () => setMode(m)))}
      </View>
      <Btn label="Start watching" onPress={save} />
    </ExplainSheet>
  );
}
