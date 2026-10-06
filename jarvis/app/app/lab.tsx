// Evidence: inside the logic repair, live (Madhav, 2026-10-05: "redesign our evidence page based on these questions ... like
// seeing it live what's happening inside the logic repair"). His questions, in his order, each with live numbers:
//   the loop (looked -> spotted -> decided -> scored -> missed -> sent to the repair shop -> changed)
//   -> what is watching, how often -> what the limits stopped, and did it matter -> is any of it working (vs random)
//   -> reconstruction (rebuilds, other traders) -> what we missed -> the repair board -> what changed -> what we wait for.
// Everything comes from /v3/evidence/live. The older research cards (setups seen, scoreboard, teacher ideas, layer credit) fold
// below and open by themselves when Ananta points at one. Long-press a row to ask Ananta about it; tap a loop step to jump.
import { focusSpot, Spot, useSpotWanted } from "../src/spotlight";
import React, { useCallback, useEffect, useState } from "react";
import { router, Stack, useFocusEffect } from "expo-router";
import { useLab } from "../src/lab";
import { askAbout, setScreen } from "../src/context";
import { Pressable, Text, View } from "react-native";
import { Donut, Progress, SignedBars } from "../src/charts";
import { Busy, Card, Divider, ErrorBox, Expand, Line, Pill, Screen, Segmented, Stat, T, pct, usdSigned } from "../src/ui";
import { useData } from "../src/useData";
import { C, pnlColor } from "../src/theme";

const ask = (label: string, q: string) => askAbout({ screen: "evidence", label }, q);
const GROUP: Record<string, { word: string; color: string; soft: string }> = {
  you: { word: "Needs you", color: C.warn, soft: C.warnSoft }, us: { word: "In progress", color: C.accent, soft: C.accentSoft },
  evidence: { word: "Waiting for evidence", color: C.dim, soft: C.card2 }, done: { word: "Done", color: C.good, soft: C.goodSoft },
};
const MISS: Record<string, [string, string]> = { CAUGHT: ["Caught", C.good], SEEN: ["Seen", C.accent], MISSED: ["Missed", C.bad] };
const VERDICT: Record<string, [string, string, string]> = {
  PASS: ["PASSED", C.good, C.goodSoft], FAIL: ["NO CHANGE", C.dim, C.card2], INSUFFICIENT: ["NOT ENOUGH DATA", C.warn, C.warnSoft],
};
const KIND: Record<string, string> = { ticket: "Ticket", request: "Request", review: "Review", question: "Question" };
const LOOP_SPOT: Record<string, string> = { looked: "evidence.clocks", spotted: "evidence.collected", decided: "evidence.limits",
  scored: "evidence.collected", missed: "evidence.misses", forwarded: "evidence.forwarded", changed: "evidence.in_use" };
const FOLD_SPOTS = ["evidence.scoreboard", "evidence.ideas", "evidence.credit"];

export default function Evidence() {
  const [lab, setLab] = useLab();
  const head = <Stack.Screen options={{ headerShown: true, title: "Evidence", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
    headerTintColor: C.text, headerBackTitle: "Home" }} />;
  useFocusEffect(useCallback(() => { setScreen({ screen: "evidence", label: "Evidence: inside the logic repair, live (loop, watching, limits, results, reconstruction, misses, repair board, changes, waiting)" }); }, []));
  const { data: d, err, loading, reload } = useData("/v3/evidence/live", 60000);
  const [fold, setFold] = useState(false);
  const want = useSpotWanted(FOLD_SPOTS);
  useEffect(() => { if (want) setFold(true); }, [want]);
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen></>;
  return (
    <>{head}
    <Screen loading={loading} onRefresh={reload}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <T small>{d.days != null ? `Day ${d.days} of paper` : "Paper"}{d.since ? ` · since ${d.since}` : ""}{d.rules ? ` · rules ${d.rules}` : ""}</T>
        <T small>as of {d.as_of}</T>
      </View>
      {d.health ? <Health h={d.health} /> : null}
      {d.headline ? (
        <Card><Text style={{ color: C.text, fontSize: 16, lineHeight: 23, fontWeight: "600" }}>{d.headline}</Text></Card>
      ) : null}

      {d.gate ? <Spot id="evidence.gate"><Gate g={d.gate} /></Spot> : null}
      {d.loop ? <Spot id="evidence.tracker"><Loop loop={d.loop} /></Spot> : null}
      {d.clocks ? <Spot id="evidence.clocks"><Clocks clocks={d.clocks} /></Spot> : null}
      {d.limits ? <Spot id="evidence.limits"><Limits limits={d.limits} /></Spot> : null}
      {d.results ? <Spot id="evidence.collected"><Results r={d.results} /></Spot> : null}
      {d.rebuild ? <Spot id="evidence.rebuild"><Rebuild r={d.rebuild} /></Spot> : null}
      {d.misses ? <Spot id="evidence.misses"><Misses m={d.misses} /></Spot> : null}
      {d.board ? <Spot id="evidence.forwarded"><Board b={d.board} /></Spot> : null}
      {d.in_use ? <InUse u={d.in_use} /> : null}
      {d.waiting ? <Spot id="evidence.shop"><Waiting w={d.waiting} /></Spot> : null}

      <Pressable onPress={() => setFold(!fold)}>
        <Card title={fold ? "Hide the research detail" : "Research detail"} sub="Setups seen, every watch's scoreboard, the short dip trade's shadow book, layer credit, teacher ideas"
          right={<Text style={{ color: C.accent, fontSize: 16 }}>{fold ? "▲" : "▼"}</Text>} />
      </Pressable>
      {fold ? <Detail /> : null}
      {d.errors ? <T small>Some parts could not load: {Object.keys(d.errors).join(", ")}.</T> : null}
      {!lab ? <T small><Text onPress={() => setLab(true)} style={{ color: C.accent }}>Turn the Lab view on</Text> to keep this page one tap away on Home.</T> : null}
    </Screen>
    </>
  );
}

// ---------------------------------------------------------------------------
function Q({ n, q, a }: { n: number; q: string; a?: string }) {
  return (
    <View style={{ flexDirection: "row", gap: 10, marginTop: 6, marginBottom: 8 }}>
      <View style={{ width: 24, height: 24, borderRadius: 12, backgroundColor: C.accentSoft, alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: C.accent, fontWeight: "800", fontSize: 12 }}>{n}</Text>
      </View>
      <View style={{ flex: 1 }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 16 }}>{q}</Text>
        {a ? <Text style={{ color: C.dim, fontSize: 13, marginTop: 2, lineHeight: 18 }}>{a}</Text> : null}
      </View>
    </View>
  );
}

const Label = ({ children }: { children: React.ReactNode }) => (
  <Text style={{ color: C.faint, fontSize: 11, fontWeight: "700", letterSpacing: 0.6, marginTop: 4 }}>{String(children).toUpperCase()}</Text>
);

function Health({ h }: { h: any }) {
  const ok = !h.down?.length;
  return (
    <Card>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
        <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: ok ? C.good : C.bad }} />
        <Text style={{ color: C.text, fontWeight: "700", flex: 1 }}>{ok ? `All ${h.of} parts running` : `Down: ${h.down.join(", ")}`}</Text>
        <T small>{h.ok}/{h.of}</T>
      </View>
      {h.outages_3d?.length ? (
        <T small>Last 3 days: {h.outages_3d.map((o: any) => `${o.name} ${o.minutes >= 90 ? `${(o.minutes / 60).toFixed(1)} h` : `${o.minutes} min`}${o.still_down ? " (still down)" : ""}`).join(" · ")}</T>
      ) : <T small>No outage in the last 3 days.</T>}
    </Card>
  );
}

const GATE: Record<string, [string, string]> = {
  PASS: [C.good, C.goodSoft], FAIL: [C.bad, C.badSoft], PARTLY: [C.warn, C.warnSoft], PENDING: [C.accent, C.accentSoft], NOT_MEASURED: [C.dim, C.card2],
};

// The Engine Acceptance Gate (Madhav, Oct 6): the build is locked only when every check passes at once.
function Gate({ g }: { g: any }) {
  const [area, setArea] = useState<string | null>(null);
  return (
    <Card title="Is the engine ready?" sub={g.rule}>
      <View style={{ flexDirection: "row", alignItems: "baseline", gap: 8 }}>
        <Text style={{ color: C.text, fontSize: 28, fontWeight: "800" }}>{g.passed}</Text>
        <Text style={{ color: C.dim, fontSize: 15 }}>of {g.of} checks pass</Text>
      </View>
      <Progress value={g.passed} of={g.of} color={C.good} />
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {Object.entries(g.counts ?? {}).filter(([, v]: any) => v).map(([k, v]: any) => (
          <Pill key={k} text={`${v} ${String(k).replace("_", " ").toLowerCase()}`} color={GATE[k]?.[0] ?? C.dim} bg={GATE[k]?.[1] ?? C.card2} />
        ))}
      </View>
      {(g.areas ?? []).map((a: string) => {
        const cs = g.checks.filter((c: any) => c.area === a);
        const ok = cs.filter((c: any) => c.status === "PASS").length;
        return (
          <View key={a}>
            <Divider />
            <Pressable onPress={() => setArea(area === a ? null : a)} style={{ flexDirection: "row", alignItems: "center", paddingVertical: 9, gap: 10 }}>
              <Text style={{ color: C.text, fontWeight: "700", flex: 1 }}>{a}</Text>
              <View style={{ flexDirection: "row", gap: 3 }}>
                {cs.map((c: any) => <View key={c.id} style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: GATE[c.status]?.[0] ?? C.dim }} />)}
              </View>
              <Text style={{ color: C.dim, fontSize: 12, width: 34, textAlign: "right" }}>{ok}/{cs.length}</Text>
              <Text style={{ color: C.faint }}>{area === a ? "▲" : "▼"}</Text>
            </Pressable>
            {area === a ? cs.map((c: any) => (
              <View key={c.id} style={{ paddingVertical: 6, paddingLeft: 4, gap: 2 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                  <Text style={{ color: C.text, fontWeight: "600", flex: 1 }}>{c.check}</Text>
                  <Pill text={c.status_words.toUpperCase()} color={GATE[c.status]?.[0]} bg={GATE[c.status]?.[1]} />
                </View>
                <T small>Pass mark: {c.pass_mark}{c.note ? ` · ${c.note}` : ""}</T>
              </View>
            )) : null}
          </View>
        );
      })}
    </Card>
  );
}

function Loop({ loop }: { loop: any[] }) {
  return (
    <Card title="The repair loop, live" sub="From what we looked at to what we changed. Tap a step to jump to it.">
      {loop.map((s: any, i: number) => (
        <Pressable key={s.key} onPress={() => LOOP_SPOT[s.key] && focusSpot(LOOP_SPOT[s.key], 2500)}
          onLongPress={() => ask(`Loop step: ${s.label}`, `Explain the "${s.label}" step of our repair loop and what its number means.`)}
          style={({ pressed }) => ({ flexDirection: "row", gap: 12, opacity: pressed ? 0.6 : 1 })}>
          <View style={{ alignItems: "center", width: 22 }}>
            <View style={{ width: 22, height: 22, borderRadius: 11, backgroundColor: C.accent, alignItems: "center", justifyContent: "center", marginTop: 6 }}>
              <Text style={{ color: "#FFF", fontSize: 11, fontWeight: "800" }}>{i + 1}</Text>
            </View>
            {i < loop.length - 1 ? <View style={{ flex: 1, width: 2, backgroundColor: C.accentSoft, minHeight: 14 }} /> : null}
          </View>
          <View style={{ flex: 1, paddingVertical: 6 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}>
              <Text style={{ color: C.text, fontWeight: "700", fontSize: 15 }}>{s.label}</Text>
              <Text style={{ color: C.text, fontWeight: "800", fontSize: 20 }}>{Number(s.n ?? 0).toLocaleString()}</Text>
            </View>
            <Text style={{ color: C.dim, fontSize: 12, lineHeight: 17 }}>{s.sub}</Text>
          </View>
        </Pressable>
      ))}
    </Card>
  );
}

function Clocks({ clocks }: { clocks: any[] }) {
  return (
    <View>
      <Q n={1} q="What is watching, and how often?" a="One row per clock: how often it looks, what it covers, and how many looks so far." />
      <Card>
        {clocks.map((c: any, i: number) => (
          <View key={c.name}>
            {i ? <Divider /> : null}
            <Expand title={c.name} sub={c.scope}
              onLongPress={() => ask(`Clock: ${c.name}`, `What does the ${c.name} do, how often, and what has it found so far?`)}
              right={
                <View style={{ alignItems: "flex-end", gap: 2 }}>
                  <Pill text={c.cadence.toUpperCase()} color={C.accent} bg={C.accentSoft} />
                  {c.n != null ? <Text style={{ color: C.text, fontWeight: "700", fontSize: 13 }}>{Number(c.n).toLocaleString()} <Text style={{ color: C.faint, fontWeight: "400" }}>{c.unit}</Text></Text> : null}
                </View>
              }>
              <T>{c.detail}</T>
            </Expand>
          </View>
        ))}
      </Card>
    </View>
  );
}

function limitTag(l: any): [string, string, string] {
  const v = String(l.verdict || "");
  if (l.id === "SIZE") return ["DOLLARS, NOT EVIDENCE", C.dim, C.card2];
  if (v.startsWith("Never")) return ["NEVER REACHED", C.dim, C.card2];
  if (v.includes("not hiding")) return ["NOT HIDING WINNERS", C.good, C.goodSoft];
  if (v.includes("did better")) return ["WORTH WATCHING", C.warn, C.warnSoft];
  if (v.includes("not followed")) return ["NOT TRACKED", C.warn, C.warnSoft];
  return ["TOO EARLY", C.dim, C.card2];
}

function Limits({ limits }: { limits: any[] }) {
  const total = limits.reduce((a: number, l: any) => a + (l.stopped || 0), 0);
  return (
    <View>
      <Q n={2} q="What did the limits stop, and did it matter?"
        a={`${total.toLocaleString()} stops so far. The Explorer tracks every trade it stops, so we can see what it would have done; Jarvis's dropped wakes are not followed.`} />
      <Card>
        {limits.map((l: any, i: number) => {
          const t = limitTag(l);
          const a = l.after;
          return (
            <View key={`${l.id}${i}`}>
              {i ? <Divider /> : null}
              <Expand title={l.rule} sub={`${l.where}${l.stopped != null ? ` · stopped ${l.stopped}` : ""}`}
                onLongPress={() => ask(`Limit: ${l.rule}`, `What does the "${l.rule}" limit stop, and should we loosen it to get more evidence?`)}
                right={<Pill text={t[0]} color={t[1]} bg={t[2]} />}>
                <Line label="Setting" value="" sub={l.setting} />
                {l.why ? <Line label="Why it is there" value="" sub={l.why} /> : null}
                {a?.closed ? (
                  <Line label="What the stopped trades did" sub={`${a.closed} closed · ${a.wins} won · ${a.events} market event${a.events === 1 ? "" : "s"}`}
                    value={<Text style={{ color: pnlColor(a.avg_usd) }}>{usdSigned(a.avg_usd)} each</Text>} />
                ) : null}
                <T>{l.verdict}</T>
                {l.proposal ? (
                  <View style={{ backgroundColor: C.warnSoft, borderRadius: 10, padding: 10, gap: 4 }}>
                    <Text style={{ color: C.warn, fontWeight: "700", fontSize: 12 }}>{l.proposal.id} · {String(l.proposal.status || "").replace(/_/g, " ").toLowerCase()}</Text>
                    <Text style={{ color: C.text, fontSize: 13 }}>{l.proposal.change}</Text>
                  </View>
                ) : null}
              </Expand>
            </View>
          );
        })}
      </Card>
    </View>
  );
}

function Results({ r }: { r: any }) {
  const items = (r.items ?? []).map((x: any) => ({
    label: x.label, value: x.avg_usd, strong: x.key === "real" || x.key === "jarvis",
    sub: x.closed ? `${x.closed} closed${x.wins != null ? ` · ${x.wins} won` : ""} · ${x.events} event${x.events === 1 ? "" : "s"}${x.open ? ` · ${x.open} open` : ""}${x.twins_avg_usd != null ? ` · its random twins ${usdSigned(x.twins_avg_usd)}` : ""}`
      : `none closed yet${x.open ? ` · ${x.open} open` : ""}`,
  }));
  return (
    <View>
      <Q n={3} q="Is any of it working?" a={r.verdict} />
      <Card title="Average per $100 trade, after costs">
        <SignedBars items={items} mark={r.random_avg_usd != null ? { value: r.random_avg_usd, label: "random entries" } : null} fmt={usdSigned} />
        <View style={{ gap: 4, marginTop: 6 }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <T small>Separate market moves so far</T><T small>{r.events} of {r.goal_events} for a verdict</T>
          </View>
          <Progress value={Math.min(r.events, r.goal_events)} of={r.goal_events} />
        </View>
        {r.books?.length ? <Divider /> : null}
        {(r.books ?? []).map((b: any) => (
          b.pct != null ? (
            <Line key={b.key} label={b.label} sub={`${b.trades ?? 0} trades${b.days ? ` · ${b.days} days` : ""}`}
              value={<Text style={{ color: pnlColor(b.pct) }}>{pct(b.pct)}{b.vs_pct != null ? <Text style={{ color: C.dim }}>{` vs ${b.vs_label} ${pct(b.vs_pct)}`}</Text> : null}</Text>} />
          ) : (
            <Line key={b.key} label={b.label} sub={`${b.closed ?? 0} closed · ${b.open ?? 0} open`} value={b.closed ? usdSigned(b.net_usd) : "–"} />
          )
        ))}
        {r.by_setup?.length ? (
          <Expand title="By setup" sub="real trades · stopped trades (average per trade)">
            {r.by_setup.map((x: any) => (
              <Line key={x.setup} label={`${x.setup} ${x.name}`}
                value={`${x.real?.closed ? `${x.real.closed}, ${usdSigned(x.real.avg_usd)}` : "–"} · ${x.would_be?.closed ? `${x.would_be.closed}, ${usdSigned(x.would_be.avg_usd)}` : "–"}`} />
            ))}
          </Expand>
        ) : null}
        <T small>{r.read}</T>
      </Card>
    </View>
  );
}

function Rebuild({ r }: { r: any }) {
  const o = r.others;
  return (
    <View>
      <Q n={4} q="Reconstruction: does the rebuild match, and what did other traders teach us?"
        a={`${r.total} rebuilds so far (${r.nightly.runs} nightly, ${r.asked.runs} you asked for), ${r.mismatches} mismatch${r.mismatches === 1 ? "" : "es"}.`} />
      <Card title="Our own decisions, rebuilt from raw candles" sub={`Nightly ${r.nightly.every.replace("every night ", "")}; any time you ask Ananta to "run the reconstruction"`}>
        <View style={{ flexDirection: "row", gap: 12 }}>
          <Stat label="Rebuilds" value={r.total} sub={`${r.nightly.runs} nightly · ${r.asked.runs} asked`} />
          <Stat label="Mismatches" value={r.mismatches} color={r.mismatches ? C.bad : C.good} />
          <Stat label="Last check" value={r.last.match == null ? "–" : r.last.match ? "Match" : "Differs"} color={r.last.match === false ? C.bad : r.last.match ? C.good : undefined}
            sub={r.last.checked != null ? `${r.last.checked} decisions · ${r.last.when}` : r.last.when ?? undefined} />
        </View>
        <T small>{r.how}</T>
        <T small>If they ever differ: {r.if_mismatch.charAt(0).toLowerCase() + r.if_mismatch.slice(1)}</T>
      </Card>
      {o ? (
        <Card title="Other traders' real trades" sub={`${o.title} · ${o.period} · ran ${o.runs}`}>
          <View style={{ flexDirection: "row", gap: 12 }}>
            <Stat label="Accounts studied" value={o.accounts_sampled} sub={`${o.excluded_bots} bots left out`} />
            <Stat label="Traded our coins" value={o.accounts_trading_our_coins} />
            <Stat label="Round trips" value={Number(o.round_trips).toLocaleString()} sub={`${o.long} long · ${o.short} short`} />
          </View>
          <Line label="Our setups were silent before their buys" value={`${o.our_setups_silent_before_their_buys_pct}%`} />
          <Line label="Their timing edge" value="" sub={o.their_timing_edge} />
          <Line label="Did their skill last?" value={o.skill_persisted ? "Yes" : "No"} />
          {r.chain?.length ? (
            <View style={{ marginTop: 6 }}>
              <Label>What came of it</Label>
              {r.chain.map((c: any, i: number) => (
                <View key={c.id} style={{ flexDirection: "row", gap: 10 }}>
                  <View style={{ alignItems: "center", width: 40 }}>
                    <Pill text={c.id} color={C.accent} bg={C.accentSoft} />
                    {i < r.chain.length - 1 ? <View style={{ flex: 1, width: 2, backgroundColor: C.line, minHeight: 10 }} /> : null}
                  </View>
                  <View style={{ flex: 1, paddingBottom: 10, gap: 2 }}>
                    <Text style={{ color: C.text, fontWeight: "700", fontSize: 13 }}>{c.step}</Text>
                    <Text style={{ color: C.dim, fontSize: 12, lineHeight: 17 }}>{c.what}</Text>
                    <Text style={{ color: c.status === "WAITING_FOR_YOU" ? C.warn : C.faint, fontSize: 11, fontWeight: "700" }}>
                      {String(c.status).replace(/_/g, " ")}{c.verdict ? ` · ${VERDICT[c.verdict]?.[0] ?? c.verdict}` : ""}</Text>
                  </View>
                </View>
              ))}
            </View>
          ) : null}
        </Card>
      ) : null}
    </View>
  );
}

function MissDonut({ title, c }: { title: string; c: any }) {
  const total = (c?.CAUGHT ?? 0) + (c?.SEEN ?? 0) + (c?.MISSED ?? 0);
  return (
    <View style={{ flex: 1, alignItems: "center", gap: 6 }}>
      <Donut center={String(total)} sub="moves" parts={Object.keys(MISS).map((k) => ({ label: k, value: c?.[k] ?? 0, color: MISS[k][1] }))} />
      <Text style={{ color: C.text, fontWeight: "700", fontSize: 13 }}>{title}</Text>
      <Text style={{ color: C.dim, fontSize: 11 }}>{Object.keys(MISS).map((k) => `${c?.[k] ?? 0} ${MISS[k][0].toLowerCase()}`).join(" · ")}</Text>
    </View>
  );
}

function Misses({ m }: { m: any }) {
  const pats = [...(m.live?.patterns ?? []).map((p: any) => ({ ...p, tier: "10 coins" })), ...(m.t30?.patterns ?? []).map((p: any) => ({ ...p, tier: "30-coin tier" }))];
  const moves = [...(m.live?.moves ?? []), ...(m.t30?.moves ?? [])].sort((a: any, b: any) => (a.day < b.day ? 1 : a.day > b.day ? -1 : 0)).slice(0, 6);
  return (
    <View>
      <Q n={5} q="What did we miss, and what happens to it?"
        a={`${m.days_reviewed} day${m.days_reviewed === 1 ? "" : "s"} reviewed${m.since ? ` since ${m.since}` : ""}; ${m.forwarded} pattern${m.forwarded === 1 ? "" : "s"} sent to the repair shop so far.`} />
      <Card>
        <View style={{ flexDirection: "row" }}>
          <MissDonut title="Live 10 coins" c={m.live?.counts} />
          <MissDonut title="30-coin tier" c={m.t30?.counts} />
        </View>
        {moves.length ? <Divider /> : null}
        {moves.map((x: any, i: number) => (
          <View key={`${x.day}${x.coin}${i}`} style={{ paddingVertical: 4, gap: 2 }}>
            <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
              <Text style={{ color: C.text, fontWeight: "700", width: 64 }}>{x.coin}</Text>
              <Text style={{ color: C.good, fontWeight: "700", width: 60 }}>+{Number(x.move_pct).toFixed(1)}%</Text>
              <Text style={{ color: C.faint, fontSize: 12, flex: 1 }}>{x.day}</Text>
              <Pill text={(MISS[x.label]?.[0] ?? x.label).toUpperCase()} color={MISS[x.label]?.[1] ?? C.dim} />
            </View>
            {x.miss_class ? (
              <Text style={{ color: x.miss_class === "INTENTIONAL" ? C.good : x.miss_class === "DATA" ? C.warn : C.text, fontSize: 12, fontWeight: "700" }}>
                {x.miss_class.charAt(0) + x.miss_class.slice(1).toLowerCase()} miss: <Text style={{ fontWeight: "400", color: C.dim }}>{x.class_why}</Text>
              </Text>
            ) : null}
            <Text style={{ color: C.dim, fontSize: 12 }}>{x.why}</Text>
          </View>
        ))}
        {pats.length ? (
          <View style={{ gap: 8, marginTop: 4 }}>
            <Label>Misses that repeat (5 in 30 days goes to the repair shop)</Label>
            {pats.map((p: any, i: number) => (
              <View key={i} style={{ gap: 4 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                  <Text style={{ color: C.text, fontSize: 13, flex: 1 }}>{p.said} <Text style={{ color: C.faint }}>({p.tier}; {p.coins})</Text></Text>
                  <Text style={{ color: p.forwarded ? C.good : C.text, fontWeight: "700" }}>{p.forwarded ? "SENT" : `${p.times} of ${p.of}`}</Text>
                </View>
                <Progress value={Math.min(p.times, p.of)} of={p.of} color={p.forwarded ? C.good : C.warn} />
              </View>
            ))}
          </View>
        ) : null}
        <T small>{m.what_we_do}</T>
        <Text onPress={() => router.push("/missed")} style={{ color: C.accent, fontWeight: "700", marginTop: 2 }}>Open what we missed ›</Text>
      </Card>
    </View>
  );
}

function BoardRow({ x }: { x: any }) {
  const [open, setOpen] = useState(false);
  const g = GROUP[x.group] ?? GROUP.us;
  return (
    <View>
      <Pressable onPress={() => setOpen(!open)} delayLongPress={350}
        onLongPress={() => ask(`Repair board ${x.id}`, `Tell me about ${x.id} on the repair board: what was found, what we did, the change and its status.`)}
        style={{ flexDirection: "row", gap: 10, paddingVertical: 10, alignItems: "flex-start" }}>
        <View style={{ width: 4, alignSelf: "stretch", borderRadius: 2, backgroundColor: g.color }} />
        <View style={{ flex: 1, gap: 2 }}>
          <Text style={{ color: C.text, fontWeight: "600", fontSize: 14 }} numberOfLines={open ? undefined : 2}>
            <Text style={{ fontWeight: "800" }}>{x.id} </Text>{x.what}</Text>
          <Text style={{ color: C.faint, fontSize: 11 }}>{KIND[x.kind] ?? x.kind}{x.date ? ` · ${x.date}` : ""}{x.kind === "request" ? ` · from ${x.from}` : ""}</Text>
        </View>
        <View style={{ alignItems: "flex-end", gap: 4 }}>
          <Pill text={x.status_words.toUpperCase()} color={g.color} bg={g.soft} />
          {x.verdict && VERDICT[x.verdict] ? <Pill text={VERDICT[x.verdict][0]} color={VERDICT[x.verdict][1]} bg={VERDICT[x.verdict][2]} /> : null}
        </View>
      </Pressable>
      {open ? (
        <View style={{ paddingLeft: 14, paddingBottom: 10, gap: 4 }}>
          {x.from && x.kind !== "request" ? <><Label>{x.kind === "ticket" ? "Found by" : "Why it was sent"}</Label><T>{x.from}</T></> : null}
          {x.question ? <><Label>Question tested</Label><T>{x.question}</T></> : null}
          {x.did ? <><Label>{x.kind === "review" ? "Result" : "What we did"}</Label><T>{x.did}</T></> : null}
          {x.change ? <><Label>The change</Label><T>{x.change}</T></> : null}
          {x.next ? <><Label>Next</Label><T>{x.next}</T></> : null}
          {x.goal ? <View style={{ gap: 4 }}><T small>{x.have ?? 0} of {x.goal}</T><Progress value={Math.min(x.have ?? 0, x.goal)} of={x.goal} /></View> : null}
        </View>
      ) : null}
    </View>
  );
}

function Board({ b }: { b: any }) {
  const groups = ["you", "us", "evidence", "done"];
  const first = groups.find((g) => b.groups?.[g]) ?? "done";
  const [tab, setTab] = useState(first);
  const total = groups.reduce((a, g) => a + (b.groups?.[g] ?? 0), 0);
  const items = (b.items ?? []).filter((x: any) => x.group === tab);
  const [all, setAll] = useState(false);
  const shown = all ? items : items.slice(0, 8);
  return (
    <View>
      <Q n={6} q="What went to the repair shop, and what happened?"
        a={`${b.kinds.review} reviews, ${b.kinds.ticket} tickets, ${b.kinds.request} requests, ${b.kinds.question} questions waiting for evidence.`} />
      <Card>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
          <Donut size={104} center={String(total)} sub="items" parts={groups.map((g) => ({ label: g, value: b.groups?.[g] ?? 0, color: GROUP[g].color }))} />
          <View style={{ flex: 1, gap: 5 }}>
            {groups.map((g) => (
              <View key={g} style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                <View style={{ width: 10, height: 10, borderRadius: 3, backgroundColor: GROUP[g].color }} />
                <Text style={{ color: C.text, fontSize: 13, flex: 1 }}>{GROUP[g].word}</Text>
                <Text style={{ color: C.text, fontWeight: "700" }}>{b.groups?.[g] ?? 0}</Text>
              </View>
            ))}
          </View>
        </View>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
          {Object.entries(b.verdicts ?? {}).map(([k, v]: any) => (
            <Pill key={k} text={`${v} ${(VERDICT[k]?.[0] ?? k).toLowerCase()}`} color={VERDICT[k]?.[1] ?? C.dim} bg={VERDICT[k]?.[2] ?? C.card2} />
          ))}
          <T small>reviews so far</T>
        </View>
        <Segmented options={groups.map((g) => ({ key: g, label: `${GROUP[g].word.split(" ")[0]} ${b.groups?.[g] ?? 0}` }))} value={tab} onChange={(k) => { setTab(k); setAll(false); }} />
        {shown.map((x: any, i: number) => <View key={`${x.id}${i}`}>{i ? <Divider /> : null}<BoardRow x={x} /></View>)}
        {!items.length ? <T small>Nothing here.</T> : null}
        {items.length > shown.length ? <Text onPress={() => setAll(true)} style={{ color: C.accent, fontWeight: "700" }}>Show all {items.length}</Text> : null}
        <T small>{b.read}</T>
      </Card>
    </View>
  );
}

function InUse({ u }: { u: any }) {
  return (
    <View>
      <Q n={7} q="What changed because of it?" a={`${u.items.length} repairs run in paper, ${u.modes.length} paper mode you chose, ${u.safety_n} safety changes.`} />
      <Spot id="evidence.in_use">
        <Card>
          {u.items.map((x: any, i: number) => (
            <View key={x.id}>
              {i ? <Divider /> : null}
              <Expand title={`${x.id} · ${x.what}`} sub={`since ${x.since}${x.from ? ` · from review ${x.from.replace("R", "#")}` : ""}`}
                right={x.numbers?.book_pct != null ? <Text style={{ color: pnlColor(x.numbers.book_pct), fontWeight: "700" }}>{pct(x.numbers.book_pct)}</Text> : undefined}>
                {x.numbers ? <Line label="Book vs buy and hold" value={`${pct(x.numbers.book_pct)} vs ${pct(x.numbers.buy_hold_pct)}`} sub={`${x.numbers.trades ?? 0} trades · ${x.numbers.days ?? 0} days`} /> : null}
                <Label>Expected</Label><T>{x.expect}</T>
                <Label>Watch out</Label><T>{x.watch_out}</T>
                {x.so_far ? <><Label>So far</Label><T>{x.so_far}</T></> : null}
              </Expand>
            </View>
          ))}
          {u.modes.map((m: any) => (
            <View key={m.id}><Divider />
              <Expand title={`${m.id} · ${m.what}`} sub={`since ${m.since} · your decision`}>
                <Label>Why</Label><T>{m.why}</T>
                <Label>Watch out</Label><T>{m.watch_out}</T>
              </Expand>
            </View>
          ))}
        </Card>
      </Spot>
      <Spot id="evidence.safety">
        <Card>
          <Expand title={`Safety changes (${u.safety_n})`} sub="newest first">
            {u.safety.map((s: any, i: number) => <Line key={i} label={s.date} value="" sub={s.what} />)}
          </Expand>
        </Card>
      </Spot>
    </View>
  );
}

function Waiting({ w }: { w: any[] }) {
  return (
    <View>
      <Q n={8} q="What are we waiting for, and how long?" a="At today's pace. Separate market moves, not trade counts, are the slow part." />
      <Card>
        {w.map((x: any, i: number) => (
          <View key={x.id} style={{ gap: 4, paddingVertical: 6 }}>
            {i ? <Divider /> : null}
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8, paddingTop: i ? 6 : 0 }}>
              <Text style={{ color: C.text, fontWeight: "700", flex: 1 }}>{x.title}</Text>
              <Text style={{ color: x.done ? C.good : C.text, fontWeight: "700" }}>{x.have ?? 0}<Text style={{ color: C.faint, fontWeight: "400" }}> / {x.goal} {x.unit}</Text></Text>
            </View>
            <Progress value={Math.min(x.have ?? 0, x.goal || 1)} of={x.goal || 1} color={x.done ? C.good : C.accent} />
            <Text style={{ color: x.eta_days != null ? C.text : C.dim, fontSize: 12 }}>
              {x.done ? "Reached." : x.eta_days != null ? `At this pace: about ${x.eta_days} days (${x.eta_date})${x.pace ? `, ${x.pace}` : ""}` : x.eta_note ? `At this pace: no date yet (${x.eta_note})` : "No pace yet."}
            </Text>
            {x.also ? <T small>{x.also}.</T> : null}
            {x.speedup ? <T small>{x.speedup}</T> : null}
          </View>
        ))}
      </Card>
    </View>
  );
}

// ---------------------------------------------------------------------------
// The research detail (the older cards), loaded only when opened
// ---------------------------------------------------------------------------
const SECTION_ORDER = ["DECISIONS", "MARKET_WEATHER", "COIN_STRUCTURE", "SETUPS", "RISK_EXITS", "NEWS_EVENTS", "BASELINES"];
const SECTION_NAME: Record<string, string> = { DECISIONS: "JARVIS'S OWN DECISIONS (VS ITS RANDOM TWINS)", MARKET_WEATHER: "MARKET WEATHER", COIN_STRUCTURE: "COIN STRUCTURE AND ZONES", SETUPS: "SETUPS",
  RISK_EXITS: "RISK AND EXITS", NEWS_EVENTS: "NEWS AND EVENTS", BASELINES: "BASELINES (RANDOM, THE BAR TO BEAT)" };
const reg = (x: any) => (x?.closed ? `${x.closed}, ${usdSigned(x.avg_usd)}` : "–");
const IDEA: Record<string, [string, string]> = {
  SUPPORTED: [C.good, C.goodSoft], PROMISING: [C.accent, C.accentSoft], POLICY: [C.text, C.card2],
  NOT_SUPPORTED: [C.bad, C.badSoft], REJECTED: [C.bad, C.badSoft], INSUFFICIENT: [C.warn, C.warnSoft],
};

function Detail() {
  const { data: d } = useData("/v3/evidence/pipeline", 300000);
  const { data: kh } = useData("/v3/knowledge/hypotheses", 600000);
  const { data: cr } = useData("/v3/credit", 600000);
  const { data: sh } = useData("/v3/shadow/h07", 600000);
  const { data: sb } = useData("/v3/scoreboard", 300000);
  return (
    <View style={{ gap: 14 }}>
      {d?.seen ? (
        <Card title="Setups seen" sub={`${d.seen.reduce((a: number, x: any) => a + x.seen, 0)} times a setup's conditions were all met`}>
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
      ) : null}

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
          <T small>{sb.how_to_read}</T>
        </Card>
        </Spot>
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
    </View>
  );
}
