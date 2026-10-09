import { Spot } from "../../src/spotlight";
import { useCallback, useState } from "react";
import { Alert, Pressable, Switch, Text, View } from "react-native";
import { router, useFocusEffect, useLocalSearchParams } from "expo-router";
import { useEffect } from "react";
import { askAbout, setScreen } from "../../src/context";
import { api } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { LineChart, StackBar } from "../../src/charts";
import { Big, Btn, Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Row, Screen, Section, Segmented, Stat, T, pct, price, usd, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, COIN_NAME, pnlColor, ratingColor, ratingWord } from "../../src/theme";
import { VisitorBooks, useMe } from "../../src/visitor";

const RANGES = [{ key: "1", label: "1D" }, { key: "7", label: "1W" }, { key: "30", label: "1M" }, { key: "365", label: "All" }];

export default function Portfolio() {
  const me = useMe();
  if (!me) return <Busy />;
  if (me.guest) return <GuestBooks />;
  return <OwnerBooks />;
}

// A visitor's Books: their own practice book only (no Ananta book, no Explorer, no trend portfolio).
function GuestBooks() {
  const { data: d, err, loading, reload } = useData("/v3/holdings", 30000);
  useFocusEffect(useCallback(() => { setScreen({ screen: "manual_book", tab: "mine", label: "Books tab: your practice book" }); reload(); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  return <VisitorBooks d={d} loading={loading} reload={reload} />;
}

function OwnerBooks() {
  const [tab, setTab] = useState("portfolio");
  const p = useLocalSearchParams<{ tab?: string; t?: string }>();
  useEffect(() => { if (p.tab) setTab(String(p.tab)); }, [p.tab, p.t]);
  useFocusEffect(useCallback(() => { setScreen({ screen: tab === "portfolio" ? "portfolio" : tab === "explorer" ? "explorer_trades" : "manual_book", tab, label: tab === "portfolio" ? "Portfolio tab: trend portfolio" : tab === "explorer" ? "Portfolio tab: Explorer trades" : "Portfolio tab: My trades (manual paper book)" }); }, [tab]));
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <JarvisRow />
      <View style={{ paddingHorizontal: 16, paddingTop: 8, paddingBottom: 4 }}>
        <Segmented value={tab} onChange={setTab} options={[{ key: "portfolio", label: "Portfolio" }, { key: "explorer", label: "Explorer" }, { key: "mine", label: "My trades" }]} />
      </View>
      {tab === "portfolio" ? <Book /> : tab === "explorer" ? <Trades /> : <Mine />}
    </View>
  );
}

// Ananta's own book sits above the others: one line, tap for the full book.
function JarvisRow() {
  const { data: b } = useData("/v3/brain", 120000);
  const open = b?.open ?? [];
  return (
    <Pressable onPress={() => router.push("/jarvis")} accessibilityRole="button"
      style={{ marginHorizontal: 16, marginTop: 10, backgroundColor: C.card, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12, flexDirection: "row", alignItems: "center" }}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 15 }}>Ananta's book</Text>
        <Text style={{ color: C.dim, fontSize: 13 }}>{open.length} open · {b ? `${b.events} of 10 events · ${b.verdict}` : "loading"}</Text>
      </View>
      <Text style={{ color: C.accent, fontSize: 18 }}>›</Text>
    </Pressable>
  );
}

function Book() {
  const { data: d, err, loading, reload } = useData("/v3/holdings");
  const [range, setRange] = useState("30");
  const { data: h } = useData(`/history?days=${range}`);
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  const auto = d.mode === "AUTO";
  const gain = d.value - d.start;
  const toggle = async (on: boolean) => {
    if (on) {
      const ok = await confirmWithFaceId("Turn on autopilot?", "The portfolio will buy and sell (paper) by itself at each daily check, without asking you.");
      if (!ok) return;
    }
    try {
      await api("/portfolio/mode", { mode: on ? "AUTO" : "SUGGEST", confirm: true });
    } catch (e: any) {
      Alert.alert("Could not change mode", e?.message ?? String(e));
    }
    reload();
  };
  const act = async (kind: "approve" | "reject") => {
    if (kind === "approve" && !(await confirmWithFaceId("Approve changes", "Make these paper trades now?"))) return;
    await api(`/portfolio/${kind}`, { ids: "all" });
    reload();
  };
  const pts = (h?.points ?? []).map((p: any) => p.main);
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="portfolio.value">
      <Big label="Portfolio value (paper)" value={usd(d.value)} change={gain}
        changeLabel={`${usdSigned(gain)} (${pct(d.return_pct)}) since start`} />
      <LineChart height={150} showAxis={false} series={[{ data: pts, color: gain >= 0 ? C.good : C.bad, fill: true }]} />
      </Spot>
      <Segmented value={range} onChange={setRange} options={RANGES} />

      <Spot id="portfolio.autopilot">
      <Card>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
          <View style={{ flex: 1 }}>
            <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Autopilot</Text>
            <T small>{auto ? "On: rebalances by itself" : "Off: suggests changes and waits for you"}</T>
          </View>
          <Switch value={auto} onValueChange={toggle} trackColor={{ true: C.accent, false: C.line }} />
        </View>
      </Card>
      </Spot>

      {d.pending.length ? (
        <Spot id="portfolio.suggested">
        <Card title="Suggested changes" sub={`${d.pending.length} waiting for you`}>
          {d.pending.map((p: any) => (
            <T key={p.id}>• {p.action === "REBALANCE" ? "Rebalance to equal weights" : `${p.action === "ENTER" ? "Buy" : p.action === "EXIT" ? "Sell" : p.action} ${p.coin ?? ""}`} — {(p.why ?? []).join("; ")}</T>
          ))}
          <View style={{ flexDirection: "row", gap: 10, marginTop: 6 }}>
            <View style={{ flex: 1 }}><Btn label="Reject" kind="secondary" onPress={() => act("reject")} /></View>
            <View style={{ flex: 1 }}><Btn label="Approve" onPress={() => act("approve")} /></View>
          </View>
        </Card>
        </Spot>
      ) : null}

      <Spot id="portfolio.holdings">
      <Section title={`Holdings · ${d.holdings.length}`} right={<T small>value · total return</T>} />
      </Spot>
      <Card>
        <StackBar parts={[...d.holdings.map((r: any, i: number) => ({ label: r.coin, value: r.value, color: C.shades[i] ?? C.line })),
          { label: "Cash", value: d.cash, color: C.card2 }]} />
        {d.holdings.map((r: any) => (
          <View key={r.coin}>
            <Divider />
            <Spot id={`portfolio.holding:${r.coin}`}>
            <Row title={r.coin} sub={`${COIN_NAME[r.coin] ?? ""} · ${r.weight_pct}% · `} onPress={() => router.push(`/coin/${r.coin}`)}
              onLongPress={() => askAbout({ screen: "holding", coin: r.coin, label: `${r.coin} in the portfolio` }, `How is my ${r.coin} holding doing, and why is it rated ${ratingWord[r.rating] ?? r.rating}?`)}
              value={usd(r.value)} valueSub={`${usdSigned(r.pnl)} (${pct(r.pnl_pct)})`} valueSubColor={pnlColor(r.pnl)}
              left={<Pill text={ratingWord[r.rating] ?? r.rating} color={ratingColor[r.rating]} />} />
            </Spot>
          </View>
        ))}
        <Divider />
        <Line label="Cash" value={usd(d.cash)} />
        <Line label="Trading costs paid" value={usd(d.costs_paid)} />
      </Card>

      {d.not_held.length ? (
        <>
          <Section title="Watching (not held)" />
          <Card>
            {d.not_held.map((r: any, i: number) => (
              <View key={r.coin}>{i ? <Divider /> : null}<Row title={r.coin} sub={r.why} onPress={() => router.push(`/coin/${r.coin}`)} /></View>
            ))}
          </Card>
        </>
      ) : null}

      <Card>
        <Expand title="How this portfolio works" sub="The trend rule from repair-shop review #4">
          <T>{d.rule_plain}</T>
          <T small>Ratings: Strong = leading the group; Steady = middle; Weak = lagging, first to go if the trend breaks.</T>
        </Expand>
        <Divider />
        <Expand title="Compare" sub="Your book vs the automatic copy">
          <View style={{ flexDirection: "row", gap: 12 }}>
            <Stat label="Your book" value={pct(d.return_pct)} color={pnlColor(d.return_pct)} />
            <Stat label="Automatic copy" value={pct(d.shadow.return_pct)} color={pnlColor(d.shadow.return_pct)} />
          </View>
          <T small>The automatic copy always follows the rule at once. A gap shows the cost of waiting for approvals.</T>
        </Expand>
      </Card>
    </Screen>
  );
}

function Trades() {
  const { data: d, err, loading, reload } = useData("/v3/trades");
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  const total = d.value - d.start;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="explorer.value">
      <Big label="Explorer book (paper)" value={usd(d.value)} change={total} changeLabel={`${usdSigned(total)} since start`} />
      </Spot>
      <View style={{ flexDirection: "row", gap: 12 }}>
        <Stat label="Open P&L" value={usdSigned(d.unrealized)} color={pnlColor(d.unrealized)} />
        <Stat label="Closed P&L" value={usdSigned(d.realized)} color={pnlColor(d.realized)} />
        <Stat label="Open trades" value={d.open.length} />
      </View>
      <Section title="Open trades" right={<T small>$100 each</T>} />
      <Card>
        {d.open.length === 0 ? <T dim>No open trades.</T> : null}
        {d.open.map((t: any, i: number) => (
          <View key={t.id}>
            {i ? <Divider /> : null}
            <Spot id={`explorer.trade:${t.id}`}>
            <Row title={t.coin} sub={`${t.setup_name} · ${t.type_name}\nBought ${price(t.entry)} · ${t.since}`} onPress={() => router.push(`/trade/${t.id}`)}
              onLongPress={() => askAbout({ screen: "trade", id: t.id, coin: t.coin, label: `${t.coin} trade ${t.id}` }, `How is this ${t.coin} trade doing and what are we waiting for?`)}
              value={usdSigned(t.pnl_usd)} valueColor={pnlColor(t.pnl_usd)} valueSub={t.status} />
            </Spot>
          </View>
        ))}
      </Card>
      {d.pending.length ? (
        <>
          <Section title="Waiting to fill" />
          <Card>
            {d.pending.map((o: any, i: number) => (
              <View key={i}>{i ? <Divider /> : null}<Row title={o.coin} sub={`${o.setup_name} · limit ${price(o.limit)}`} valueSub={`until ${o.expires.slice(11, 16)} UTC`} /></View>
            ))}
          </Card>
        </>
      ) : null}
      <Spot id="explorer.closed">
      <Section title="Closed trades" />
      <Card>
        {d.closed.length === 0 ? <T dim>None yet. The first live-vs-history check needs 30.</T> : null}
        {d.closed.map((t: any, i: number) => (
          <View key={t.id}>
            {i ? <Divider /> : null}
            <Row title={t.coin} sub={`${t.exit} · ${t.time}`} onPress={() => router.push(`/trade/${t.id}`)} value={usdSigned(t.net_usd)} valueColor={pnlColor(t.net_usd)} />
          </View>
        ))}
      </Card>
      </Spot>
    </Screen>
  );
}

function Mine() {
  const { data: d, err, loading, reload } = useData("/v3/manual");
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  const gain = d.equity - d.start;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="mine.value">
      <Big label="My paper book" value={usd(d.equity)} change={gain} changeLabel={`${usdSigned(gain)} (${pct(d.return_pct)}) since start`} />
      </Spot>
      <T dim>Orders you ask Ananta for land here, separate from the agent's books, so your calls and the agent's can be compared. Paper only.</T>
      <View style={{ flexDirection: "row", gap: 12 }}>
        <Stat label="Cash" value={usd(d.cash)} />
        <Stat label="Closed P&L" value={usdSigned(d.realized)} color={pnlColor(d.realized)} />
        <Stat label="Costs" value={usd(d.costs)} />
      </View>
      <Section title="Positions" />
      <Card>
        {d.positions.length === 0 ? <T dim>None yet. Try asking Ananta: "buy $200 of ETH with a stop at 2,600".</T> : null}
        {d.positions.map((p: any, i: number) => (
          <View key={p.coin}>
            {i ? <Divider /> : null}
            <Spot id={`mine.position:${p.coin}`}>
            <Row title={p.coin} sub={[p.stop ? `stop ${price(p.stop)}` : null, p.target ? `target ${price(p.target)}` : null].filter(Boolean).join(" · ") || "no stop set"}
              value={usd(p.value)} valueSub={`${usdSigned(p.pnl)}`} valueSubColor={pnlColor(p.pnl)} onPress={() => router.push(`/coin/${p.coin}`)}
              onLongPress={() => askAbout({ screen: "manual_position", coin: p.coin, label: `my ${p.coin} paper position` }, `How is my ${p.coin} paper position doing?`)} />
            </Spot>
          </View>
        ))}
      </Card>
      <Section title="Orders and reasons" />
      <Card>
        {d.fills.length === 0 ? <T dim>No orders yet.</T> : null}
        {d.fills.map((f: any, i: number) => (
          <View key={f.id}>
            {i ? <Divider /> : null}
            <Line label={`${f.side === "BUY" ? "Bought" : "Sold"} ${f.coin} · ${new Date(f.t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`}
              value={`${usd(f.usd)} @ ${price(f.px)}`} sub={f.reason ? `“${f.reason}”` : f.trigger !== "owner" ? `automatic: ${f.trigger}` : undefined} />
          </View>
        ))}
      </Card>
      {d.jobs?.length ? (
        <>
          <Section title="Research jobs" />
          <Card>
            {d.jobs.map((jb: any) => (
              <Line key={jb.id} label={`${jb.kind} · ${new Date(jb.t * 1000).toLocaleTimeString(undefined, { hour: "numeric", minute: "2-digit" })}`}
                value={jb.status === "DONE" && jb.result?.match !== undefined ? (jb.result.match ? "✓ matches" : "✗ differs") : jb.status.toLowerCase()} />
            ))}
          </Card>
        </>
      ) : null}
    </Screen>
  );
}
