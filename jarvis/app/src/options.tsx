// Options on India's Home (Madhav, 23 Oct): the Rs 60,000 index line (Nifty and Bank Nifty options), today's plan, the session's
// decisions, the option book's result, and the recorder's expiry-day paper book. Honest from day one: zero sessions say so.
// Shown only with the Indian market loaded; crypto (NDAX, spot only) has no options section.
import { useState } from "react";
import { Modal, Pressable, Text, TextInput, View } from "react-native";
import { api } from "./api";
import { useData } from "./useData";
import { Act, Btn, Card, ListState, T, Tag, cad, cadSigned, s as st } from "./ui";
import { C, pnlColor } from "./theme";
import { askAbout } from "./context";

export function OptionsCard() {
  const { data: d, err, loading, reload } = useData("/v3/options", 60000);
  const [alloc, setAlloc] = useState(false);
  if (!d && loading) return <Card><T dim>Reading the options line…</T></Card>;
  if (!d) return <Card><ListState state="error" text={err ?? "No data"} /></Card>;
  const p = d.plan ?? {};
  const pct = (x: any) => (x == null ? "–" : `${Math.round(x * 100)}%`);
  const a = d.allocation ?? {};
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
        <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
          <T small style={{ flex: 1 }}>Allocation: {a.mode === "fixed" ? `fixed · stocks ${cad(a.stocks_inr, 0)} · options ${cad(a.options_inr, 0)}` : "Ananta decides the split between stocks and options"}</T>
          <Act tight label="Change ›" onPress={() => setAlloc(true)} />
        </View>
        {alloc ? <AllocationSheet a={a} onClose={() => { setAlloc(false); reload(); }} /> : null}
        <T small>{d.suitability}</T>
      </View>
    </Card>
  );
}

// The capital split (Madhav, 23 Oct): Ananta decides, or a fixed split between stocks and options. Recorded now, shown on Home; the books
// size to it once SZ2 lands and the lock says yes (the sheet says so).
function AllocationSheet({ a, onClose }: { a: any; onClose: () => void }) {
  const [mode, setMode] = useState<"ananta" | "fixed">(a?.mode === "fixed" ? "fixed" : "ananta");
  const [stocks, setStocks] = useState(String(a?.stocks_inr ?? 30000));
  const [options, setOptions] = useState(String(a?.options_inr ?? 30000));
  const [msg, setMsg] = useState("");
  const save = async () => {
    setMsg("Saving…");
    try {
      await api("/v3/allocation", { mode, stocks_inr: mode === "fixed" ? Number(stocks) : null, options_inr: mode === "fixed" ? Number(options) : null });
      onClose();
    } catch (e: any) { setMsg(e?.message ?? "Could not save"); }
  };
  const chip = (on: boolean, label: string, onPress: () => void) => (
    <Pressable onPress={onPress} accessibilityRole="button" style={{ paddingVertical: 8, paddingHorizontal: 14, borderRadius: 999, backgroundColor: on ? C.text : C.card2, borderWidth: 1, borderColor: on ? C.text : C.line }}>
      <Text style={{ color: on ? C.bg : C.text, fontWeight: "700" }}>{label}</Text>
    </Pressable>
  );
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 16 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 16, gap: 12, maxWidth: 520, width: "100%", alignSelf: "center" }}>
          <Text style={st.h}>Capital allocation</Text>
          <T small>Who decides how the ₹60,000 is split between stocks and options.</T>
          <View style={{ flexDirection: "row", gap: 8 }}>{chip(mode === "ananta", "Ananta decides", () => setMode("ananta"))}{chip(mode === "fixed", "Fixed split", () => setMode("fixed"))}</View>
          {mode === "fixed" ? (
            <View style={{ flexDirection: "row", gap: 10 }}>
              <View style={{ flex: 1 }}><T small>Stocks (₹)</T><TextInput value={stocks} onChangeText={setStocks} keyboardType="numeric" style={{ color: C.text, borderWidth: 1, borderColor: C.line, borderRadius: 10, padding: 10 }} /></View>
              <View style={{ flex: 1 }}><T small>Options (₹)</T><TextInput value={options} onChangeText={setOptions} keyboardType="numeric" style={{ color: C.text, borderWidth: 1, borderColor: C.line, borderRadius: 10, padding: 10 }} /></View>
            </View>
          ) : <T small>Ananta moves money between stocks and options on its market read, within the guardrails.</T>}
          <T small>Recorded now and shown on Home. The books size to it once sizing v2 lands and the lock says yes; until then it changes no trade.</T>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <Btn label="Save" onPress={save} />
            <Btn label="Cancel" kind="secondary" onPress={onClose} />
          </View>
          {msg ? <T small>{msg}</T> : null}
        </Pressable>
      </Pressable>
    </Modal>
  );
}
