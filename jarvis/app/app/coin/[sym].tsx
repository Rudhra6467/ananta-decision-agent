import { View } from "react-native";
import { Stack, useLocalSearchParams } from "expo-router";
import { LineChart } from "../../src/charts";
import { Busy, Card, Chip, Line, Screen, T, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, coinColor, ratingColor } from "../../src/theme";

export default function Coin() {
  const { sym } = useLocalSearchParams<{ sym: string }>();
  const { data: d, err, loading, reload } = useData(`/coin/${sym}`);
  const title = <Stack.Screen options={{ headerShown: true, title: String(sym), headerStyle: { backgroundColor: C.bg }, headerTintColor: C.text }} />;
  if (!d && loading) return <>{title}<Busy /></>;
  if (!d) return <>{title}<Screen loading={loading} onRefresh={reload}><T style={{ color: C.bad }}>{err}</T></Screen></>;
  const r = d.rating;
  return (
    <>
      {title}
      <Screen loading={loading} onRefresh={reload}>
        <Card>
          <View style={{ flexDirection: "row", justifyContent: "space-between", alignItems: "center" }}>
            <T style={{ fontSize: 28, fontWeight: "800", color: coinColor[d.coin] ?? C.text }}>{usd(d.price)}</T>
            {r ? <Chip text={r.rating} color={ratingColor[r.rating]} /> : null}
          </View>
          <T dim>Held in the portfolio book: {usd(d.held_usd)}</T>
          {(r?.why ?? []).map((w: string, i: number) => <T key={i} dim>• {w}</T>)}
        </Card>
        <Card title="Last 120 days">
          <LineChart height={190} series={[
            { data: d.daily.map((x: any) => x.c), color: coinColor[d.coin] ?? C.text, label: "price" },
            { data: d.daily.map((x: any) => x.ema20), color: C.ema20, width: 1.5, label: "20-day" },
            { data: d.daily.map((x: any) => x.ema50), color: C.ema50, width: 1.5, dashed: true, label: "50-day" },
          ]} />
          <T dim style={{ fontSize: 12 }}>Held while the price stays above both averages and Bitcoin is above its 50-day.</T>
        </Card>
        <Card title="Last 4 days (hourly)">
          <LineChart height={140} series={[
            { data: d.hourly.map((x: any) => x.c), color: coinColor[d.coin] ?? C.text, label: "price" },
            { data: d.hourly.map((x: any) => x.ema20), color: C.ema20, width: 1.5, label: "20-hour" },
          ]} />
        </Card>
        <Card title="Explorer trades on this coin">
          {d.open_trades.length === 0 && d.closed_trades.length === 0 ? <T dim>None yet.</T> : null}
          {d.open_trades.map((t: any) => (
            <Line key={t.id} label={`open · ${t.setup} ${t.type}`} value={`${usd(t.pnl_usd)} · ${t.suggestion}`} color={t.pnl_usd >= 0 ? C.good : C.bad} />
          ))}
          {d.closed_trades.map((t: any, i: number) => (
            <Line key={i} label={`${t.setup} · ${t.bell}`} value={usd(t.net_usd)} color={(t.net_usd ?? 0) >= 0 ? C.good : C.bad} />
          ))}
        </Card>
      </Screen>
    </>
  );
}
