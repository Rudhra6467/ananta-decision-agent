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
