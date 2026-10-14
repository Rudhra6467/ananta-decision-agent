// Madhav's own three buy setups (capitulation at the lows, higher-low retest, quiet base), read on every coin at each daily close.
// Markets shows which coins are showing one (or are one sign away); the coin page shows each setup's checklist and a news check button.
// These are evidence for Madhav, never orders: the history line under them says what review #5 found.
import { useState } from "react";
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { api } from "./api";
import { askAbout } from "./context";
import { Btn, Divider, Expand, Pill, T } from "./ui";
import { C, live } from "./theme";

const STATE: Record<string, { text: string; color: string; bg: string }> = live(() => ({
  FIRED: { text: "SHOWING", color: C.good, bg: C.goodSoft },
  CLOSE: { text: "1 SIGN MISSING", color: C.warn, bg: C.warnSoft },
  NO: { text: "NOT NOW", color: C.dim, bg: C.card2 },
  NO_DATA: { text: "NO DATA", color: C.faint, bg: C.card2 },
}));
const HISTORY: Record<string, string> = {
  SUPPORTED: "history supports it", NOT_SUPPORTED: "history 2018-23: no better than a random day", NOT_CONFIRMED: "worked 2018-23, not since",
  INSUFFICIENT: "too few cases in history to judge", UNTESTED: "not tested yet",
};
const NEWS: Record<string, string> = live(() => ({ CLEAR: C.good, CAUTION: C.warn, BLOCK: C.bad }));

function Check({ ok }: { ok: boolean }) {
  return <Text style={{ color: ok ? C.good : C.bad, width: 18, fontWeight: "800" }}>{ok ? "✓" : "✗"}</Text>;
}

export function ReadsBoard({ d }: { d: any }) {
  if (!d?.coins?.length) return <T small>{d?.note ?? "Waiting for daily candles."}</T>;
  const live = d.coins.filter((r: any) => r.best?.state === "FIRED" || r.best?.state === "CLOSE");
  const quiet = d.coins.filter((r: any) => !live.includes(r)).map((r: any) => r.coin);
  return (
    <View style={{ gap: 4 }}>
      <T small>Your three buy setups, checked on every coin at the {d.day} daily close. Evidence for you, not orders.</T>
      {live.map((r: any, i: number) => (
        <View key={r.coin}>
          {i ? <Divider /> : null}
          <Pressable onPress={() => router.push(`/coin/${r.coin}`)} delayLongPress={350}
            onLongPress={() => askAbout({ screen: "markets", label: `Your setups on ${r.coin}: ${r.best.name} ${r.best.met}/${r.best.of}` }, `Is ${r.coin} setting up like my own buys?`)}
            style={({ pressed }) => ({ paddingVertical: 8, flexDirection: "row", gap: 10, alignItems: "center", opacity: pressed ? 0.6 : 1 })}>
            <Text style={{ color: C.text, fontWeight: "700", width: 44 }}>{r.coin}</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.text, fontSize: 13 }}>{r.best.name} <Text style={{ color: C.faint }}>· {r.best.met} of {r.best.of}</Text></Text>
              <Text style={{ color: C.dim, fontSize: 12 }}>{r.best.like}</Text>
            </View>
            <Pill text={STATE[r.best.state].text} color={STATE[r.best.state].color} bg={STATE[r.best.state].bg} />
          </Pressable>
        </View>
      ))}
      {quiet.length ? <T small>{live.length ? "Nothing close on " : "Nothing close on any coin: "}{quiet.join(", ")}.</T> : null}
      <T small>History (2018-2023): none of the three beat a random day on its own. Since 2024 all three did better, but on few cases.</T>
    </View>
  );
}

export function ReadsCoin({ row, coin, guest }: { row: any; coin: string; guest?: boolean }) {
  const [news, setNews] = useState<any>(null);
  const [busy, setBusy] = useState(false);
  if (!row) return <T small>No daily candles for this coin yet.</T>;
  const check = async () => {
    setBusy(true);
    try { setNews(await api(`/v3/reads/${coin}/news`, {}, 90000)); }
    catch (e: any) { setNews({ verdict: "NOT_CHECKED", why: e?.message ?? String(e) }); }
    finally { setBusy(false); }
  };
  return (
    <View style={{ gap: 6 }}>
      <T small>At the {row.day} daily close. Each setup comes from one of your SOL buys.</T>
      {row.reads.map((r: any) => (
        <Expand key={r.variant} title={`${r.name}${r.variant === "M3b" ? " (breakout)" : ""}`}
          sub={`${r.like} · ${r.of ? `${r.met} of ${r.of}` : "no data"} · ${HISTORY[r.history] ?? r.history}`}
          right={<Pill text={STATE[r.state]?.text ?? r.state} color={STATE[r.state]?.color} bg={STATE[r.state]?.bg} />}
          start={r.state === "FIRED"}>
          <View style={{ gap: 4 }}>
            {r.conditions.map((c: any) => (
              <View key={c.name} style={{ flexDirection: "row", gap: 6 }}>
                <Check ok={c.ok} />
                <View style={{ flex: 1 }}>
                  <Text style={{ color: C.text, fontSize: 13, fontWeight: "600" }}>{c.name}</Text>
                  <Text style={{ color: C.dim, fontSize: 12 }}>{c.found} <Text style={{ color: C.faint }}>(needs {c.need})</Text></Text>
                </View>
              </View>
            ))}
            {r.stop_pct != null ? <T small>If it fails: the stop would be {r.stop_pct}% from the close (under the structure, not a tight 2%).</T> : null}
          </View>
        </Expand>
      ))}
      <Divider />
      <T small>Last look before a buy: an AI reads the last few days of news about {coin} itself and flags real damage (hacks, outages, regulators), not market fear.</T>
      {news ? (
        <View style={{ gap: 4 }}>
          <Text style={{ color: NEWS[news.verdict] ?? C.dim, fontWeight: "800" }}>News: {news.verdict}</Text>
          {news.why ? <T small>{news.why}</T> : null}
          {(news.damage ?? []).slice(0, 3).map((x: any, i: number) => <T key={`d${i}`} small>⚠ {x.headline}{x.note ? ` (${x.note})` : ""}</T>)}
          {(news.good ?? []).slice(0, 2).map((x: any, i: number) => <T key={`g${i}`} small>+ {x.headline}</T>)}
        </View>
      ) : null}
      {guest ? <T small>The news check uses Madhav's AI budget, so it is locked in practice mode.</T> :
        <Btn small kind="secondary" label={busy ? "Checking the news…" : news ? "Check again" : "Check the news (AI, about 1¢)"} onPress={busy ? () => {} : check} />}
    </View>
  );
}
