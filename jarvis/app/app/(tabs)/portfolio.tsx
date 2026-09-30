import { Alert, View } from "react-native";
import { api } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { Btn, Busy, Card, Line, Screen, T, pct, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, ratingColor } from "../../src/theme";

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
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card title={`Mode: ${d.mode}`} right={<Btn label={d.mode === "SUGGEST" ? "Switch to AUTO" : "Back to SUGGEST"} onPress={switchMode} />}>
        <T dim>Rule {d.rule}: hold a coin while it is above its 50- and 20-day averages and Bitcoin is above its 50-day. Decided {d.decided}.</T>
        <Line label="Main book" value={`${usd(d.books.MAIN.equity)} (${pct(d.books.MAIN.return_pct)})`} />
        <Line label="Shadow (always automatic)" value={`${usd(d.books.SHADOW.equity)} (${pct(d.books.SHADOW.return_pct)})`} />
      </Card>
      {d.ratings.map((r: any) => (
        <Card key={r.coin} title={r.coin} right={<T style={{ color: ratingColor[r.rating], fontWeight: "700" }}>{r.rating}</T>}>
          <Line label="Held in main book" value={usd(d.books.MAIN.holdings?.[r.coin] ?? 0)} />
          <View style={{ gap: 2 }}>{(r.why || []).map((w: string, i: number) => <T key={i} dim>• {w}</T>)}</View>
        </Card>
      ))}
    </Screen>
  );
}
