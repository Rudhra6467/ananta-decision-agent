import { View } from "react-native";
import { Busy, Card, Line, Screen, T, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";

export default function Evidence() {
  const { data: d, err, loading, reload } = useData("/evidence");
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><T style={{ color: C.bad }}>{err}</T></Screen>;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card title={`Open paper trades (${d.open_trades.length})`}>
        {d.open_trades.map((t: any) => (
          <Line key={t.id} label={`${t.coin} ${t.setup} ${t.type}`} value={`${usd(t.pnl_usd)} · ${t.suggestion}`} color={t.pnl_usd >= 0 ? C.good : C.bad} />
        ))}
      </Card>
      <Card title="Recently closed">
        {d.recent_closed.length === 0 ? <T dim>None yet.</T> : d.recent_closed.map((t: any, i: number) => (
          <Line key={i} label={`${t.coin} ${t.setup} · ${t.bell}`} value={usd(t.net_usd)} color={(t.net_usd ?? 0) >= 0 ? C.good : C.bad} />
        ))}
      </Card>
      <Card title="Intraday setups seen (24h, not traded)">
        {Object.keys(d.sightings_today).length === 0 ? <T dim>None.</T> : Object.entries(d.sightings_today).map(([k, v]: any) => (
          <Line key={k} label={`${k} × ${v.seen}`} value={`${v.p_target != null ? Math.round(v.p_target * 100) + "% hit +3% first" : "–"} · after costs ${v.net_pct ?? "–"}%${v.reliable ? " · RELIABLE" : ""}`} />
        ))}
      </Card>
      {d.registry ? (
        <Card title="What Jarvis knows (variable registry)">
          <T dim>KEEP {d.registry.counts.KEEP} · WATCH {d.registry.counts.WATCH} · DROP {d.registry.counts.DROP}</T>
          {d.registry.variables.filter((v: any) => v.status === "KEEP").map((v: any) => (
            <View key={v.id}><T>✓ {v.name}</T><T dim>{v.evidence}</T></View>
          ))}
        </Card>
      ) : null}
      {d.weekly ? <Card title={`Weekly evidence ${d.weekly.name}`}><T dim>{d.weekly.markdown}</T></Card> : null}
    </Screen>
  );
}
