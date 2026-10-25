// Your money on India's Home (Madhav, 23 Oct, evening: "make the app feel more understandable ... critical details behind More"): ONE card,
// one sentence, the three parts of the money in one line, and More › opens everything else — the mode switch, today's move, the options line,
// the paper copy of the account, every holding ranked with its reason, and what Ananta is watching. The same grammar as the crypto account card.
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { api } from "./api";
import { useData } from "./useData";
import { Act, Btn, Card, ListState, T, s as st } from "./ui";
import { C } from "./theme";
import { askAbout } from "./context";
import { useSheetRequest } from "./spotlight";

const GRADE_COLOR: Record<string, string> = { A: "good", B: "good", C: "warn", D: "bad" };
const ACTION_WORD: Record<string, string> = { HOLD: "Keep", WATCH: "Watch", TRIM: "Trim", REDUCE: "Reduce", TIDY: "Tidy up", ADD: "Add" };
const rs = (x: any) => (x == null ? "–" : "₹" + Math.round(Number(x)).toLocaleString("en-IN"));

export function MoneyCard() {
  const { data: d, err, loading, reload } = useData("/v3/allocation/plan", 60000);
  const [open, setOpen] = useState(false);
  useSheetRequest(["money"], () => setOpen(true));                    // "show my money" by voice
  if (!d && loading) return <Card><T dim>Reading your money…</T></Card>;
  if (!d) return <Card><ListState state="error" text={err ?? "No data"} /></Card>;
  const auto = d.mode === "autonomous";
  const sl = d.sleeves?.now ?? {};
  const n = d.counts?.suggested_changes ?? (d.suggestions ?? []).length;
  const voiceQ = auto ? "What did you move today, and why?" : "What would you change in my holdings?";
  return (
    <Card>
      <View style={st.row}>
        <Text style={st.h}>{auto ? "Your money · Ananta manages it" : "Your money · Ananta only suggests"}</Text>
        <Act tight label="More ›" onPress={() => setOpen(true)} />
      </View>
      <T>{d.headline}</T>
      <T small>Stocks {rs(sl.stocks)} · Options {rs(sl.options)} · Cash {rs(sl.cash)}{n ? ` · ${n} suggested change${n === 1 ? "" : "s"}` : ""} · paper</T>
      {d.guard ? <T faint numberOfLines={2}>Guardrails: {d.guard.short} · {String(d.guard.next ?? "").replace(/^Next decisions at the open on /, "next decisions ")}</T> : null}
      <View style={{ flexDirection: "row", gap: 10 }}>
        <Act tight label="Ask ›" onPress={() => askAbout({ screen: "allocation", label: "your money" }, voiceQ)} />
      </View>
      {open ? <MoneyPanel d={d} onClose={() => { setOpen(false); reload(); }} reload={reload} /> : null}
    </Card>
  );
}

function Row({ k, v }: { k: string; v: string }) {
  return (
    <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 10 }}>
      <T small>{k}</T>
      <T small style={{ textAlign: "right", flexShrink: 1 }}>{v}</T>
    </View>
  );
}

function Section({ title, children }: { title: string; children: any }) {
  return (
    <View style={{ gap: 4, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 10 }}>
      <Text style={st.h}>{title}</Text>
      {children}
    </View>
  );
}

function MoneyPanel({ d, onClose, reload }: { d: any; onClose: () => void; reload: () => void }) {
  const { data: o } = useData("/v3/options", 60000);
  const [msg, setMsg] = useState("");
  const [mode, setMode] = useState<string>(d.mode);
  const [pick, setPick] = useState<string | null>(null);
  const [showAll, setShowAll] = useState(false);
  const setM = async (m: string) => {
    setMsg("Saving…");
    try { await api("/v3/allocation", { mode: m }); setMode(m); setMsg(m === "autonomous" ? "Ananta now manages the split on paper. The plan rebuilds within minutes." : "Ananta now only suggests; nothing moves."); reload(); }
    catch (e: any) { setMsg(e?.message ?? "Could not save"); }
  };
  const chip = (on: boolean, label: string, onPress: () => void) => (
    <Pressable onPress={onPress} accessibilityRole="button" style={{ paddingVertical: 8, paddingHorizontal: 14, borderRadius: 999, backgroundColor: on ? C.text : C.card2, borderWidth: 1, borderColor: on ? C.text : C.line }}>
      <Text style={{ color: on ? C.bg : C.text, fontWeight: "700" }}>{label}</Text>
    </Pressable>
  );
  const sl = d.sleeves ?? {};
  const hs: any[] = d.holdings ?? [];
  const changes = hs.filter((x) => x.action !== "HOLD" && x.action !== "WATCH");
  const shown = showAll ? hs : changes.length ? changes : hs.slice(0, 5);
  const ab = d.account_book;
  const p = o?.plan ?? {};
  const pct = (x: any) => (x == null ? "–" : `${Math.round(x * 100)}%`);
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 12 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center", maxHeight: "92%" }}>
          <View style={st.row}>
            <Text style={st.h}>Your money</Text>
            <Act tight label="✕" onPress={onClose} />
          </View>
          <ScrollView contentContainerStyle={{ gap: 10 }}>
            <T>{d.headline}</T>
            <View style={{ gap: 2 }}>
              <Row k="Stocks" v={`${rs(sl.now?.stocks)} · ${sl.now_pct?.stocks}%${sl.after && sl.after.stocks !== sl.now?.stocks ? ` → ${rs(sl.after.stocks)}` : ""}`} />
              <Row k="Options" v={`${rs(sl.now?.options)} · ${sl.now_pct?.options}% (kept at or under ${sl.target_pct?.options_max}%)${sl.after && sl.after.options !== sl.now?.options ? ` → ${rs(sl.after.options)}` : ""}`} />
              <Row k="Cash" v={`${rs(sl.now?.cash)} · ${sl.now_pct?.cash}% (at least ${sl.target_pct?.cash_min}%)${sl.after && sl.after.cash !== sl.now?.cash ? ` → ${rs(sl.after.cash)}` : ""}`} />
            </View>

            {d.guard ? (
              <Section title={`Guardrails: ${d.guard.short}`}>
                {(d.guard.lines ?? []).map((w: string, i: number) => <T key={i} small>· {w}</T>)}
                {d.guard.next ? <T small>· {d.guard.next}</T> : null}
                <T small>{d.guard.buy_rule}</T>
              </Section>
            ) : null}

            <Section title="Who decides">
              <View style={{ flexDirection: "row", gap: 8 }}>{chip(mode === "autonomous", "Ananta manages", () => setM("autonomous"))}{chip(mode !== "autonomous", "Ananta suggests", () => setM("advisory"))}</View>
              <T small>{mode === "autonomous"
                ? "Ananta moves money between stocks, options and cash on the paper copy of your account, at most 10% of it a day, and writes every move down. Nothing goes to your broker."
                : "Options stay at ₹50,000 and your stocks stay as they are. Ananta grades every holding and suggests changes; it moves nothing."}</T>
              {msg ? <T small>{msg}</T> : null}
            </Section>

            {(d.moves ?? []).length ? (
              <Section title={d.moves_applied ? "Today's move" : mode === "autonomous" ? "Today's move (fills at the session's close)" : "What it would move (not moved: suggest-only)"}>
                {d.moves.map((m: any, i: number) => <T key={i} small>{rs(m.inr)} {m.from} → {m.to}{m.symbol ? ` (${m.symbol})` : ""}{m.why ? `: ${m.why}` : ""}</T>)}
              </Section>
            ) : null}

            <Section title={`Your stocks, ranked${changes.length ? ` · ${changes.length} suggested change${changes.length === 1 ? "" : "s"}` : ""}`}>
              {hs.length === 0 ? <T small>Holdings are shown to the owner only.</T> : null}
              {shown.map((x) => (
                <Pressable key={x.symbol} onPress={() => setPick(pick === x.symbol ? null : x.symbol)} style={{ gap: 2, paddingVertical: 4, borderTopWidth: 1, borderTopColor: C.line }}>
                  <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                    <Text style={{ color: C.text, fontWeight: "700" }}>{x.rank}. {x.symbol} <Text style={{ color: (C as any)[GRADE_COLOR[x.grade]] }}>{x.grade}</Text></Text>
                    <Text style={{ color: C.text }}>{ACTION_WORD[x.action] ?? x.action}{x.suggest_inr ? ` ~${rs(x.suggest_inr)}` : ""}</Text>
                  </View>
                  <T small>{rs(x.value_inr)} · {x.weight_pct}% of your stocks{x.pnl_pct == null ? "" : ` · ${x.pnl_pct > 0 ? "+" : ""}${x.pnl_pct}% on what you paid`}</T>
                  {pick === x.symbol ? (
                    <View style={{ gap: 2 }}>
                      <T small>{x.why}</T>
                      <T small>Wrong if {x.wrong_if}.</T>
                      <Act tight label="Talk it over ›" onPress={() => { onClose(); askAbout({ screen: "allocation", label: x.symbol }, `Should I ${(ACTION_WORD[x.action] ?? x.action).toLowerCase()} ${x.symbol}? Why is it rated ${x.grade}?`); }} />
                    </View>
                  ) : null}
                </Pressable>
              ))}
              {hs.length > shown.length || showAll ? <Act tight label={showAll ? "Show fewer" : `Show all ${hs.length}`} onPress={() => setShowAll(!showAll)} /> : null}
            </Section>

            {o ? (
              <Section title="The options line">
                <T small>{o.words}</T>
                {p.session ? <T small>Plan for {p.session}: up {pct(p.bull)} · down {pct(p.bear)} · flat {pct(p.neutral)}{p.vix ? ` · fear gauge ${p.vix}` : ""}</T> : null}
                {d.options?.words ? <T small>{d.options.words}</T> : null}
                <T small>{o.suitability}</T>
              </Section>
            ) : null}

            {ab ? (
              <Section title="The paper copy of your account">
                <T small>{ab.words}</T>
                {(ab.trades ?? []).slice(-5).reverse().map((t: any, i: number) => (
                  <T key={i} small>{t.day}: {t.skipped ? `skipped ${t.symbol ?? ""} — ${t.skipped}` : t.side ? `${t.side} ${t.qty} ${t.symbol} at ₹${t.price} (charges ₹${t.cost_inr})` : `${rs(t.inr)} ${t.from} → ${t.to}`}</T>
                ))}
                {(ab.differs_from_real ?? []).length ? <T small>It differs from your real account in {ab.differs_from_real.length} name{ab.differs_from_real.length === 1 ? "" : "s"}: the copy trades on paper only.</T> : null}
              </Section>
            ) : null}

            {(d.watch ?? []).length ? (
              <Section title="What Ananta is watching">
                {d.watch.map((w: any, i: number) => <T key={i} small>{w.what}: {w.now}. Changes if {w.flips_if}.</T>)}
              </Section>
            ) : null}
            <T small>{d.words}</T>
            <Btn label="Talk it over with Ananta" onPress={() => { onClose(); askAbout({ screen: "allocation", label: "your money" }, "Walk me through my holdings: what is strong, what is weak, and what would you change first?"); }} />
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

// Drafts waiting for Madhav (the reconstruction's DECISION findings): one line and a count; Open › shows each with Yes / Skip.
// Shown only when something waits. The voice tab takes "approve the first draft" too.
export function DraftsCard() {
  const { data: d, reload } = useData("/v3/reconstruction/drafts", 120000);
  const [open, setOpen] = useState(false);
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
        <Act tight label="Open ›" onPress={() => setOpen(true)} />
      </View>
      <T small>Ananta found {rows.length === 1 ? "a pattern" : `${rows.length} patterns`} in what it missed. Yes means it studies the idea on past years; Skip closes it.</T>
      {open ? (
        <Modal visible transparent animationType="fade" onRequestClose={() => setOpen(false)}>
          <Pressable onPress={() => setOpen(false)} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 12 }}>
            <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center", maxHeight: "92%" }}>
              <View style={st.row}>
                <Text style={st.h}>Waiting for your yes</Text>
                <Act tight label="✕" onPress={() => setOpen(false)} />
              </View>
              <ScrollView contentContainerStyle={{ gap: 10 }}>
                {rows.map((x) => (
                  <View key={x.key} style={{ gap: 6, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 8 }}>
                    <T small>{x.n}. {x.words}</T>
                    <View style={{ flexDirection: "row", gap: 8 }}>
                      <Btn small label="Yes, study it" onPress={() => act(x.key, "APPROVED")} />
                      <Btn small kind="secondary" label="Skip" onPress={() => act(x.key, "SKIPPED")} />
                      <Act tight label="Ask ›" onPress={() => { setOpen(false); askAbout({ screen: "reconstruction", label: "a draft" }, `Explain draft ${x.n} in simple words: what did Ananta miss, and what would the study test?`); }} />
                    </View>
                  </View>
                ))}
                {msg ? <T small>{msg}</T> : null}
              </ScrollView>
            </Pressable>
          </Pressable>
        </Modal>
      ) : null}
    </Card>
  );
}
