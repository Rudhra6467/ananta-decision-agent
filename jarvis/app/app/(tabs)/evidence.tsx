import { Pressable, View } from "react-native";
import { router } from "expo-router";
import { HBars } from "../../src/charts";
import { Busy, Card, Chip, Line, Screen, T, Tile, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";

const SETUP_NAMES: Record<string, string> = {
  E1: "E1 trend pullback", E2: "E2 breakout", E3: "E3 bounce", E4: "E4 momentum", E5: "E5 squeeze",
  E6: "E6 RSI dip", E7: "E7 oversold in downtrend", E8: "E8 weak below 50-day",
};

export default function Evidence() {
  const { data: d, err, loading, reload } = useData("/evidence");
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><T style={{ color: C.bad }}>{err}</T></Screen>;
  const tot = d.closed_total ?? { n: 0, net_usd: 0, win_rate: null };
  const openPnl = d.open_trades.reduce((a: number, t: any) => a + (t.pnl_usd ?? 0), 0);
  const sight = Object.entries(d.sightings_today ?? {}) as [string, any][];
  return (
    <Screen loading={loading} onRefresh={reload}>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        <Tile label="Closed trades" value={tot.n} sub={`win rate ${tot.win_rate == null ? "–" : Math.round(tot.win_rate * 100) + "%"}`} />
        <Tile label="Closed P&L" value={usd(tot.net_usd)} color={tot.net_usd >= 0 ? C.good : C.bad} sub="after costs" />
        <Tile label="Open trades" value={d.open_trades.length} sub={`open P&L ${usd(openPnl)}`} color={openPnl >= 0 ? C.good : C.bad} />
        <Tile label="What Jarvis knows" value={`${d.registry?.counts?.KEEP ?? 0} keep`} sub={`${d.registry?.counts?.WATCH ?? 0} watch · ${d.registry?.counts?.DROP ?? 0} dropped`} color={C.accent} />
      </View>
      <Card title="Profit and loss by setup">
        {(d.by_setup ?? []).length === 0 ? <T dim>No closed trades yet; this fills in as trades finish.</T> :
          <HBars fmt={usd} items={d.by_setup.map((x: any) => ({ label: SETUP_NAMES[x.name] ?? x.name, value: x.net_usd, sub: `${x.n} trades · ${Math.round(x.win_rate * 100)}% won` }))} />}
      </Card>
      <Card title="Profit and loss by exit">
        {(d.by_exit ?? []).length === 0 ? <T dim>Nothing yet.</T> :
          <HBars fmt={usd} items={d.by_exit.map((x: any) => ({ label: x.name, value: x.net_usd, sub: `${x.n} trades` }))} />}
      </Card>
      <Card title="Open paper trades">
        {d.open_trades.length === 0 ? <T dim>None open.</T> : d.open_trades.map((t: any) => (
          <Pressable key={t.id} onPress={() => router.push(`/coin/${t.coin}`)}>
            <Line label={`${t.coin} · ${SETUP_NAMES[t.setup] ?? t.setup} · ${t.type.replace("_", " ").toLowerCase()}`} value={`${usd(t.pnl_usd)}  ${t.suggestion}`} color={t.pnl_usd >= 0 ? C.good : C.bad} />
          </Pressable>
        ))}
      </Card>
      <Card title="Intraday setups seen (24h) · information only">
        {sight.length === 0 ? <T dim>None in the last 24 hours.</T> :
          <HBars fmt={(v) => `${Math.round(v * 100)}%`} items={sight.map(([k, v]) => ({
            label: `${SETUP_NAMES[k] ?? k} × ${v.seen}`, value: v.p_target ?? 0, color: v.reliable ? C.good : C.dim,
            sub: `chance of +3% before −1.5% in 24h · after costs ${v.net_pct ?? "–"}%${v.reliable ? " · reliably positive" : ""}`,
          }))} />}
      </Card>
      {d.registry ? (
        <Card title="What Jarvis knows">
          {["KEEP", "WATCH", "DROP"].map((st) => (
            <View key={st} style={{ gap: 4 }}>
              <Chip text={st} color={st === "KEEP" ? C.good : st === "WATCH" ? C.warn : C.bad} />
              {d.registry.variables.filter((v: any) => v.status === st).map((v: any) => (
                <T key={v.id} dim style={{ fontSize: 12 }}>• {v.name}</T>
              ))}
            </View>
          ))}
        </Card>
      ) : null}
      {d.weekly ? <Card title={`Weekly evidence · ${d.weekly.name}`}><T dim>{d.weekly.markdown}</T></Card> : null}
    </Screen>
  );
}
