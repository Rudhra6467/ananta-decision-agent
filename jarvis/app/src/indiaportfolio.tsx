// India's account on Home (Madhav, 24 Oct 16:27, with Wealthsimple's Home as the model): the first section talks only about the money —
// the total, its gain or loss, and two boxes, Stocks and Options, each with its value and its + or − on the outside. Tapping a box opens
// its positions with an Ask button. No guardrails and no market talk here: those live in "Your money · Ananta manages it".
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { Act, Btn, T, s as st } from "./ui";
import { C, pnlColor } from "./theme";
import { askAbout } from "./context";
import { useData } from "./useData";
import { useSheetRequest } from "./spotlight";

const rs = (x: any) => (x == null || Number.isNaN(Number(x)) ? "–" : "₹" + Math.round(Number(x)).toLocaleString("en-IN"));
const rsSigned = (x: any) => (x == null ? "–" : `${Number(x) < 0 ? "−" : "+"}${rs(Math.abs(Number(x)))}`);
const pctSigned = (x: any) => (x == null ? "" : `${Number(x) < 0 ? "−" : "+"}${Math.abs(Number(x)).toFixed(2)}%`);
const dayWords = (iso?: string | null) => {
  if (!iso) return "";
  const d = new Date(iso.length <= 10 ? iso + "T12:00:00" : iso);
  return d.toLocaleDateString("en-CA", { day: "numeric", month: "short" });
};
const GRADE_COLOR: Record<string, string> = { A: "good", B: "good", C: "warn", D: "bad" };
// plain words for the options book's internal names (no code word reaches a screen)
const STRATEGY_WORD: Record<string, string> = { "O-01": "opening option", "O-02": "opening option pair", "O-03": "expiry-eve strangle", "O-04": "expiry-afternoon straddle" };
const EXIT_WORD: Record<string, string> = { trail: "trailing stop", stop: "stop", time: "time exit", target: "target" };
const ACTION_WORD: Record<string, string> = { HOLD: "Keep", WATCH: "Watch", TRIM: "Trim", REDUCE: "Reduce", TIDY: "Tidy up", ADD: "Add" };

type Pos = { sym: string; qty: number; avg: number; last: number; value: number; paid: number; pnl: number; pnlPct: number | null };

export function positionsOf(a: any): Pos[] {
  return (Object.entries(a?.positions ?? {}) as [string, any][]).map(([sym, p]) => {
    const qty = Number(p.qty ?? 0), last = Number(p.last ?? 0), paid = Number(p.paid ?? 0);
    const value = qty * last;
    return { sym, qty, last, avg: Number(p.avg ?? (qty ? paid / qty : 0)), value, paid, pnl: value - paid, pnlPct: paid ? 100 * (value / paid - 1) : null };
  }).sort((x, y) => y.value - x.value);
}

function Box({ title, value, change, changePct, sub, onPress }: { title: string; value: number; change: number; changePct: number | null; sub: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`${title}, ${rs(value)}, ${rsSigned(change)}. Opens the positions.`}
      style={({ pressed }) => ({ flex: 1, gap: 6, backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 16, padding: 14, minHeight: 132, opacity: pressed ? 0.85 : 1 })}>
      <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
        <T small>{title}</T>
        <Text style={{ color: C.dim, fontSize: 18 }}>›</Text>
      </View>
      <Text style={[st.h, { fontSize: 22, lineHeight: 28 }]} numberOfLines={1} adjustsFontSizeToFit>{rs(value)}</Text>
      <View style={{ flex: 1 }} />
      <Text style={{ color: pnlColor(change), fontWeight: "700", fontSize: 14 }} numberOfLines={1}>{rsSigned(change)}{changePct == null ? "" : ` · ${pctSigned(changePct)}`}</Text>
      <T faint numberOfLines={2}>{sub}</T>
    </Pressable>
  );
}

export function IndiaPortfolio({ a }: { a: any }) {
  const [open, setOpen] = useState<null | "stocks" | "options">(null);
  useSheetRequest(["stocks", "options"], (n) => setOpen(n as "stocks" | "options"));      // "show my stocks" by voice
  const pos = positionsOf(a);
  const stocks = a.stocks_inr ?? pos.reduce((s, p) => s + p.value, 0);
  const paid = a.stocks_paid_inr ?? pos.reduce((s, p) => s + p.paid, 0);
  const stocksPnl = a.stocks_pnl_inr ?? stocks - paid;
  const stocksPct = a.stocks_pnl_pct ?? (paid ? 100 * (stocks / paid - 1) : null);
  const ob = a.options_book ?? {};
  const options = Number(a.options_inr ?? 0);
  const optPnl = Number(ob.pnl_inr ?? 0);
  const total = Number(a.value_cad ?? 0);
  const change = total - Number(a.start_cad ?? total);
  const stale = (a.prices_stale_days ?? 0) >= 1;
  return (
    <View style={{ gap: 12 }}>
      <Pressable onPress={() => askAbout({ screen: "home", label: "your account" }, "How is my account doing: the total, my stocks and my options?")}
        style={{ alignItems: "center", gap: 4, paddingVertical: 10 }} accessibilityRole="button">
        <T small>Your account · paper copy</T>
        <Text style={[st.big, { fontSize: 40, lineHeight: 48 }]}>{rs(total)}</Text>
        <Text style={{ color: pnlColor(change), fontWeight: "700", fontSize: 15 }}>{rsSigned(change)} · {pctSigned(a.return_pct ?? 0)} since {dayWords(a.started)}</Text>
        <T faint>{rs(a.cash_cad)} cash · prices from Zerodha, {dayWords(a.prices_at)}{stale ? ` (${a.prices_stale_days} days old)` : ""}</T>
      </Pressable>
      <View style={{ flexDirection: "row", gap: 10 }}>
        <Box title="Stocks" value={stocks} change={stocksPnl} changePct={stocksPct} sub={`${pos.length} holdings · on what you paid`} onPress={() => setOpen("stocks")} />
        <Box title="Options" value={options} change={optPnl} changePct={options ? (100 * optPnl) / options : null}
          sub={ob.sessions ? `${ob.sessions} session${ob.sessions === 1 ? "" : "s"} traded · paper` : "No trades yet · paper"} onPress={() => setOpen("options")} />
      </View>
      {open === "stocks" ? <StocksSheet a={a} pos={pos} stocks={stocks} pnl={stocksPnl} pct={stocksPct} onClose={() => setOpen(null)} /> : null}
      {open === "options" ? <OptionsSheet a={a} onClose={() => setOpen(null)} /> : null}
    </View>
  );
}

function Sheet({ title, onClose, children }: { title: string; onClose: () => void; children: any }) {
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 12 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center", maxHeight: "92%" }}>
          <View style={st.row}>
            <Text style={st.h}>{title}</Text>
            <Act tight label="✕" onPress={onClose} />
          </View>
          <ScrollView contentContainerStyle={{ gap: 10 }}>{children}</ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}

function StocksSheet({ a, pos, stocks, pnl, pct, onClose }: { a: any; pos: Pos[]; stocks: number; pnl: number; pct: number | null; onClose: () => void }) {
  const { data: plan } = useData("/v3/allocation/plan", 120000);
  const grade: Record<string, any> = Object.fromEntries(((plan?.holdings ?? []) as any[]).map((h) => [h.symbol, h]));
  const [pick, setPick] = useState<string | null>(null);
  const ask = (q: string, label = "your stocks") => { onClose(); askAbout({ screen: "home", label }, q); };
  return (
    <Sheet title={`Stocks · ${rs(stocks)}`} onClose={onClose}>
      <Text style={{ color: pnlColor(pnl), fontWeight: "700" }}>{rsSigned(pnl)}{pct == null ? "" : ` · ${pctSigned(pct)}`} on what you paid</Text>
      <T small>{pos.length} holdings, biggest first. Prices from the Zerodha snapshot of {dayWords(a.prices_at)}. Tap one for Ananta's grade and to ask about it.</T>
      {pos.map((p) => {
        const g = grade[p.sym];
        return (
          <Pressable key={p.sym} onPress={() => setPick(pick === p.sym ? null : p.sym)} style={{ gap: 3, paddingVertical: 8, borderTopWidth: 1, borderTopColor: C.line }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
              <Text style={{ color: C.text, fontWeight: "700" }}>{p.sym}{g ? <Text style={{ color: (C as any)[GRADE_COLOR[g.grade]] ?? C.dim }}>  {g.grade}</Text> : null}</Text>
              <Text style={{ color: C.text, fontWeight: "700" }}>{rs(p.value)}</Text>
            </View>
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
              <T small>{p.qty} × {rs(p.avg)} paid → {rs(p.last)} now</T>
              <Text style={{ color: pnlColor(p.pnl), fontSize: 13, fontWeight: "600" }}>{rsSigned(p.pnl)}{p.pnlPct == null ? "" : ` · ${pctSigned(p.pnlPct)}`}</Text>
            </View>
            {pick === p.sym ? (
              <View style={{ gap: 4, paddingTop: 2 }}>
                {g ? <T small>{ACTION_WORD[g.action] ?? g.action}{g.suggest_inr ? ` about ${rs(g.suggest_inr)}` : ""}: {g.why}</T> : null}
                {g?.wrong_if ? <T small>Wrong if {g.wrong_if}.</T> : null}
                <Act tight label={`Ask about ${p.sym} ›`} onPress={() => ask(`How is ${p.sym} doing in my account, and what would you do with it?`, p.sym)} />
              </View>
            ) : null}
          </Pressable>
        );
      })}
      <Btn label="Ask about my stocks" onPress={() => ask("Analyze my stocks: which are strong, which are weak, and what would you change first, with reasons?")} />
    </Sheet>
  );
}

function OptionsSheet({ a, onClose }: { a: any; onClose: () => void }) {
  const { data: o } = useData("/v3/options", 120000);
  const ob = a.options_book ?? {};
  const rec = o?.recorder ?? {};
  const dec: any[] = o?.decisions_today ?? [];
  const ask = (q: string) => { onClose(); askAbout({ screen: "home", label: "your options" }, q); };
  return (
    <Sheet title={`Options · ${rs(a.options_inr)}`} onClose={onClose}>
      <Text style={{ color: pnlColor(ob.pnl_inr ?? 0), fontWeight: "700" }}>{rsSigned(ob.pnl_inr ?? 0)} so far · {ob.sessions ?? 0} session{ob.sessions === 1 ? "" : "s"} traded</Text>
      <T small>{rs(a.options_inr)} of your paper money is set aside for options. Ananta trades one Nifty or Bank Nifty lot at a time, decided between 09:15 and 10:15 Indian time, and only when the opening move is bigger than what the option costs.</T>
      <View style={{ gap: 4, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 10 }}>
        <Text style={st.h}>Open positions</Text>
        {dec.filter((d) => d.open || d.status === "open").length ? dec.filter((d) => d.open || d.status === "open").map((d, i) => <T key={i} small>{d.words ?? JSON.stringify(d)}</T>)
          : <T small>None open.</T>}
      </View>
      <View style={{ gap: 4, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 10 }}>
        <Text style={st.h}>Last session</Text>
        <T small>{o?.words ?? "Reading the options line…"}</T>
        {o?.errors?.[0] && !/sign-in/i.test(o?.words ?? "") ? <T small>Why: {typeof o.errors[0] === "string" ? o.errors[0] : o.errors[0]?.words ?? o.errors[0]?.error ?? ""}</T> : null}
      </View>
      <View style={{ gap: 4, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 10 }}>
        <Text style={st.h}>The expiry-day practice book</Text>
        <T small>{rec.trades ? `${rec.trades} practice trades on real option prices, ${rsSigned(rec.net_inr)} net.` : "No practice trades recorded yet."}</T>
        {(rec.last ?? []).map((t: any, i: number) => <T key={i} small>{dayWords(t.day)} · {t.index} {STRATEGY_WORD[t.strategy] ?? "practice trade"}: {rsSigned(t.net_inr)}{t.exit ? ` (${EXIT_WORD[t.exit] ?? t.exit})` : ""}</T>)}
      </View>
      {o?.suitability ? <T faint>{o.suitability}</T> : null}
      <Btn label="Ask about my options" onPress={() => ask("How are my options doing, what would the options line trade next session, and why?")} />
    </Sheet>
  );
}
