// The order ticket on a coin's trading page (plan 3.2): Buy or Sell, an amount in dollars or in coins, an optional stop and
// target, then Review (nothing changes yet) and Place. Paper money only; it goes into the signed-in account's own book,
// stamped with its initials, and Ananta watches it but never closes it without a yes.
import { useEffect, useState } from "react";
import { Pressable, Text, TextInput, View } from "react-native";
import { api } from "./api";
import { ExplainSheet, showToast } from "./blocks";
import { C, COIN_NAME } from "./theme";
import { Btn, T, price } from "./ui";

export function OrderTicket({ coin, px, side: side0, held, open, onClose, onDone }: {
  coin: string; px: number; side: "buy" | "sell"; held?: number; open: boolean; onClose: () => void; onDone: () => void;
}) {
  const [side, setSide] = useState<"buy" | "sell">(side0);
  const [unit, setUnit] = useState<"usd" | "coin">("usd");
  const [amt, setAmt] = useState("100");
  const [stop, setStop] = useState("");
  const [target, setTarget] = useState("");
  const [pv, setPv] = useState<any>(null);
  const [msg, setMsg] = useState("");
  useEffect(() => { if (open) { setSide(side0); setPv(null); setMsg(""); setAmt(side0 === "sell" && held ? String(Math.round(held * px)) : "100"); } }, [open, side0]);
  const name = COIN_NAME[coin] ?? coin;
  const n = parseFloat(amt);
  const usd = !isFinite(n) ? null : unit === "usd" ? n : n * px;
  const order = () => ({ side, coin, usd, stop: side === "buy" && parseFloat(stop) ? parseFloat(stop) : undefined,
    target: side === "buy" && parseFloat(target) ? parseFloat(target) : undefined });
  const review = async () => {
    setMsg("");
    try { setPv(await api("/v3/manual/order", order())); } catch (e: any) { setPv(null); setMsg(e?.message ?? String(e)); }
  };
  const place = async () => {
    try {
      await api("/v3/manual/order", { ...order(), confirm: true });
      showToast("Order placed ✓");
      onClose();
      onDone();
    } catch (e: any) { setMsg(e?.message ?? String(e)); }
  };
  const field = (v: string, set: (s: string) => void, ph: string) => (
    <TextInput value={v} onChangeText={(t) => { set(t.replace(/[^0-9.]/g, "")); setPv(null); }} placeholder={ph} keyboardType="decimal-pad"
      placeholderTextColor={C.faint} style={{ flex: 1, borderWidth: 1, borderColor: C.line, borderRadius: 10, paddingHorizontal: 12, paddingVertical: 10,
        color: C.text, fontSize: 16, backgroundColor: C.card }} />
  );
  return (
    <ExplainSheet open={open} onClose={onClose} title={`${side === "buy" ? "Buy" : "Sell"} ${name} · paper`}>
      <View style={{ flexDirection: "row", gap: 8 }}>
        {(["buy", "sell"] as const).map((s) => (
          <Pressable key={s} onPress={() => { setSide(s); setPv(null); }} disabled={s === "sell" && !held}
            style={{ flex: 1, borderRadius: 10, paddingVertical: 10, alignItems: "center", opacity: s === "sell" && !held ? 0.4 : 1,
              backgroundColor: side === s ? (s === "buy" ? C.good : C.bad) : C.card2 }}>
            <Text style={{ color: side === s ? C.onInk : C.text, fontWeight: "700" }}>{s === "buy" ? "Buy" : "Sell"}</Text>
          </Pressable>
        ))}
      </View>
      <T dim small>Price now {price(px)}{held ? ` · you hold ${held.toPrecision(4)} ${coin}` : ""}</T>
      <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
        {field(amt, setAmt, unit === "usd" ? "Amount in $" : `Amount in ${coin}`)}
        <Pressable onPress={() => { setUnit(unit === "usd" ? "coin" : "usd"); setAmt(""); setPv(null); }}
          style={{ borderRadius: 10, borderWidth: 1, borderColor: C.line, paddingHorizontal: 12, paddingVertical: 10 }}>
          <Text style={{ color: C.accent, fontWeight: "700" }}>{unit === "usd" ? "$" : coin} ⇄</Text>
        </Pressable>
      </View>
      {usd != null && unit === "coin" ? <T small dim>≈ ${usd.toFixed(2)}</T> : null}
      {side === "buy" ? (
        <>
          <T small dim>Optional: sell automatically below a stop, or at a target.</T>
          <View style={{ flexDirection: "row", gap: 8 }}>
            {field(stop, setStop, "Stop price")}
            {field(target, setTarget, "Target price")}
          </View>
        </>
      ) : null}
      {pv ? (
        <View style={{ backgroundColor: C.accentSoft, borderRadius: 12, padding: 12, gap: 10 }}>
          <Text style={{ color: C.text, fontSize: 15, lineHeight: 21 }}>{pv.summary}</Text>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <View style={{ flex: 1 }}><Btn label="Change" kind="secondary" onPress={() => setPv(null)} /></View>
            <View style={{ flex: 1 }}><Btn label="Place order" onPress={place} /></View>
          </View>
        </View>
      ) : <Btn label="Review order" onPress={review} />}
      {msg ? <Text style={{ color: C.bad }}>{msg}</Text> : null}
    </ExplainSheet>
  );
}

// the Buy / Sell bar fixed at the bottom of the trading page
export function TradeBar({ onBuy, onSell, canSell }: { onBuy: () => void; onSell: () => void; canSell: boolean }) {
  return (
    <View style={{ flexDirection: "row", gap: 10, paddingHorizontal: 16, paddingTop: 10, paddingBottom: 22, backgroundColor: C.card,
      borderTopWidth: 1, borderTopColor: C.line }}>
      <Pressable onPress={onBuy} style={({ pressed }) => ({ flex: 1, backgroundColor: C.good, borderRadius: 12, paddingVertical: 13, alignItems: "center", opacity: pressed ? 0.8 : 1 })}>
        <Text style={{ color: C.onInk, fontWeight: "800", fontSize: 16 }}>Buy</Text>
      </Pressable>
      <Pressable onPress={onSell} disabled={!canSell} style={({ pressed }) => ({ flex: 1, backgroundColor: canSell ? C.bad : C.card2, borderRadius: 12,
        paddingVertical: 13, alignItems: "center", opacity: pressed ? 0.8 : 1 })}>
        <Text style={{ color: canSell ? C.onInk : C.faint, fontWeight: "800", fontSize: 16 }}>Sell</Text>
      </Pressable>
    </View>
  );
}
