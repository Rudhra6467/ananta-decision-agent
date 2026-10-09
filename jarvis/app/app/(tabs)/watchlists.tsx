// Watchlists (plan 3.5, D9), for Madhav and visitors alike:
//  1. the watchlist: this account's watches (coins or a group, a setup kind, a mode, a state), with + to add one, and the coins
//  2. Ananta's reasoning: one simple line per coin; a tap shows the whole decision chain
//  3. Nearing a trade: coins closest to passing, with what is still missing
//  4. Reconstruction (Madhav only): counts under the title; a tap opens the reconstruction pages
// The Bitcoin box moved to Home (the market rule slide); zones and "Your setups" live on each coin's page and in Books › Details.
import { Spot } from "../../src/spotlight";
import { useCallback, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { api } from "../../src/api";
import { Progress } from "../../src/charts";
import { Btn, Busy, Card, Divider, ErrorBox, Screen, Section, T } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME } from "../../src/theme";
import { ChainLadder } from "../../src/chain";
import { ExplainSheet, showToast } from "../../src/blocks";
import { CoinLine } from "../../src/home";
import { useMe } from "../../src/visitor";

const MODE: Record<string, string> = { tell: "Tell me", ask: "Ask me first", auto: "Auto" };
const NEXT_MODE: Record<string, string> = { tell: "ask", ask: "auto", auto: "tell" };
const STATE: Record<string, [string, string]> = { WATCHING: ["Watching", "dim"], CLOSE: ["Getting close", "warn"], FIRED: ["Fired", "good"], PAUSED: ["Paused", "faint"] };

export default function Watchlists() {
  const me = useMe();
  const own = !!me && !me.guest;
  const { data: d, err, loading, reload } = useData(me ? "/v3/coins" : null, 60000);
  const { data: w, reload: reloadW } = useData(me ? "/v3/watches/mine" : null, 60000);
  const { data: ch } = useData(me ? "/v3/chain" : null, 300000);
  const { data: ev } = useData(own ? "/v3/evidence/live" : null, 600000);
  const [add, setAdd] = useState(false);
  const { glow } = useLocalSearchParams<{ glow?: string }>();          // Phase 5: the watch just made glows when Watchlists opens
  useFocusEffect(useCallback(() => { setScreen({ screen: "markets", label: "Watchlists tab: your watches, Ananta's reasoning, nearing a trade" }); reloadW(); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  const myCoins: string[] = me?.guest ? (me?.profile?.coins ?? []) : [];
  const coins = (d.coins ?? []).filter((c: any) => !myCoins.length || myCoins.includes(c.coin));
  const near = [...(d.coins ?? [])].filter((c: any) => c.closest).sort((a: any, b: any) => b.closest.met / b.closest.of - a.closest.met / a.closest.of).slice(0, 5);
  const rb = ev?.rebuild;
  return (
    <Screen loading={loading} onRefresh={() => { reload(); reloadW(); }}>
      <Spot id="markets.summary">
        <Section title="Watchlist" right={
          <Pressable onPress={() => setAdd(true)} accessibilityLabel="Add a watch" style={{ flexDirection: "row", alignItems: "center", gap: 4, backgroundColor: C.accent,
            borderRadius: 999, paddingHorizontal: 12, paddingVertical: 5 }}>
            <Text style={{ color: C.onInk, fontWeight: "800" }}>+ Watch</Text>
          </Pressable>} />
        <Card>
          {(w?.watches ?? []).length === 0 ? <T dim>No watches yet. Tap + Watch to have Ananta watch a coin or a group, and choose whether it tells you, asks you first or trades by itself.</T> : null}
          {(w?.watches ?? []).map((x: any, i: number) => <View key={x.id}>{i ? <Divider /> : null}<WatchRow w={x} reload={reloadW} glow={!!glow && glow === x.id} /></View>)}
        </Card>
        <Card title={myCoins.length ? "Your coins" : "Coins Ananta watches"} sub="tap for the trading page · + to watch or trade">
          {coins.map((c: any, i: number) => <View key={c.coin}>{i ? <Divider /> : null}<Spot id={`markets.coin:${c.coin}`}><CoinLine c={c} /></Spot></View>)}
        </Card>
      </Spot>

      {ch?.coins?.length ? (
        <Spot id="markets.chain">
          <Section title="Ananta's reasoning" right={<T small>tap a coin for every step</T>} />
          <Card><Reasoning rows={ch.coins} /></Card>
        </Spot>
      ) : null}

      {near.length ? (
        <Spot id="markets.near">
          <Section title="Nearing a trade" right={<T small>closest to all conditions</T>} />
          <Card>
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
    <View style={{ paddingVertical: 10, gap: 6, ...(glow ? { backgroundColor: C.accentSoft, borderRadius: 12, paddingHorizontal: 10, borderWidth: 2, borderColor: C.accent } : {}) }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        {glow ? <Text style={{ color: C.accent, fontSize: 11, fontWeight: "800" }}>NEW</Text> : null}
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 15, flex: 1 }}>{who}</Text>
        <Text style={{ color: (C as any)[st[1]], fontSize: 12, fontWeight: "700" }}>{st[0].toUpperCase()}{close}</Text>
      </View>
      <Text style={{ color: C.dim, fontSize: 13 }}>{w.kind_name}</Text>
      <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
        <Pressable onPress={mode} accessibilityLabel={`Mode ${MODE[w.mode]}; tap to change`} style={{ borderRadius: 999, borderWidth: 1, borderColor: C.accent,
          backgroundColor: C.accentSoft, paddingHorizontal: 10, paddingVertical: 4 }}>
          <Text style={{ color: C.accent, fontSize: 12, fontWeight: "700" }}>{MODE[w.mode] ?? w.mode} ⇄</Text>
        </Pressable>
        <View style={{ flex: 1 }} />
        <Text onPress={stop} style={{ color: C.bad, fontSize: 13, fontWeight: "600" }}>Remove</Text>
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
