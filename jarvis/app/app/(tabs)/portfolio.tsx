import { Alert, Pressable, View } from "react-native";
import { router } from "expo-router";
import { api } from "../../src/api";
import { Spark, StackBar } from "../../src/charts";
import { confirmWithFaceId } from "../../src/guard";
import { Btn, Busy, Card, Chip, Screen, T, pct, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, coinColor, ratingColor } from "../../src/theme";

export default function Portfolio() {
  const { data: d, err, loading, reload } = useData("/portfolio");
  const switchMode = async () => {
    const next = d.mode === "SUGGEST" ? "AUTO" : "SUGGEST";
    const msg = next === "AUTO" ? "Jarvis will change the paper portfolio by itself, without asking." : "Every change will wait for your approval.";
    if (!(await confirmWithFaceId(`Switch to ${next}`, msg))) return;
    try { await api("/portfolio/mode", { mode: next, confirm: true }); reload(); } catch (e: any) { Alert.alert("Failed", e.message); }
  };
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><T style={{ color: C.bad }}>{err}</T></Screen>;
  const main = d.books.MAIN;
  const parts = [
    ...Object.entries(main.holdings as Record<string, number>).sort((a, b) => b[1] - a[1]).map(([c, v]) => ({ label: c, value: v, color: coinColor[c] ?? C.ok })),
    { label: "Cash", value: Math.max(0, main.cash), color: C.line },
  ];
  const counts = ["STRONG", "OK", "WEAK", "OUT"].map((r) => [r, d.ratings.filter((x: any) => x.rating === r).length] as const);
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card>
        <T dim>Portfolio book (paper)</T>
        <T style={{ fontSize: 30, fontWeight: "800" }}>{usd(main.equity)}</T>
        <T style={{ color: main.return_pct >= 0 ? C.good : C.bad, fontWeight: "700" }}>{pct(main.return_pct)} · shadow (always automatic) {pct(d.books.SHADOW.return_pct)}</T>
        <StackBar parts={parts} />
      </Card>
      <View style={{ flexDirection: "row", gap: 8, flexWrap: "wrap" }}>
        {counts.map(([r, n]) => <Chip key={r} text={`${r} ${n}`} color={ratingColor[r]} />)}
        <Chip text={`BTC gate ${d.btc_gate ? "ON" : "OFF"}`} color={d.btc_gate ? C.good : C.bad} />
      </View>
      {d.ratings.map((r: any) => (
        <Pressable key={r.coin} onPress={() => router.push(`/coin/${r.coin}`)}>
          <Card>
            <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", gap: 8 }}>
              <View style={{ gap: 4, flex: 1 }}>
                <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
                  <T style={{ fontWeight: "800", fontSize: 16, color: coinColor[r.coin] ?? C.text }}>{r.coin}</T>
                  <Chip text={r.rating} color={ratingColor[r.rating]} />
                </View>
                <T dim style={{ fontSize: 12 }}>{r.why?.[0]}</T>
                <T dim style={{ fontSize: 12 }}>held {usd(main.holdings?.[r.coin] ?? 0)}</T>
              </View>
              <Spark data={r.spark ?? []} color={ratingColor[r.rating]} />
            </View>
          </Card>
        </Pressable>
      ))}
      <Card title={`Mode: ${d.mode}`}>
        <T dim>{d.mode === "SUGGEST" ? "Jarvis suggests; you approve on Today." : "Jarvis changes the paper portfolio by itself."} Rule {d.rule}: hold a coin while it is above its 20- and 50-day averages and Bitcoin is above its 50-day. Decided {d.decided}.</T>
        <Btn label={d.mode === "SUGGEST" ? "Switch to AUTO" : "Back to SUGGEST"} onPress={switchMode} />
      </Card>
    </Screen>
  );
}
