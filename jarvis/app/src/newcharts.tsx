// 7 Nov 2026 (Madhav): on Today, the Nifty 50 and Bank Nifty box opens their chart (the last 120 closes with the 50- and 200-day averages
// and the swing zones, from /v3/chart/NIFTY and /v3/chart/BANKNIFTY), and the portfolio box opens the portfolio's performance over time
// (/v3/chart/PORTFOLIO: your account on paper (the managed book), the same holdings left alone and the Nifty 500 from one start, one
// point per session). A sheet over the screen, the new look's cards and gold; every sheet ends with an Ask Ananta button.
// 10 Nov 2026 (Madhav: "do the necessary changes to crypto market Ananta as well"): the same sheet for crypto. The first box opens
// Bitcoin, Ethereum and Solana (/v3/surface/chart/BTC, ETH, SOL: daily closes with the dial's 50- and 200-day averages) and the account
// box opens the $500 book against Bitcoin just held and the hurdle (/v3/surface/chart/PORTFOLIO). The server names the lines.
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { LineChart } from "./charts";
import { Body, Btn, G, H, Meta, TY } from "./newui";
import { C } from "./theme";
import { useData } from "./useData";
import type { Market } from "./market";

export type ChartKind = "index" | "portfolio";
const INDIA = [{ key: "NIFTY", label: "Nifty 50" }, { key: "BANKNIFTY", label: "Bank Nifty" }];
const CRYPTO = [{ key: "BTC", label: "Bitcoin" }, { key: "ETH", label: "Ethereum" }, { key: "SOL", label: "Solana" }];
const ix = (v: any) => (v == null || v === "" ? null : Number(v));

// which chart a Today box opens: its label names the index; the stocks and options pages are the portfolio. A crypto page carries its
// coin (BTC, ETH, SOL); a crypto page without one is the account.
export function chartFor(label: string, market?: Market | null, coin?: string): { kind: ChartKind; which: string } {
  if (market === "crypto") return coin && CRYPTO.some((c) => c.key === coin) ? { kind: "index", which: coin } : { kind: "portfolio", which: "PORTFOLIO" };
  const l = (label || "").toLowerCase();
  if (l.includes("bank")) return { kind: "index", which: "BANKNIFTY" };
  if (l.includes("nifty")) return { kind: "index", which: "NIFTY" };
  return { kind: "portfolio", which: "PORTFOLIO" };
}

export function ChartSheet(props: {
  kind: ChartKind; which: string; market?: Market | null; onClose: () => void; onAsk: (q: string) => void; onOpenMoney?: () => void;
}) {
  const [cur, setCur] = useState(props.which);
  const base = props.market === "crypto" ? "/v3/surface/chart" : "/v3/chart";
  const path = props.kind === "index" ? `${base}/${cur}` : `${base}/PORTFOLIO`;
  // keyed on the path: switching the index mounts a fresh load, so a tap during the first fetch is never dropped (review, 7 Nov)
  return <ChartBody key={path} {...props} cur={cur} setCur={setCur} path={path} />;
}

function ChartBody({ kind, cur, setCur, path, market, onClose, onAsk, onOpenMoney }: {
  kind: ChartKind; cur: string; setCur: (k: string) => void; path: string; market?: Market | null; onClose: () => void; onAsk: (q: string) => void; onOpenMoney?: () => void;
}) {
  const { data: d, loading, err } = useData<any>(path, 300000);
  const ch = d?.chart ?? {};
  const dates: string[] = ch.dates ?? [];
  const crypto = market === "crypto";
  const INDEX = crypto ? CRYPTO : INDIA;
  const loc = crypto ? "en-US" : "en-IN";
  const title = kind === "index" ? (INDEX.find((i) => i.key === cur)?.label ?? cur) : "Your account on paper";
  const question = kind === "index"
    ? (crypto ? `Walk me through the ${title} chart: the trend, where it stands against its 50-day and 200-day averages, and what that means for the $500 book.`
      : `Walk me through the ${title} chart: the trend, where support and resistance are, and what it says for the next session.`)
    : (crypto ? "Walk me through the $500 book over time: against Bitcoin just held and the hurdle, and what explains the gap."
      : "Walk me through my account on paper over time: the managed book against the same holdings left alone and the Nifty 500, and what explains the gap.");
  const xl: [string, string] = d?.x_labels?.length === 2 ? [d.x_labels[0], d.x_labels[1]] : [dates[0] ?? "", dates[dates.length - 1] ?? ""];
  const ln = d?.lines ?? {};      // the server may name the three lines (crypto: the $500 book, Bitcoin held, the hurdle)
  let body: React.ReactNode;
  if (loading && !d) body = <Meta>Drawing…</Meta>;
  else if (err) body = <Body>{err}</Body>;
  else if (kind === "index") {
    const closes = (ch.closes ?? []).map(ix);
    const refs = [
      ...((ch.support ?? []) as number[]).slice(0, 2).map((v) => ({ value: v, label: `S ${Math.round(v).toLocaleString(loc)}`, color: C.good })),
      ...((ch.resistance ?? []) as number[]).slice(0, 2).map((v) => ({ value: v, label: `R ${Math.round(v).toLocaleString(loc)}`, color: C.bad })),
    ];
    body = closes.length ? (
      <LineChart height={200} refs={refs} xLabels={xl}
        series={[
          { data: closes, color: G.gold(), label: "close", fill: true },
          { data: (ch.sma50 ?? []).map(ix), color: C.warn, label: "50-day", dashed: true, width: 1 },
          { data: (ch.sma200 ?? []).map(ix), color: C.dim, label: "200-day", dashed: true, width: 1 },
        ]} />
    ) : <Body>No chart for {title} yet.</Body>;
  } else {
    const yours = (ch.yours ?? []).map(ix);
    body = yours.length >= 2 ? (
      <LineChart height={200} xLabels={xl}
        series={[
          { data: yours, color: G.gold(), label: ln.yours ?? "your account (managed book)", fill: true },
          { data: (ch.untouched ?? []).map(ix), color: C.dim, label: ln.untouched ?? "left alone", dashed: true, width: 1 },
          { data: (ch.nifty500 ?? []).map(ix), color: C.faint, label: ln.nifty500 ?? "Nifty 500", dashed: true, width: 1 },
        ]} />
    ) : <Body>{crypto ? `The account's record has ${yours.length} night${yours.length === 1 ? "" : "s"} so far; the line starts at two.`
      : `The portfolio record has ${yours.length} session${yours.length === 1 ? "" : "s"} so far; the line starts at two.`}</Body>;
  }
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} accessibilityLabel="Close the chart" style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.6)", justifyContent: "center", padding: 12 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 20, padding: 16, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center", maxHeight: "90%" }}>
          <ScrollView showsVerticalScrollIndicator={false} contentContainerStyle={{ gap: 10 }}>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
              <H>{title}</H>
              <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
                {d?.as_of ? <Meta>{d.as_of}</Meta> : null}
                <Pressable onPress={onClose} accessibilityRole="button" accessibilityLabel="Close" hitSlop={8}
                  style={{ width: 32, height: 32, borderRadius: 16, backgroundColor: C.card2, alignItems: "center", justifyContent: "center" }}>
                  <Text style={{ color: C.text, fontSize: 15, fontWeight: "700" }}>✕</Text>
                </Pressable>
              </View>
            </View>
            {kind === "index" ? (
              <View style={{ flexDirection: "row", gap: 8 }}>
                {INDEX.map((i) => (
                  <Pressable key={i.key} onPress={() => setCur(i.key)} accessibilityRole="tab" accessibilityState={{ selected: i.key === cur }}
                    style={{ paddingVertical: 7, paddingHorizontal: 14, borderRadius: 999, backgroundColor: i.key === cur ? G.goldSoft() : C.card2, minHeight: 34 }}>
                    <Text style={[TY.meta, { color: i.key === cur ? G.gold() : C.dim }]}>{i.label}</Text>
                  </Pressable>
                ))}
              </View>
            ) : null}
            {body}
            {kind === "portfolio" && d?.legend ? (
              <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
                {[["yours", G.gold()], ["untouched", C.dim], ["nifty500", C.faint]].map(([k, col]) => (
                  <View key={k} style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
                    <View style={{ width: 10, height: 3, borderRadius: 2, backgroundColor: col as string }} />
                    <Meta faint>{d.legend[k as string]}</Meta>
                  </View>
                ))}
              </View>
            ) : null}
            {d?.words ? <Body>{d.words}</Body> : null}
            <Meta faint>{d?.note ?? (kind === "index" ? (crypto ? "Daily closes in US dollars." : "Daily closes; zones are swing levels, a description, never a rule.") : (crypto ? "Paper only; one point a night." : "Paper only; one point per session."))}</Meta>
            <Btn label="Ask Ananta about this chart" onPress={() => { onClose(); onAsk(question); }} />
            {onOpenMoney ? <Btn label="Open Money" kind="s" onPress={() => { onClose(); onOpenMoney(); }} /> : null}
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
