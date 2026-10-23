// Books › Trades (plan 3.3a, D8), redrawn Oct 14 to one grammar: one card on top (title · one number · one line · one action), then
// Open and Closed as plain rows (coin · rule, one fact line, the result), three closed rows then Show all. For the account (the $500
// NDAX book, in C$) the number is the net result since the start and Rules › explains how it trades; for the lab (US$) the filter chips
// say who took each trade. Same shape for Madhav and a visitor.
import React, { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { askAbout } from "./context";
import { ExplainSheet } from "./blocks";
import { C, pnlColor } from "./theme";
import { Act, Btn, Card, Divider, Expand, ListState, Section, Stat, StatCard, T, Tag, dayOf, money, moneySigned, pct, price, s as st, usdSigned, when } from "./ui";
import { sayMoney, upDown, type VoiceSpec } from "./sectionvoice";
import { W } from "./market";

const openTrade = (t: any) => router.push(t.link ?? `/story/${encodeURIComponent(t.id)}`);
const tm = (v: any) => (/^\d{4}-\d{2}-\d{2}$/.test(String(v)) ? dayOf(String(v)) : when(v));

// `voice` (Oct 16): the section voice button on the top card; what Ananta says is built here from the same numbers the card shows
export function BooksTrades({ d, explainers, title, voice }: { d: any; explainers?: React.ReactNode; title?: string; voice?: Omit<VoiceSpec, "say"> }) {
  const [showAll, setShowAll] = useState(false);
  const [only, setOnly] = useState<string>("all");
  const [rules, setRules] = useState(false);
  const s = d.summary ?? {};
  const acct = d.currency === "CAD";
  const M = money(d.currency), S = moneySigned(d.currency);
  const open: any[] = d.trades ?? [], closed: any[] = d.closed ?? [];
  const stamps = Array.from(new Set([...open, ...closed].map((t) => t.stamp?.label?.split(" · ")[0]).filter(Boolean))) as string[];
  const filt = (l: any[]) => l.filter((t) => only === "all" || (only === "mine" ? t.stamp?.who === "you" : only === "ananta" ? t.stamp?.who === "ananta"
    : t.stamp?.label?.startsWith(only)));
  const gain = (s.value ?? 0) - (s.start ?? 0);
  const ex = s.execution_check;
  const fo = filt(open), fc = filt(closed);
  const shownClosed = showAll ? fc : fc.slice(0, 3);
  const ccy = acct ? "CAD" : "USD";
  const vs: VoiceSpec | undefined = !voice ? undefined : acct ? {
    questions: [gain < 0 ? "Why is the account down?" : "Why is the account up?", "What does inside the bid and ask mean?", "How many fills until a verdict?", "What are the account's rules?"],
    ...voice,
    say: () => `This is the account's record: the 500 dollar NDAX book, in Canadian dollars. Net since ${dayOf(s.since) || "the start"}: ${upDown(gain)} ${sayMoney(gain, ccy)}.`
      + ` ${s.closed_count ?? closed.length} closed trade${(s.closed_count ?? closed.length) === 1 ? "" : "s"}, ${s.won_count ?? 0} won, ${open.length} open.`
      + (ex ? ` ${ex.inside_bid_ask} of ${ex.fills} paper fills were inside NDAX's real bid and ask, the check that the paper fills are honest.` : "")
      + " Tap Rules to see how it trades." } : {
    questions: ["Why are the lab's books down since the start?", "Which book is doing best?", "What does measuring in the background mean?"],
    ...voice,
    say: () => `These are the lab's paper books, in US dollars. Together they are worth ${sayMoney(s.value, ccy)}, ${upDown(gain)} ${sayMoney(gain, ccy)} since they started,`
      + ` with ${open.length} open trade${open.length === 1 ? "" : "s"}${s.open_pnl != null ? `, ${upDown(s.open_pnl)} ${sayMoney(s.open_pnl, ccy)} on those` : ""}.`
      + " They measure every strategy in the background, and they never touch the account." };
  return (
    <View style={{ gap: 12 }}>
      {acct ? (
        <StatCard voice={vs} title={W().account_title} label="Account summary"
          value={s.value == null ? "…" : S(gain)} valueColor={pnlColor(gain)} aside={`net since ${dayOf(s.since) || "the start"}`}
          line={`${s.closed_count ?? closed.length} closed · ${s.won_count ?? 0} won · ${open.length} open${ex ? ` · ${ex.inside_bid_ask} of ${ex.fills} fills inside the bid/ask` : ""}`}
          meta={`Worth ${M(s.value)} · started with ${M(s.start, 0)}`} action={{ label: "Rules ›", onPress: () => setRules(true) }} />
      ) : (
        <StatCard voice={vs} title={title ?? (d.read === "Your own practice trades." ? "Your practice book · paper money" : "The lab's paper books · US$")} label="Books summary"
          value={s.value == null ? "…" : M(s.value)} aside={`${S(gain)} since start`} asideColor={pnlColor(gain)}
          line={`${open.length} open · open result ${S(s.open_pnl ?? 0)} · closed recently ${S(s.closed_pnl_recent ?? 0)}`}
          meta={d.read === "Your own practice trades." ? "Paper money; nothing here is real" : "Measuring in the background; never the account"} />
      )}
      {d.retired?.length ? (
        <Card>
          <Expand title={`Retired strategies · ${usdSigned(s.retired_pnl)} since start · kept as evidence`}>
            {d.retired.map((b: any) => (
              <View key={b.name} style={{ gap: 2, paddingVertical: 6 }}>
                <View style={st.row}>
                  <T>{b.name} · {b.status === "PARKED" ? "parked" : "retired"}</T>
                  <Text style={[st.rowTitle, st.num, { color: pnlColor((b.value ?? 0) - (b.start ?? 0)) }]}>{usdSigned((b.value ?? 0) - (b.start ?? 0))}</Text>
                </View>
                <T small>{b.why}</T>
              </View>
            ))}
            {s.evidence_open ? <T small>Plus {s.evidence_open} measuring rows (zone touches, your setups on the universe, random baselines): evidence, never holdings. See Evidence.</T> : null}
          </Expand>
        </Card>
      ) : null}

      {!acct && stamps.length > 1 ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {[["all", "All"], ["mine", "Only mine"], ["ananta", "Only Ananta's"], ...stamps.map((x) => [x, x])].map(([k, l]) => (
            <Tag key={k} text={l} on={only === k} onPress={() => setOnly(k)} />
          ))}
        </View>
      ) : null}

      <Section title={`Open · ${fo.length}`} right={<T small>{acct ? W().marked_at : "Marked at the last price"}</T>} />
      <Card>
        {fo.length === 0 ? <ListState state="empty" text={acct ? "No open trades. The next decision comes at the daily close." : "No open trades here."} /> : null}
        {fo.map((t, i) => <View key={`${t.id}`}>{i ? <Divider /> : null}<TradeRow t={t} ccy={d.currency} /></View>)}
      </Card>

      <Section title={`Closed · ${fc.length}`} right={fc.length > 3 ? <Act tight label={showAll ? "Show less" : `Show all ${fc.length} ›`} onPress={() => setShowAll(!showAll)} /> : undefined} />
      <Card>
        {fc.length === 0 ? <ListState state="empty" text="No closed trades yet." /> : null}
        {shownClosed.map((t, i) => <View key={`${t.id}`}>{i ? <Divider /> : null}<TradeRow t={t} closed ccy={d.currency} /></View>)}
      </Card>

      {acct ? <T faint>The lab's paper books are in US$ and live under Details › Lab. They never touch the account.</T> : null}
      {explainers}
      <ExplainSheet open={rules} onClose={() => setRules(false)} title="How the account trades">
        <T>Paper money at NDAX's real bid and ask, in Canadian dollars, from a $500 start. Every fill is checked against the quote it was marked at.</T>
        <T>The core follows the trend dial: when Bitcoin closes above its 50-day and 200-day averages the dial is OPEN and the core basket is held; when it closes below, the core goes to cash.</T>
        <T>The edge sleeve buys deep pullbacks (the rule that passed its test) on the most-traded NDAX coins while the dial is closed (out when RSI(10) closes over 40, or after 10 days), and any rule you step up to promoted once it has a passing measured cell. The judgment sleeve mirrors the brain's buys on NDAX coins.</T>
        <T>Stops sit 6 ATR below the entry on NDAX prices; every entry is sized by the audit. Brakes: a 2% day or a 4% week stops new buys; four losses in a row pause it for a week; a 15% fall from the peak pauses it until you resume.</T>
        <Btn label="Ask Ananta about the rules" onPress={() => { setRules(false); askAbout({ screen: "books", label: "the $500 book's rules" }, "Explain how the $500 NDAX book trades: the dial, the core, the edge sleeve, the stops and the brakes."); }} />
      </ExplainSheet>
    </View>
  );
}

// One row for an open or a closed trade: coin · rule (or who took it), one fact line, the result and its percent.
function TradeRow({ t, closed, ccy }: { t: any; closed?: boolean; ccy?: string }) {
  const res = closed ? t.net_usd : t.pnl_usd;
  const S = moneySigned(ccy);
  const who: string = t.stamp?.label ?? "";
  const tag = t.rule ? String(t.rule) : t.sleeve ? String(t.sleeve).toLowerCase() : who.split(" · ").slice(-1)[0] ?? "";
  const sub = closed
    ? [t.time ? tm(t.time) : null, t.exit ?? null, t.why ?? null].filter(Boolean).join(" · ")
    : [t.entry ? `Bought ${price(t.entry, ccy)}` : null, t.now ? `now ${price(t.now, ccy)}` : null, t.stop ? `stop ${price(t.stop, ccy)}` : null,
      t.since ? `since ${tm(t.since)}` : null].filter(Boolean).join(" · ");
  return (
    <Pressable onPress={() => openTrade(t)} delayLongPress={350}
      onLongPress={() => askAbout({ screen: "trade", id: t.id, coin: t.coin, label: `${t.coin} trade (${who})` }, `How is this ${t.coin} trade doing?`)}
      style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 10, minHeight: 56, paddingVertical: 8, opacity: pressed ? 0.6 : 1 })}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={st.rowTitle} numberOfLines={1}>
          {t.coin}
          {tag ? <Text style={{ color: C.dim, fontWeight: "400" }}> · {tag}</Text> : null}
          {t.stamp?.who === "you" ? <Text style={{ color: C.dim, fontWeight: "400" }}> · you</Text> : null}
        </Text>
        {sub ? <T small numberOfLines={1}>{sub}</T> : null}
      </View>
      <View style={{ alignItems: "flex-end", gap: 2 }}>
        <Text style={[st.rowTitle, st.num, { color: pnlColor(res) }]}>{res == null ? "–" : S(res)}</Text>
        {!closed && t.pnl_pct != null ? <Text style={[st.small, st.num]}>{pct(t.pnl_pct)}</Text> : null}
      </View>
      <Text style={{ color: C.dim, fontSize: 18 }}>›</Text>
    </Pressable>
  );
}

// the two explainers at the bottom (Madhav's trend portfolio rule and the compare against its automatic copy)
export function Explainers({ h }: { h: any }) {
  if (!h) return null;
  return (
    <Card>
      <Expand title="How this portfolio works" sub="Who takes trades here, and the trend rule">
        <T>Every trade in this list carries a stamp. Ananta's trades say which rule or sleeve took them: the 15-minute Explorer, the hourly watch, the daily watches, Ananta's own picks
          or the trend portfolio. "You" means you placed it; Ananta watches those and warns you, but never closes them without your yes.</T>
        {h.rule_plain ? <T>The trend portfolio: {h.rule_plain}</T> : null}
        <T small>Ratings: Strong = leading the group; Steady = middle; Weak = lagging, first to go if the trend breaks.</T>
      </Expand>
      <Divider />
      <Expand title="Compare" sub="The trend portfolio against its automatic copy">
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Stat label="Your book" value={pct(h.return_pct)} color={pnlColor(h.return_pct)} />
          {h.shadow ? <Stat label="Automatic copy" value={pct(h.shadow.return_pct)} color={pnlColor(h.shadow.return_pct)} /> : null}
        </View>
        <T small>The automatic copy follows the rule at once. A gap shows what waiting for approvals cost or saved.</T>
      </Expand>
    </Card>
  );
}
