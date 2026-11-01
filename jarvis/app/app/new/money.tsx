// Money (the new look): the account in hero, the four books with their clock, the next session's managed plan, every holding ranked
// with its grade and action. Data: /india/v3/money (jarvis/india/surfaces.py). Paper only: a suggestion is advice, the managed book acts on it on paper.
import { Text, View } from "react-native";
import { router } from "expo-router";
import { useData } from "../../src/useData";
import { NScreen } from "../../src/newscreen";
import { Body, BookRow, Btn, G, GradeChip, H, Meta, NCard, TY, inr, pctS } from "../../src/newui";
import { C } from "../../src/theme";
import { ScreenError } from "../../src/safe";

export const ErrorBoundary = ScreenError;
const WORD: Record<string, string> = { hold: "hold", watch: "watch", trim: "trim", reduce: "reduce", tidy: "tidy", add: "add" };

export default function Money() {
  const { data: d, err, loading, reload } = useData<any>("/v3/money", 60000);
  const askIt = (q: string) => router.navigate({ pathname: "/new/ask", params: { q } } as any);
  const plan = d?.plan;
  return (
    <NScreen title="Money" loading={loading} onRefresh={reload} err={err}>
      {d ? (
        <>
          <View>
            <Text style={[TY.hero, { color: C.text }]}>{inr(d.value_inr)}</Text>
            <Meta>{d.as_of ? d.as_of + " · " : ""}{inr(d.stocks_inr)} stocks · {inr(d.options_inr)} options · {inr(d.cash_inr)} cash</Meta>
          </View>
          <BookRow books={d.books || []} clock={d.clock?.words ? `${d.clock.words}` : null} note={d.books_note} />
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
          <View style={{ backgroundColor: C.card, borderRadius: 16, paddingHorizontal: 16, paddingTop: 12 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "baseline" }}><H>Your holdings</H><Meta>{(d.holdings || []).length} ranked</Meta></View>
            {(d.holdings || []).map((h: any, i: number) => (
              <View key={h.symbol} style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 12, borderTopWidth: i ? 1 : 0, borderTopColor: C.line, marginTop: i ? 0 : 6 }}>
                <View style={{ flex: 1, paddingRight: 8 }}>
                  <Text style={[TY.figure, { color: C.text }]}>{h.symbol} <Meta>{h.weight_pct != null ? `${h.weight_pct}% of stocks` : ""}</Meta></Text>
                  <Meta faint>{inr(h.value_inr)}{h.pnl_pct != null ? ` · ${pctS(h.pnl_pct, 0)} on cost` : ""}</Meta>
                </View>
                <GradeChip grade={h.grade} word={(WORD[h.action] || h.action || "") + (h.suggest_inr ? ` ${inr(h.suggest_inr)}` : "")} />
              </View>
            ))}
            <View style={{ paddingVertical: 12 }}><Meta faint>{d.holdings_note}</Meta></View>
          </View>
        </>
      ) : null}
    </NScreen>
  );
}
