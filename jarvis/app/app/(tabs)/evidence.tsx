// Evidence, as one pipeline from top to bottom:
// 1 watching -> 2 seen -> 3 decided (or blocked, and why) -> 4 results vs random -> 5 rebuild and other traders
// -> 6 repair shop (why / question / result / change / status / progress) -> 7 in use.
// Everything comes from /v3/evidence/pipeline (live Explorer, ledger, nightly rebuild). Long-press any row to ask Ananta.
import { Spot } from "../../src/spotlight";
import { useCallback } from "react";
import { useFocusEffect } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { Text, View } from "react-native";
import { LineChart, Progress } from "../../src/charts";
import { Bullet, Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Screen, Stat, T, pct, usdSigned } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, pnlColor } from "../../src/theme";

const VERDICT: Record<string, [string, string, string]> = { PASS: ["PASSED", C.good, C.goodSoft], FAIL: ["NO CHANGE", C.dim, C.card2] };
const ask = (label: string, q: string) => askAbout({ screen: "evidence", label }, q);
const IDEA: Record<string, [string, string]> = {
  SUPPORTED: [C.good, C.goodSoft], PROMISING: [C.accent, C.accentSoft], POLICY: [C.text, C.card2],
  NOT_SUPPORTED: [C.bad, C.badSoft], REJECTED: [C.bad, C.badSoft], INSUFFICIENT: [C.warn, C.warnSoft],
};

export default function Evidence() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "evidence", label: "Evidence pipeline: watching, seen, decided, results, rebuild, repair shop, in use" }); }, []));
  const { data: d, err, loading, reload } = useData("/v3/evidence/pipeline");
  const { data: fw } = useData("/v3/evidence/forwarded");
  const { data: kh } = useData("/v3/knowledge/hypotheses");
  const { data: cr } = useData("/v3/credit", 600000);
  const { data: sh } = useData("/v3/shadow/h07", 600000);
  const { data: rq } = useData("/v3/requests", 120000);
  const { data: sb } = useData("/v3/scoreboard", 300000);
  if (!d && loading) return <Busy />;
  if (!d || d.error) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={d?.error ?? err ?? "No data"} /></Screen>;
  const R = d.results, D = d.decided;
  const seenTotal = d.seen.reduce((a: number, x: any) => a + x.seen, 0);
  const blockedTotal = D.blocked.reduce((a: number, x: any) => a + x.n, 0);
  return (
    <Screen loading={loading} onRefresh={reload}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <T small>Day {d.days} of paper trading · rules {d.rules}</T>
        <T small>as of {d.as_of}</T>
      </View>

      {/* 1 */}
      <Spot id="evidence.tracker">
      <Stage n={1} title="Watching" sub="what is running, how often" />
      <Card>
        {d.watching.map((w: any, i: number) => (
          <View key={w.name}>
            {i ? <Divider /> : null}
            <Expand title={w.name} sub={w.every} onLongPress={() => ask(`Watcher: ${w.name}`, `What does the ${w.name} do and what has it found so far?`)}
              right={<Text style={{ color: C.text, fontWeight: "700" }}>{w.runs != null ? `${w.runs.toLocaleString()} runs` : w.last ?? ""}</Text>}>
              <T>{w.detail}</T>
              {w.since ? <T small>since {w.since}</T> : null}
              {w.last ? <T small>last run {w.last}</T> : null}
            </Expand>
          </View>
        ))}
      </Card>
      </Spot>

      {/* 2 + 3 */}
      <Spot id="evidence.collected">
      <Stage n={2} title="Seen" sub={`${seenTotal} setups spotted`} />
      <Card>
        {d.seen.map((s: any, i: number) => (
          <View key={s.setup}>
            {i ? <Divider /> : null}
            <View style={{ flexDirection: "row", alignItems: "center", paddingVertical: 8, gap: 8 }}>
              <Text style={{ color: C.text, fontWeight: "700", width: 30 }}>{s.setup}</Text>
              <Text style={{ color: C.dim, flex: 1, fontSize: 13 }} numberOfLines={1}>{s.name}</Text>
              {s.traded ? <Pill text="TRADED" color={C.accent} /> : <Pill text="WATCH ONLY" />}
              <Text style={{ color: C.text, width: 40, textAlign: "right", fontWeight: "600" }}>{s.seen}</Text>
            </View>
          </View>
        ))}
      </Card>

      <Stage n={3} title="Decided" sub="placed, filled, or blocked and why" />
      <Card>
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Stat label="Real orders" value={D.real_orders} />
          <Stat label="Filled" value={D.filled} sub={`${D.missed} missed`} />
          <Stat label="Blocked" value={blockedTotal} />
        </View>
        <Divider />
        {D.blocked.map((b: any) => <Line key={b.code} label={b.why} value={String(b.n)} />)}
        <T small>Plus {D.random_baseline} random entries, tracked as the baseline every setup must beat.</T>
      </Card>
      </Spot>

      {/* 4 */}
      <Stage n={4} title="Results" sub="after costs, against random" />
      <Card>
        <ResultRow label="Real paper trades" s={R.real} extra={R.open_real ? `${R.open_real} still open` : undefined} />
        <Divider />
        <ResultRow label="Would-be trades" s={R.would_be} extra="a setup fitted; only a limit stopped it" />
        <Divider />
        <ResultRow label="Random entries" s={R.random} extra="the bar to beat" />
        {R.no_type?.closed ? (<><Divider /><ResultRow label="No trade type fitted" s={R.no_type} extra="should do worse; shows the filter works" /></>) : null}
        {R.since_wide ? (<><Divider /><ResultRow label="Real, since wide mode" s={R.since_wide} /></>) : null}
        {R.by_setup?.length ? (
          <Expand title="By setup" sub="real · would-be">
            {R.by_setup.map((x: any) => (
              <Line key={x.setup} label={`${x.setup} ${x.name}`}
                value={<Text style={{ color: C.text }}>{fmt(x.real)} · {fmt(x.would_be)}</Text>} />
            ))}
          </Expand>
        ) : null}
        <T small>{R.read_this}</T>
      </Card>

      {/* 4b: every watch, its own evidence book */}
      {sb?.watches?.length ? (
        <Spot id="evidence.scoreboard">
        <Card title="Scoreboard: every watch" sub={sb.headline}>
          {SECTION_ORDER.filter((s) => sb.watches.some((w: any) => w.section === s)).map((s) => (
            <View key={s} style={{ gap: 2 }}>
              <Text style={{ color: C.dim, fontSize: 11, fontWeight: "700", letterSpacing: 0.6, paddingTop: 6 }}>{SECTION_NAME[s] ?? s}</Text>
              {sb.watches.filter((w: any) => w.section === s).map((w: any) => (
                <Expand key={w.id} title={w.name}
                  sub={`${w.closed} closed · ${w.open} open${w.closed ? ` · ${Math.round(100 * (w.win_rate ?? 0))}% won` : ""} · ${w.events} event${w.events === 1 ? "" : "s"}`}
                  right={<Text style={{ color: w.avg_usd == null ? C.faint : pnlColor(w.avg_usd), fontWeight: "700" }}>{w.avg_usd == null ? "–" : usdSigned(w.avg_usd)}</Text>}
                  onLongPress={() => ask(`Watch: ${w.name}`, `How is the ${w.name} watch doing against random, and is that enough evidence yet?`)}>
                  <Line label="Net, all closed" value={usdSigned(w.net_usd)} />
                  <Line label={`Average vs random${w.baseline ? ` (${w.baseline.toLowerCase().replace("_", " ")})` : ""}`} value={w.vs_random_usd == null ? "–" : usdSigned(w.vs_random_usd)} />
                  <Line label="Worst run" value={usdSigned(w.worst_run_usd)} />
                  <Line label="Market allowed · risk-off" value={`${reg(w.by_regime?.ALLOWED)} · ${reg(w.by_regime?.RISK_OFF)}`} />
                  {w.real_closed !== w.closed ? <T small>{w.real_closed} real trades; the rest are signals a limit blocked, tracked the same way.</T> : null}
                  {w.costs ? <T small>Costs: {w.costs}</T> : null}
                  <T small>{w.verdict} · since {w.since}</T>
                </Expand>
              ))}
            </View>
          ))}
          {sb.trend_portfolio ? (
            <Line label="Trend portfolio (T3)" sub={`${sb.trend_portfolio.days ?? "–"} days`}
              value={`${pct(sb.trend_portfolio.return_pct)} vs buy-and-hold ${pct(sb.trend_portfolio.buy_hold_pct)}`} />
          ) : null}
          <T small>{sb.how_to_read}</T>
        </Card>
        </Spot>
      ) : null}

      {/* 5 */}
      <Stage n={5} title="Rebuild and other traders" sub="does the live log match a replay from raw candles?" />
      <Card>
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Stat label="Rebuild" value={d.rebuild.match == null ? "–" : d.rebuild.match ? "Match" : "Mismatch"} color={d.rebuild.match === false ? C.bad : d.rebuild.match ? C.good : undefined} />
          <Stat label="Real events checked" value={d.rebuild.real_events ?? 0} />
          <Stat label="Mismatches" value={d.rebuild.mismatches ?? 0} color={d.rebuild.mismatches ? C.bad : undefined} />
        </View>
        <T small>Every night the whole Explorer is replayed from raw candles. A mismatch would mean the live engine did something the rules don't explain; it would go straight to the repair shop.</T>
        {d.rebuild.studies.map((s: any) => (
          <View key={s.id}>
            <Divider />
            <Expand title={s.title} sub={`${s.date} · ${s.runs}`} onLongPress={() => ask(`Study ${s.id}: ${s.title}`, `What did the study of other traders show, and what did we do with it?`)}>
              <Line label="Accounts studied" value={`${s.accounts_sampled} (${s.excluded_bots} bots left out)`} />
              <Line label="Trading our coins" value={String(s.accounts_trading_our_coins)} />
              <Line label="Round trips" value={Number(s.round_trips).toLocaleString()} sub={s.period} />
              <Line label="Our setups were silent before their buys" value={`${s.our_setups_silent_before_their_buys_pct}%`} />
              <Line label="Their timing edge" value="" sub={s.their_timing_edge} />
              <Line label="Skill lasted over time" value={s.skill_persisted ? "yes" : "no"} />
              <Label>What we did</Label><T>{s.what_we_did}</T>
            </Expand>
          </View>
        ))}
      </Card>

      {/* 6 */}
      <Spot id="evidence.forwarded">
      <Stage n={6} title="Repair shop" sub="forwarded questions, tested on data the system never saw" />
      <Card>
        {d.shop.reviews.map((r: any, i: number) => (
          <View key={r.id}>
            {i ? <Divider /> : null}
            <Expand title={`#${r.id.slice(1)} ${r.title}`} sub={`${r.date} · ${r.status === "DONE" ? "done" : r.status?.toLowerCase()}`}
              onLongPress={() => askAbout({ screen: "review", id: r.id, label: `Repair-shop review ${r.id}: ${r.title}` }, `Explain review ${r.id} simply: why it was done and what it means for us.`)}
              right={<Pill text={VERDICT[r.verdict]?.[0] ?? r.verdict ?? ""} color={VERDICT[r.verdict]?.[1]} bg={VERDICT[r.verdict]?.[2]} />}>
              <Label>Why it was forwarded</Label><T>{r.forwarded_because}</T>
              <Label>Question tested</Label><T>{r.question}</T>
              <Label>Result</Label><T>{r.result}</T>
              <Label>What changed</Label><T>{r.changed}</T>
            </Expand>
          </View>
        ))}
      </Card>
      </Spot>
      <Spot id="evidence.shop">
      <Card title="Waiting for evidence">
        {d.shop.queue.map((q: any, i: number) => (
          <View key={q.id}>
            {i ? <Divider /> : null}
            <Expand title={q.title} sub={`${q.id} · waiting for ${q.waiting_for}`}
              onLongPress={() => ask(`Repair-shop question ${q.id}: ${q.title}`, `How close is ${q.title} to being tested, and what will it decide?`)}
              right={q.goal ? <Text style={{ color: C.text, fontWeight: "700" }}>{q.have ?? 0}<Text style={{ color: C.faint, fontWeight: "400" }}> / {q.goal}</Text></Text> : undefined}>
              <T>{q.why}</T>
              {q.note ? <T small>Counting {q.note}.</T> : null}
              {q.events != null ? <Line label="Independent market moves" value={String(q.events)} /> : null}
            </Expand>
            {q.goal ? <Progress value={Math.min(q.have ?? 0, q.goal)} of={q.goal} /> : null}
          </View>
        ))}
      </Card>
      </Spot>

      {rq?.requests?.length ? (
        <Card title="Your requests to the repair shop" sub={`${rq.requests.filter((r: any) => r.status === "OPEN" || r.status === "PLANNED").length} open · say "flag this" or "that was wrong" to Ananta; you get a phone note when one is fixed`}>
          {rq.requests.slice(0, 10).map((r: any) => (
            <View key={r.id} style={{ paddingVertical: 4 }}>
              <Text style={{ color: C.text, fontSize: 13 }}>{r.num ? <Text style={{ fontWeight: "700" }}>#{r.num} </Text> : null}{r.text}</Text>
              <Text style={{ color: r.status === "DONE" ? C.good : r.status === "PLANNED" ? C.accent : C.faint, fontSize: 11 }}>
                {r.kind.toUpperCase()} · {r.status === "DONE" ? "FIXED" : r.status}{r.about ? ` · ${r.about}` : ""}{r.note ? ` · ${r.note}` : ""}</Text>
            </View>
          ))}
        </Card>
      ) : null}

      {sh ? (
        <Card title="Paper shadow: short dip trade (H07)" sub={sh.history}>
          <T small>{sh.closed ? `${sh.closed} closed: ${sh.net_usd >= 0 ? "+" : "-"}$${Math.abs(sh.net_usd).toFixed(2)} on $100 each, ${Math.round(100 * (sh.win_rate ?? 0))}% won` : "No closed trades yet."}{sh.open ? ` · ${sh.open} open` : ""}{sh.waiting ? ` · ${sh.waiting} waiting for the next open` : ""}</T>
          {(sh.trades ?? []).slice(0, 5).map((t: any) => (
            <T key={t.id} small>{t.coin} {t.signal_day}: {t.status === "CLOSED" ? `${t.net_usd >= 0 ? "+" : "-"}$${Math.abs(t.net_usd).toFixed(2)} (${t.why})` : t.status.toLowerCase()}</T>
          ))}
          <T small>{sh.note}</T>
        </Card>
      ) : null}

      {cr ? (
        <Spot id="evidence.credit">
        <Card title="What each layer contributed" sub={cr.settled ? `${cr.settled} records scored (20 days after each close) since ${cr.since}` :
          `Recording every coin at each daily close since ${cr.since ?? "today"}; the first scores come 20 days later.`}>
          {(cr.by_signal ?? []).filter((x: any) => x.with_n || x.without_n).map((x: any) => (
            <View key={x.signal} style={{ flexDirection: "row", paddingVertical: 4, gap: 8 }}>
              <Text style={{ flex: 1, color: C.text, fontSize: 13 }}>{x.name}</Text>
              <Text style={{ color: x.diff_pts == null ? C.faint : x.diff_pts >= 0 ? C.good : C.bad, fontSize: 12 }}>
                {x.diff_pts == null ? `${x.with_n} / ${x.without_n} cases` : `${x.diff_pts > 0 ? "+" : ""}${x.diff_pts} pts (${x.with_n})`}</Text>
            </View>
          ))}
          {cr.explorer?.joined ? <T small>Explorer: {cr.explorer.joined} closed paper trades joined to what each layer said that day.</T> : null}
          <T small>{cr.note}</T>
        </Card>
        </Spot>
      ) : null}

      {kh?.hypotheses?.length ? (
        <Spot id="evidence.ideas">
        <Card title="Ideas from the teachers" sub="Rayner, Trade With Trend, your own trades: ideas until our data backs them">
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6, marginBottom: 6 }}>
            {Object.entries(kh.hypotheses.reduce((a: any, h: any) => ({ ...a, [h.status]: (a[h.status] ?? 0) + 1 }), {})).map(([k, v]: any) => (
              <Pill key={k} text={`${v} ${String(k).replace("_", " ").toLowerCase()}`} color={IDEA[k]?.[0] ?? C.dim} bg={IDEA[k]?.[1] ?? C.card2} />
            ))}
          </View>
          {kh.hypotheses.map((h: any, i: number) => (
            <View key={h.id}>
              {i ? <Divider /> : null}
              <Expand title={`${h.id} ${h.claim}`} sub={h.family}
                onLongPress={() => ask(`Teacher idea ${h.id}: ${h.claim}`, `What is idea ${h.id} and what did our data say about it?`)}
                right={<Pill text={String(h.status).replace("_", " ")} color={IDEA[h.status]?.[0] ?? C.dim} bg={IDEA[h.status]?.[1] ?? C.card2} />}>
                {h.evidence ? <><Label>What our data says</Label><T>{h.evidence}</T></> : <T small>Not measured yet.</T>}
                {h.used_as ? <><Label>Used as</Label><T>{h.used_as}</T></> : null}
                {h.next ? <><Label>Next</Label><T>{h.next}</T></> : null}
                <Label>From</Label><T small>{(h.sources ?? []).join(" · ")}</T>
              </Expand>
            </View>
          ))}
        </Card>
        </Spot>
      ) : null}

      {/* 7 */}
      <Spot id="evidence.in_use">
      <Stage n={7} title="In use" sub="what changed because of the evidence" />
      {d.in_use.modes.map((m: any) => (
        <Card key={m.id} title={`${m.id} · ${m.what}`} sub={`since ${m.since} · decided by ${m.decided_by}`}>
          <Label>Why</Label><T>{m.why}</T>
          <Label>Watch out</Label><T>{m.watch_out}</T>
        </Card>
      ))}
      {(fw?.in_use ?? d.in_use.repairs).map((x: any) => {
        const t = x.tracking ?? {};
        return (
          <Card key={x.id} title={`${x.id} · ${x.what}`} sub={`since ${x.since}`}>
            {t.series ? (
              <LineChart height={140} series={[
                { data: t.series.map((p: any) => p.main), color: C.accent, label: "your book" },
                { data: t.series.map((p: any) => p.shadow), color: C.faint, dashed: true, label: "automatic copy" },
              ]} />
            ) : null}
            <View style={{ flexDirection: "row", gap: 12 }}>
              <Stat label="Your book" value={pct(t.main_return_pct)} color={pnlColor(t.main_return_pct)} />
              <Stat label="Buy & hold" value={pct(t.buy_hold_return_pct)} color={pnlColor(t.buy_hold_return_pct)} />
              <Stat label="Trades" value={t.trades ?? "–"} sub={`${t.days ?? 0} days`} />
            </View>
            <Label>Expected</Label><T>{x.expect}</T>
            <Label>Watch out</Label><T>{x.watch_out}</T>
            <Label>So far</Label><T>{x.verdict_so_far}</T>
          </Card>
        );
      })}
      </Spot>
      <Spot id="evidence.safety">
      <Card title="Safety changes">
        {d.in_use.safety.map((s: any, i: number) => (
          <View key={i}>{i ? <Divider /> : null}<Line label={s.date} value="" sub={s.what} /></View>
        ))}
        {!d.in_use.safety.length ? <Bullet>None yet.</Bullet> : null}
      </Card>
      </Spot>
    </Screen>
  );
}

const fmt = (s: any) => (s?.closed ? `${s.closed}, ${usdSigned(s.avg_usd)}` : "–");
const SECTION_ORDER = ["MARKET_WEATHER", "COIN_STRUCTURE", "SETUPS", "RISK_EXITS", "NEWS_EVENTS", "BASELINES"];
const SECTION_NAME: Record<string, string> = { MARKET_WEATHER: "MARKET WEATHER", COIN_STRUCTURE: "COIN STRUCTURE AND ZONES", SETUPS: "SETUPS",
  RISK_EXITS: "RISK AND EXITS", NEWS_EVENTS: "NEWS AND EVENTS", BASELINES: "BASELINES (RANDOM, THE BAR TO BEAT)" };
const reg = (x: any) => (x?.closed ? `${x.closed}, ${usdSigned(x.avg_usd)}` : "–");

function ResultRow({ label, s, extra }: { label: string; s: any; extra?: string }) {
  const n = s?.closed ?? 0;
  return (
    <View style={{ paddingVertical: 8 }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <Text style={{ color: C.text, fontWeight: "600" }}>{label}</Text>
        <Text style={{ color: pnlColor(s?.net_usd), fontWeight: "700" }}>{n ? usdSigned(s.net_usd) : "–"}</Text>
      </View>
      <Text style={{ color: C.dim, fontSize: 12, marginTop: 2 }}>
        {n ? `${n} closed · ${s.wins} won · avg ${usdSigned(s.avg_usd)} · ${s.events} independent event${s.events === 1 ? "" : "s"}` : "none closed yet"}
        {extra ? ` · ${extra}` : ""}
      </Text>
    </View>
  );
}

function Stage({ n, title, sub }: { n: number; title: string; sub?: string }) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10, marginTop: 10 }}>
      <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: C.card2, alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: C.accent, fontWeight: "800", fontSize: 12 }}>{n}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 16 }}>{title}</Text>
        {sub ? <Text style={{ color: C.faint, fontSize: 12 }}>{sub}</Text> : null}
      </View>
    </View>
  );
}

const Label = ({ children }: { children: React.ReactNode }) => (
  <Text style={{ color: C.faint, fontSize: 11, fontWeight: "700", letterSpacing: 0.6, marginTop: 4 }}>{String(children).toUpperCase()}</Text>
);
