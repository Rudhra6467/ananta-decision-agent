// Options on India's Home (Madhav, 23 Oct): the Rs 60,000 index line (Nifty and Bank Nifty options), today's plan, the session's
// decisions, the option book's result, and the recorder's expiry-day paper book. Honest from day one: zero sessions say so.
// Shown only with the Indian market loaded; crypto (NDAX, spot only) has no options section.
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { api } from "./api";
import { useData } from "./useData";
import { Act, Btn, Card, ListState, T, Tag, cad, cadSigned, s as st } from "./ui";
import { C, pnlColor } from "./theme";
import { askAbout } from "./context";

export function OptionsCard() {
  const { data: d, err, loading, reload } = useData("/v3/options", 60000);
  if (!d && loading) return <Card><T dim>Reading the options line…</T></Card>;
  if (!d) return <Card><ListState state="error" text={err ?? "No data"} /></Card>;
  const p = d.plan ?? {};
  const pct = (x: any) => (x == null ? "–" : `${Math.round(x * 100)}%`);
  return (
    <Card>
      <View style={st.row}>
        <Text style={st.h}>Options · ₹60,000 index line</Text>
        <Act tight label="Ask ›" onPress={() => askAbout({ screen: "options", label: "the options line" }, "How is the options line doing, and what is today's plan?")} />
      </View>
      <View style={{ flexDirection: "row", alignItems: "baseline", gap: 10 }}>
        <Text style={{ color: C.text, fontSize: 28, fontWeight: "800" }}>{cad(d.value_inr, 0)}</Text>
        <Text style={{ color: pnlColor(d.pnl_inr), fontWeight: "700" }}>{cadSigned(d.pnl_inr)} · {d.sessions} session{d.sessions === 1 ? "" : "s"}</Text>
      </View>
      <T small>{d.words}</T>
      {p.session ? (
        <View style={{ gap: 4 }}>
          <T small>Plan for {p.session}: bull {pct(p.bull)} · bear {pct(p.bear)} · flat {pct(p.neutral)}{p.vix ? ` · VIX ${p.vix}` : ""}</T>
          <T small>{p.scenarios?.bull ? `Bull = ${p.scenarios.bull}; bear = ${p.scenarios.bear}` : ""}{(p.limits ?? []).length ? ` · limits: ${(p.limits ?? []).join(", ")}` : ""}</T>
        </View>
      ) : null}
      {(d.decisions_today ?? []).length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {d.decisions_today.map((x: any, i: number) => <Tag key={i} text={`${x.index} · ${x.point}`} value={String(x.action ?? "")} />)}
        </View>
      ) : null}
      <View style={{ gap: 2 }}>
        <T small>Recorder book (expiry-day O-03/O-04 on real option minutes): {d.recorder?.trades ?? 0} trades · {cadSigned(d.recorder?.net_inr)}</T>
        <T small>{d.suitability}</T>
      </View>
    </Card>
  );
}

// Allocation (Madhav, 23 Oct 14:04): options fixed at ₹50,000 and stocks as they are in his account (advisory: Ananta rates, ranks and suggests), or
// autonomous (Ananta moves capital between stocks, options and cash on paper and keeps watching). Both paper; the plan is the owner's.
const GRADE_COLOR: Record<string, string> = { A: "good", B: "good", C: "warn", D: "bad" };
const rs = (x: any) => (x == null ? "–" : "₹" + Math.round(Number(x)).toLocaleString("en-IN"));

export function AllocationCard() {
  const { data: d, err, loading, reload } = useData("/v3/allocation/plan", 60000);
  const [open, setOpen] = useState(false);
  if (!d && loading) return <Card><T dim>Reading the allocation…</T></Card>;
  if (!d) return <Card><ListState state="error" text={err ?? "No data"} /></Card>;
  const auto = d.mode === "autonomous";
  const sl = d.sleeves ?? {};
  const top = (d.suggestions ?? []).slice(0, 3);
  return (
    <Card>
      <View style={st.row}>
        <Text style={st.h}>Allocation · {auto ? "Autonomous" : "Advisory"}</Text>
        <Act tight label="Open ›" onPress={() => setOpen(true)} />
      </View>
      <T small>{d.headline}</T>
      {sl.now ? <Sleeves sl={sl} /> : null}
      {d.account_book ? <T small>{d.account_book.words}</T> : null}
      {top.map((x: any, i: number) => (
        <T key={i} small>{x.action} {x.symbol} ({x.grade}){x.suggest_inr ? ` · about ${rs(x.suggest_inr)}` : ""}</T>
      ))}
      {open ? <AllocationPanel d={d} onClose={() => { setOpen(false); reload(); }} reload={reload} /> : null}
    </Card>
  );
}

function Sleeves({ sl }: { sl: any }) {
  const now = sl.now_pct ?? {}, tg = sl.target_pct ?? {};
  const row = (label: string, k: string, tgt?: string) => (
    <View key={k} style={{ flexDirection: "row", justifyContent: "space-between" }}>
      <T small>{label}</T>
      <T small>{rs(sl.now?.[k])} · {now[k]}%{tgt ? ` (table: ${tgt})` : ""}{sl.after && sl.after[k] !== sl.now[k] ? ` → ${rs(sl.after[k])}` : ""}</T>
    </View>
  );
  return (
    <View style={{ gap: 2 }}>
      {row("Stocks", "stocks", `about ${tg.stocks}%`)}
      {row("Options", "options", `up to ${tg.options_max}%`)}
      {row("Cash", "cash", `at least ${tg.cash_min}%`)}
    </View>
  );
}

function AllocationPanel({ d, onClose, reload }: { d: any; onClose: () => void; reload: () => void }) {
  const [msg, setMsg] = useState("");
  const [mode, setMode] = useState<string>(d.mode);
  const [pick, setPick] = useState<string | null>(null);
  const setM = async (m: string) => {
    setMsg("Saving…");
    try { await api("/v3/allocation", { mode: m }); setMode(m); setMsg(m === "autonomous" ? "Autonomous: the plan rebuilds within minutes; moves are paper only." : "Advisory: nothing moves; ratings and suggestions only."); reload(); }
    catch (e: any) { setMsg(e?.message ?? "Could not save"); }
  };
  const chip = (on: boolean, label: string, onPress: () => void) => (
    <Pressable onPress={onPress} accessibilityRole="button" style={{ paddingVertical: 8, paddingHorizontal: 14, borderRadius: 999, backgroundColor: on ? C.text : C.card2, borderWidth: 1, borderColor: on ? C.text : C.line }}>
      <Text style={{ color: on ? C.bg : C.text, fontWeight: "700" }}>{label}</Text>
    </Pressable>
  );
  const hs: any[] = d.holdings ?? [];
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 12 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center", maxHeight: "92%" }}>
          <View style={st.row}>
            <Text style={st.h}>Capital allocation</Text>
            <Act tight label="✕" onPress={onClose} />
          </View>
          <ScrollView contentContainerStyle={{ gap: 10 }}>
            <View style={{ flexDirection: "row", gap: 8 }}>{chip(mode !== "autonomous", "Advisory", () => setM("advisory"))}{chip(mode === "autonomous", "Autonomous", () => setM("autonomous"))}</View>
            <T small>{mode === "autonomous"
              ? "Autonomous: one pool. Ananta sets the split from the market regime, moves capital between stocks, options and cash (at most 10% of the pool a session), writes every move to the ledger and keeps watching."
              : "Advisory: options fixed at ₹50,000, stocks as they are in your account. Ananta rates and ranks every holding and suggests changes. It moves nothing."}</T>
            {msg ? <T small>{msg}</T> : null}
            <T>{d.headline}</T>
            {d.sleeves?.now ? <Sleeves sl={d.sleeves} /> : null}
            {(d.moves ?? []).length ? (
              <View style={{ gap: 4 }}>
                <Text style={st.h}>{d.moves_applied ? "Paper moves today" : "What it would move (advisory: not moved)"}</Text>
                {d.moves.map((m: any, i: number) => <T key={i} small>{rs(m.inr)} {m.from} → {m.to}{m.symbol ? ` (${m.symbol})` : ""}{m.why ? ` — ${m.why}` : ""}</T>)}
              </View>
            ) : null}
            {d.account_book ? (
              <View style={{ gap: 2 }}>
                <Text style={st.h}>Account book (what the allocated capital holds, paper)</Text>
                <T small>{d.account_book.words}</T>
                {(d.account_book.trades ?? []).slice(-6).reverse().map((t: any, i: number) => (
                  <T key={i} small>{t.day}: {t.skipped ? `skipped ${t.symbol ?? ""} — ${t.skipped}` : t.side ? `${t.side} ${t.qty} ${t.symbol} at ₹${t.price} (costs ₹${t.cost_inr})` : `${rs(t.inr)} ${t.from} → ${t.to}`}</T>
                ))}
                {(d.account_book.differs_from_real ?? []).length ? <T small>Differs from your real account in {d.account_book.differs_from_real.length} name(s): the twin trades on paper only.</T> : null}
              </View>
            ) : null}
            {d.options ? (
              <View style={{ gap: 2 }}>
                <Text style={st.h}>Options sleeve · grade {d.options.grade}</Text>
                <T small>{d.options.words}</T>
                <T small>{d.options.why}</T>
              </View>
            ) : null}
            <Text style={st.h}>Your stocks, ranked</Text>
            {hs.length === 0 ? <T small>Holdings are shown to the owner only.</T> : null}
            {hs.map((x) => (
              <Pressable key={x.symbol} onPress={() => setPick(pick === x.symbol ? null : x.symbol)} style={{ gap: 2, paddingVertical: 4, borderTopWidth: 1, borderTopColor: C.line }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                  <Text style={{ color: C.text, fontWeight: "700" }}>{x.rank}. {x.symbol} · <Text style={{ color: (C as any)[GRADE_COLOR[x.grade]] }}>{x.grade}</Text> ({x.score})</Text>
                  <Text style={{ color: C.text }}>{x.action}{x.suggest_inr ? ` ~${rs(x.suggest_inr)}` : ""}</Text>
                </View>
                <T small>{rs(x.value_inr)} · {x.weight_pct}% of stocks · {x.pnl_pct == null ? "" : `${x.pnl_pct > 0 ? "+" : ""}${x.pnl_pct}% on cost`}</T>
                {pick === x.symbol ? (
                  <View style={{ gap: 2 }}>
                    <T small>{x.why}</T>
                    <T small>Wrong if: {x.wrong_if}</T>
                    <Act tight label="Talk it over ›" onPress={() => { onClose(); askAbout({ screen: "allocation", label: x.symbol }, `Should I ${x.action.toLowerCase()} ${x.symbol}? Why is it grade ${x.grade}?`); }} />
                  </View>
                ) : null}
              </Pressable>
            ))}
            {(d.watch ?? []).length ? (
              <View style={{ gap: 4 }}>
                <Text style={st.h}>What I'm watching</Text>
                {d.watch.map((w: any, i: number) => <T key={i} small>{w.what}: {w.now}. {w.flips_if}.</T>)}
              </View>
            ) : null}
            <T small>{d.yardstick}</T>
            <T small>{d.words}</T>
            <Btn label="Talk it over with Ananta" onPress={() => { onClose(); askAbout({ screen: "allocation", label: "the allocation" }, "Rate and rank my holdings and tell me what you would change first."); }} />
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

// Drafts waiting for Madhav (RX-IN, 23 Oct): the reconstruction's DECISION findings. Yes = register a study (tested on 2000-2023 only);
// Skip = closed. Shown on India Home only when something waits; the voice tab takes "approve the first draft" too.
export function DraftsCard() {
  const { data: d, reload } = useData("/v3/reconstruction/drafts", 120000);
  const [msg, setMsg] = useState("");
  const rows: any[] = d?.drafts ?? [];
  if (!rows.length) return null;
  const act = async (key: string, decision: string) => {
    setMsg("Saving…");
    try { await api("/v3/reconstruction/decide", { key, decision }); setMsg(decision === "APPROVED" ? "Approved: a study will be registered." : "Skipped."); reload(); }
    catch (e: any) { setMsg(e?.message ?? "Could not save"); }
  };
  return (
    <Card>
      <View style={st.row}>
        <Text style={st.h}>Waiting for your yes · {rows.length}</Text>
        <Act tight label="Ask ›" onPress={() => askAbout({ screen: "reconstruction", label: "the drafts" }, "What drafts are waiting for me, and what does each mean?")} />
      </View>
      <T small>{d?.meaning}</T>
      {rows.slice(0, 4).map((x) => (
        <View key={x.key} style={{ gap: 4, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 6 }}>
          <T small>{x.n}. {x.type} ({x.day}): {x.words}</T>
          <View style={{ flexDirection: "row", gap: 8 }}>
            <Btn small label="Yes, register" onPress={() => act(x.key, "APPROVED")} />
            <Btn small kind="secondary" label="Skip" onPress={() => act(x.key, "SKIPPED")} />
          </View>
        </View>
      ))}
      {msg ? <T small>{msg}</T> : null}
    </Card>
  );
}
