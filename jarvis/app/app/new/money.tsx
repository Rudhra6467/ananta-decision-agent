// Money (the new look): the account in hero, the four books with their clock, the next session's managed plan, every holding ranked
// with its grade and action. Data: /india/v3/money (jarvis/india/surfaces.py). Paper only: a suggestion is advice, the managed book acts on it on paper.
import { useEffect, useRef, useState } from "react";
import { ScrollView, Text, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useData } from "../../src/useData";
import { NScreen, askHref } from "../../src/newscreen";
import { Body, BookRow, Btn, G, GradeChip, H, Meta, NCard, TY, inr, pctS } from "../../src/newui";
import { C } from "../../src/theme";
import { ScreenError } from "../../src/safe";

export const ErrorBoundary = ScreenError;
const WORD: Record<string, string> = { hold: "hold", watch: "watch", trim: "trim", reduce: "reduce", tidy: "tidy", add: "add" };

export default function Money() {
  const { data: d, err, loading, reload } = useData<any>("/v3/money", 60000);
  const askIt = (q: string) => router.navigate(askHref(q));
  const plan = d?.plan;
  // 1 Nov (Madhav): Today's account box opens straight at Your holdings, the Nifty box at the options
  const p = useLocalSearchParams<{ focus?: string; t?: string }>();
  const ref = useRef<ScrollView | null>(null);
  const [ys, setYs] = useState<Record<string, number>>({});
  const ysRef = useRef<Record<string, number>>({});
  ysRef.current = ys;
  useEffect(() => {
    if (!d || !p.focus) return;
    // the section's place settles as fonts and cards finish laying out: aim three times, each at its latest position
    const go = () => { const y = ysRef.current[p.focus as string]; if (y != null) ref.current?.scrollTo({ y: Math.max(0, y - 8), animated: true }); };
    const ts = [80, 400, 900].map((ms) => setTimeout(go, ms));
    return () => ts.forEach(clearTimeout);
  }, [p.focus, p.t, d]);
  const mark = (k: string) => (e: any) => { const y = e?.nativeEvent?.layout?.y; if (y != null && ys[k] !== y) setYs((o) => ({ ...o, [k]: y })); };
  const ob = d?.options_book;
  return (
    <NScreen title="Money" loading={loading} onRefresh={reload} err={err} scrollRef={ref}>
      {d ? (
        <>
          <View>
            <Text style={[TY.hero, { color: C.text }]}>{inr(d.value_inr)}</Text>
            <Meta>{d.as_of ? d.as_of + " · " : ""}{inr(d.stocks_inr)} stocks · {inr(d.options_inr)} options · {inr(d.cash_inr)} cash</Meta>
          </View>
          <BookRow books={d.books || []} clock={d.clock?.words ? `${d.clock.words}` : null} note={d.books_note}
            onAsk={() => askIt("Explain the four books in detail: what each one is, how each started, what the numbers mean today, what the 60-session clock is for, and what would tell us the managed book is working.")} />
          {plan && !plan.error ? (
            <NCard pad={14}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
                <H>Next session's plan</H>
                <Meta color={G.gold()}>{plan.no_change ? "no change" : `${plan.cuts} cuts · ${plan.buys?.length || 0} buys`}</Meta>
              </View>
              <Body style={{ marginTop: 4 }}>{plan.brief}</Body>
              <View style={{ flexDirection: "row", gap: 8, marginTop: 10 }}>
                <Btn label="Why these" kind="s" onPress={() => askIt("Why these replacements? What else passed the filters?")} style={{ paddingVertical: 8, minHeight: 40 }} />
                <Btn label="Ask about it" kind="t" onPress={() => askIt("What will you change in my portfolio next session, and why?")} style={{ paddingVertical: 8, minHeight: 40 }} />
              </View>
            </NCard>
          ) : plan?.error ? <NCard pad={14}><Meta>No plan could be written</Meta><Body dim style={{ marginTop: 4 }}>{plan.error}</Body></NCard> : null}
          {d.managed?.replacements?.length ? (
            <NCard pad={14}>
              <H>Replacements held</H>
              {d.managed.replacements.map((r: any) => (
                <View key={r.symbol} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 8, borderTopWidth: 1, borderTopColor: C.line, marginTop: 8 }}>
                  <View><Text style={[TY.figure, { color: C.text }]}>{r.symbol} <Meta>for {r.for_cut}</Meta></Text><Meta faint>{r.held_sessions} sessions · stop ₹{r.stop}</Meta></View>
                  <Text style={[TY.figure, { color: (r.pnl_pct || 0) >= 0 ? C.good : C.bad }]}>{pctS(r.pnl_pct)}</Text>
                </View>
              ))}
            </NCard>
          ) : null}
          <View onLayout={mark("holdings")} style={{ backgroundColor: C.card, borderRadius: 16, paddingHorizontal: 16, paddingTop: 12 }}>
            <H>Your holdings</H>
            <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 10, paddingBottom: 6, borderBottomWidth: 1, borderBottomColor: C.line }}>
              <Meta>Holding · value · on cost</Meta><Meta>Ananta's decision</Meta>
            </View>
            {(d.holdings || []).map((h: any, i: number) => (
              <View key={h.symbol} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderTopColor: C.line }}>
                <View style={{ flex: 1, paddingRight: 8 }}>
                  <Text style={[TY.figure, { color: C.text }]}>{h.symbol} <Meta>{h.weight_pct != null ? `${h.weight_pct}% of stocks` : ""}</Meta></Text>
                  <Meta faint>{inr(h.value_inr)}{h.pnl_pct != null ? ` · ${pctS(h.pnl_pct, 0)} on cost` : ""}</Meta>
                </View>
                <GradeChip grade={h.grade} word={(WORD[h.action] || h.action || "") + (h.suggest_inr ? ` ${inr(h.suggest_inr)}` : "")} />
              </View>
            ))}
            <View style={{ paddingVertical: 12 }}><Meta faint>{d.holdings_note}</Meta></View>
          </View>
          {ob ? (
            <View onLayout={mark("options")} style={{ backgroundColor: C.card, borderRadius: 16, paddingHorizontal: 16, paddingTop: 12, paddingBottom: 12 }}>
              <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}><H>Your options</H><Meta>{inr(ob.set_aside_inr)} set aside</Meta></View>
              <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 10, paddingBottom: 6, borderBottomWidth: 1, borderBottomColor: C.line }}>
                <Meta>Open now</Meta><Meta>Closes</Meta>
              </View>
              {(ob.open || []).length ? ob.open.map((x: any) => (
                <View key={x.index + x.point} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 12 }}>
                  <Text style={[TY.figure, { color: C.text }]}>{x.index === "BANKNIFTY" ? "Bank Nifty" : "Nifty"} <Meta>{x.lots} lot · paper</Meta></Text>
                  <Meta>at the next open</Meta>
                </View>
              )) : <View style={{ paddingVertical: 12 }}><Body dim>No open option positions.</Body></View>}
              <View style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 6, borderTopWidth: 1, borderTopColor: C.line }}>
                <Meta>The options line · {ob.sessions} sessions</Meta><Meta>with real fills</Meta>
              </View>
              {(ob.by_index || []).map((r: any) => (
                <View key={r.index} style={{ flexDirection: "row", justifyContent: "space-between", paddingVertical: 8 }}>
                  <Body>{r.index === "BANKNIFTY" ? "Bank Nifty" : "Nifty"} <Meta>{r.trades} trades</Meta></Body>
                  <Text style={[TY.figure, { color: (r.rupees || 0) > 0 ? C.good : (r.rupees || 0) < 0 ? C.bad : C.text }]}>{inr(r.rupees)}</Text>
                </View>
              ))}
              <Meta faint style={{ marginTop: 6 }}>{ob.words}</Meta>
            </View>
          ) : null}
        </>
      ) : null}
    </NScreen>
  );
}
