import { Alert, View } from "react-native";
import { api } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { Btn, Busy, Card, Line, Screen, T, pct, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";

export default function Today() {
  const { data: d, err, loading, reload } = useData("/today");
  const act = async (kind: "approve" | "reject", ids: string[] | "all") => {
    const n = ids === "all" ? d?.portfolio?.pending?.length : ids.length;
    if (!(await confirmWithFaceId(kind === "approve" ? "Approve" : "Reject", `${kind === "approve" ? "Approve" : "Reject"} ${n} suggestion(s)? Paper book only.`))) return;
    try {
      const r = await api(`/portfolio/${kind}`, { ids });
      Alert.alert("Done", kind === "approve" ? `${r.fills?.length ?? 0} paper fills` : `${r.rejected} rejected`);
      reload();
    } catch (e: any) { Alert.alert("Failed", e.message); }
  };
  if (!d && loading) return <Busy />;
  const p = d?.portfolio;
  return (
    <Screen loading={loading} onRefresh={reload}>
      {err ? <Card><T style={{ color: C.bad }}>{err}</T></Card> : null}
      {p ? (
        <Card title="Suggestions waiting for you" right={<T dim>{p.mode}</T>}>
          {p.pending.length === 0 ? <T dim>Nothing waiting.</T> : p.pending.map((x: any) => (
            <View key={x.id} style={{ gap: 6, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 8 }}>
              <T>{x.action} {x.coin}</T>
              <T dim>{(x.why || []).join(" · ")}</T>
              <View style={{ flexDirection: "row", gap: 8 }}>
                <Btn label="Approve" kind="good" onPress={() => act("approve", [x.id])} />
                <Btn label="Reject" kind="bad" onPress={() => act("reject", [x.id])} />
              </View>
            </View>
          ))}
          {p.pending.length > 1 ? <Btn label={`Approve all ${p.pending.length}`} kind="good" onPress={() => act("approve", "all")} /> : null}
        </Card>
      ) : null}
      {p ? (
        <Card title="Portfolio (paper)">
          <Line label="Main book" value={`${usd(p.main.equity)} (${pct(p.main.return_pct)})`} />
          <Line label="Always-automatic shadow" value={`${usd(p.shadow.equity)} (${pct(p.shadow.return_pct)})`} />
          <Line label="Bitcoin market gate" value={p.btc_gate ? "ON" : "OFF"} color={p.btc_gate ? C.good : C.bad} />
        </Card>
      ) : null}
      {d?.explorer ? (
        <Card title="Explorer (paper trades)">
          <Line label="Account" value={usd(d.explorer.equity)} />
          <Line label="Open trades" value={d.explorer.open_trades} />
          <Line label="Open P&L" value={usd(d.explorer.unrealized_usd)} color={d.explorer.unrealized_usd >= 0 ? C.good : C.bad} />
          <Line label="Realized" value={usd(d.explorer.realized_usd)} />
        </Card>
      ) : null}
      <Card title="Recent alerts">
        {(d?.alerts ?? []).slice(0, 10).map((a: any, i: number) => (
          <View key={i}><T>{a.title}</T><T dim>{a.body}</T><T dim>{String(a.ts).slice(0, 16).replace("T", " ")} UTC</T></View>
        ))}
      </Card>
      {d?.daily_report ? <Card title={`Daily report ${d.daily_report.name}`}><T dim>{d.daily_report.markdown}</T></Card> : null}
      <T dim>As of {d?.as_of} · paper only</T>
    </Screen>
  );
}
