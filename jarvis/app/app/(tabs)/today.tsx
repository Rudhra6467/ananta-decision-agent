import { useState } from "react";
import { Alert, Pressable, View } from "react-native";
import { api } from "../../src/api";
import { LineChart } from "../../src/charts";
import { confirmWithFaceId } from "../../src/guard";
import { Btn, Busy, Card, Chip, Screen, T, Tile, pct, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";

const START = 4000; // two $2,000 paper books

export default function Today() {
  const { data: d, err, loading, reload } = useData("/today");
  const { data: h, reload: reloadH } = useData("/history?days=30");
  const [showReport, setShowReport] = useState(false);
  const refresh = () => { reload(); reloadH(); };
  const act = async (kind: "approve" | "reject", ids: string[] | "all") => {
    const n = ids === "all" ? d?.portfolio?.pending?.length : ids.length;
    if (!(await confirmWithFaceId(kind === "approve" ? "Approve" : "Reject", `${kind === "approve" ? "Approve" : "Reject"} ${n} suggestion(s)? Paper book only.`))) return;
    try {
      const r = await api(`/portfolio/${kind}`, { ids });
      Alert.alert("Done", kind === "approve" ? `${r.fills?.length ?? 0} paper trades made` : `${r.rejected} rejected`);
      refresh();
    } catch (e: any) { Alert.alert("Failed", e.message); }
  };
  if (!d && loading) return <Busy />;
  const p = d?.portfolio;
  const total = (p?.main?.equity ?? 0) + (d?.explorer?.equity ?? 0);
  const pts = h?.points ?? [];
  return (
    <Screen loading={loading} onRefresh={refresh}>
      {err ? <Card><T style={{ color: C.bad }}>{err}</T></Card> : null}
      <Card>
        <T dim>Total paper value · two books</T>
        <T style={{ fontSize: 34, fontWeight: "800" }}>{usd(total)}</T>
        <T style={{ color: total >= START ? C.good : C.bad, fontWeight: "700" }}>{pct(((total - START) / START) * 100)} since start</T>
        <LineChart height={120} series={[
          { data: pts.map((x: any) => x.main), color: C.accent, label: "Portfolio" },
          { data: pts.map((x: any) => x.explorer), color: C.ok, label: "Explorer" },
        ]} />
      </Card>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        <Tile label="Portfolio book" value={pct(p?.main?.return_pct)} sub={usd(p?.main?.equity)} color={(p?.main?.return_pct ?? 0) >= 0 ? C.good : C.bad} />
        <Tile label="Explorer trades" value={d?.explorer?.open_trades ?? "–"} sub={`open P&L ${usd(d?.explorer?.unrealized_usd)}`} />
        <Tile label="Bitcoin gate" value={p?.btc_gate ? "ON" : "OFF"} sub="market allows holding" color={p?.btc_gate ? C.good : C.bad} />
        <Tile label="Mode" value={p?.mode ?? "–"} sub={p?.mode === "AUTO" ? "acts by itself" : "asks you first"} color={C.accent} />
      </View>
      {p ? (
        <Card title="Waiting for you" right={<Chip text={`${p.pending.length}`} color={p.pending.length ? C.warn : C.dim} />}>
          {p.pending.length === 0 ? <T dim>Nothing to approve right now.</T> : p.pending.map((x: any) => (
            <View key={x.id} style={{ gap: 6, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 8 }}>
              <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
                <Chip text={x.action} color={x.action === "EXIT" ? C.bad : x.action === "ENTER" ? C.good : C.ok} />
                <T style={{ fontWeight: "700" }}>{x.coin}</T>
              </View>
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
      <Card title="Latest alerts">
        {(d?.alerts ?? []).slice(0, 6).map((a: any, i: number) => (
          <View key={i} style={{ borderTopWidth: i ? 1 : 0, borderTopColor: C.line, paddingTop: i ? 6 : 0 }}>
            <T style={{ fontWeight: "600" }}>{a.title.replace(/^Ananta\s*/, "")}</T>
            <T dim>{a.body}</T>
            <T dim style={{ fontSize: 11 }}>{String(a.ts).slice(5, 16).replace("T", " ")} UTC</T>
          </View>
        ))}
      </Card>
      {d?.daily_report ? (
        <Pressable onPress={() => setShowReport(!showReport)}>
          <Card title={`Daily report · ${d.daily_report.name}`} right={<T dim>{showReport ? "hide" : "show"}</T>}>
            {showReport ? <T dim>{d.daily_report.markdown}</T> : <T dim>Tap to read tonight's full report.</T>}
          </Card>
        </Pressable>
      ) : null}
      <T dim style={{ textAlign: "center", fontSize: 11 }}>As of {d?.as_of} · paper only · pull down to refresh</T>
    </Screen>
  );
}
