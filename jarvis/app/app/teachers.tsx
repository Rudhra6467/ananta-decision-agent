// The YouTube teachers, tested (Madhav, 25 Oct 2026: "extract all the information that will be useful for Indian market ... test all the
// needed strategies and keep their results ... keep a track of them for forward evidence"). Every claim from the two libraries is a card:
// what he says, what the test found in plain words, and the live tracking. Reads /v3/teachers (India service, records repo summary).
import { useCallback, useMemo, useState } from "react";
import { Pressable, Text, View } from "react-native";
import { Stack, useFocusEffect } from "expo-router";
import { askAbout, setScreen } from "../src/context";
import { Spot } from "../src/spotlight";
import { Busy, Card, Divider, ErrorBox, Screen, Segmented, T } from "../src/ui";
import { useData } from "../src/useData";
import { C, live } from "../src/theme";

const TONE: Record<string, [string, string]> = live(() => ({
  PASSED: [C.good, C.goodSoft], MIXED: [C.accent, C.accentSoft], "WRONG WAY": [C.bad, C.badSoft], "DID NOT HOLD": [C.dim, C.card2],
  "NOT ENOUGH DATA": [C.warn, C.warnSoft], MEASURED: [C.accent, C.accentSoft],
}));
const FILTERS = [{ key: "all", label: "All" }, { key: "held", label: "Held up" }, { key: "wrong", label: "Wrong way" }, { key: "no", label: "Not proven" },
  { key: "live", label: "Tracking live" }, { key: "other", label: "Waiting" }];
const inFilter = (c: any, f: string) => f === "all" || (f === "held" && ["PASSED", "MIXED"].includes(c.verdict)) || (f === "wrong" && c.verdict === "WRONG WAY")
  || (f === "no" && ["DID NOT HOLD", "NOT ENOUGH DATA"].includes(c.verdict)) || (f === "live" && c.status === "FORWARD")
  || (f === "other" && !["TEST", "FORWARD", "DESCRIPTIVE"].includes(c.status));
const pctx = (x: any) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${(x * 100).toFixed(2)}%`);
const tx = (x: any) => (x == null ? "–" : `${x >= 0 ? "+" : ""}${Number(x).toFixed(1)}`);
const inr = (x: any) => (x == null ? "–" : `${x < 0 ? "−" : "+"}₹${Math.abs(Math.round(x)).toLocaleString("en-IN")}`);
// "H02_bn_1300_s30_cost_x1520" -> "H02 · Bank Nifty 13:00 · stop 30% · stop to cost · out 15:20"
function nameOf(id: string): string {
  const p = id.split("_");
  const out: string[] = [];
  for (const x of p) {
    if (/^H\d+$/.test(x)) out.push(x);
    else if (x === "grid" || x === "stopgrid") out.push(x === "grid" ? "entry-time test" : "stop-width test");
    else if (x === "bn" || x === "banknifty") out.push("Bank Nifty");
    else if (x === "nf" || x === "nifty") out.push("Nifty");
    else if (/^\d{4}$/.test(x)) out.push(`${x.slice(0, 2)}:${x.slice(2)}`);
    else if (/^s\d+$/.test(x)) out.push(`stop ${x.slice(1)}%`);
    else if (/^p\d+$/.test(x)) out.push(`stop ${x.slice(1)} pts`);
    else if (/^x\d{4}$/.test(x)) out.push(`out ${x.slice(1, 3)}:${x.slice(3)}`);
    else if (x === "cost") out.push("stop to cost");
    else if (x === "exp") out.push("expiry day");
    else if (x === "eve") out.push("expiry-eve strangle");
    else if (x === "weekly") out.push("weekly straddle");
    else if (x === "nextweek") out.push("next week's straddle");
    else out.push(x);
  }
  return out.join(" · ");
}
const ask = (label: string, q: string) => askAbout({ screen: "teachers", label }, q);

export default function Teachers() {
  const { data: d, err, loading, reload } = useData("/v3/teachers", 600000);
  const [who, setWho] = useState("TWT");
  const [f, setF] = useState("all");
  const [open, setOpen] = useState<string | null>(null);
  useFocusEffect(useCallback(() => { setScreen({ screen: "teachers", label: "The YouTube teachers, tested: every claim as a card, what held, what came out the wrong way, what is tracked live" }); }, []));
  const head = <Stack.Screen options={{ headerShown: true, title: "Teachers, tested", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false, headerTintColor: C.text, headerBackTitle: "Evidence" }} />;
  const cards = useMemo(() => (d?.cards ?? []).filter((c: any) => c.teacher === who), [d, who]);
  if (!d && loading) return <>{head}<Busy /></>;
  if (!d || !d.ready) return <>{head}<Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "The teachers' results are not ready yet."} /></Screen></>;
  const tested = cards.filter((c: any) => c.status === "TEST");
  const n = (v: string[]) => tested.filter((c: any) => v.includes(c.verdict)).length;
  const list = cards.filter((c: any) => inFilter(c, f));
  const teacher = d.teachers?.[who] ?? {};
  const fwd = (d.forward_rows ?? []).filter((r: any) => (who === "OPT") && r.card);
  return (
    <>{head}
      <Screen loading={loading} onRefresh={reload}>
        <T dim>Every claim from the two YouTube libraries, written as an exact rule before any result was seen, tested on 2000-2017 and checked again on 2018-2023 at a strict bar. 2024 onward stays sealed. Nothing here trades.</T>
        <Segmented value={who} onChange={(k) => { setWho(k); setOpen(null); }} options={[{ key: "TWT", label: "Trade With Trend" }, { key: "OPT", label: "Optionables" }]} />
        <Spot id="teachers.score">
          <Card title={teacher.name} sub={`${cards.length} claims · ${tested.length} backtested · ${teacher.videos ?? ""}`}>
            <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
              {[["Held up", n(["PASSED", "MIXED"]), C.good], ["Wrong way", n(["WRONG WAY"]), C.bad], ["Did not hold", n(["DID NOT HOLD"]), C.dim], ["Too little data", n(["NOT ENOUGH DATA"]), C.warn],
                ["Tracking live", cards.filter((c: any) => c.status === "FORWARD").length, C.accent]].map(([label, v, col]: any) => (
                <View key={label} style={{ backgroundColor: C.card2, borderRadius: 10, paddingVertical: 8, paddingHorizontal: 10, minWidth: 92 }}>
                  <Text style={{ color: col, fontSize: 20, fontWeight: "700" }}>{v}</Text>
                  <Text style={{ color: C.dim, fontSize: 12 }}>{label}</Text>
                </View>
              ))}
            </View>
          </Card>
        </Spot>
        {who === "TWT" && d.survivors?.length ? (
          <Spot id="teachers.held">
            <Card title="What held up" sub="Use as filters, not as buy signals; each is tracked on live sessions from 26 Oct">
              {d.survivors.filter((s: any) => s.id.startsWith("TWT")).map((s: any, i: number) => (
                <View key={s.id}>{i ? <Divider /> : null}
                  <Text style={{ color: C.text, fontWeight: "600", fontSize: 14, paddingTop: 6 }}>{s.title}</Text>
                  <Text style={{ color: C.dim, fontSize: 13, lineHeight: 19, paddingBottom: 6 }}>{s.plain}</Text>
                </View>
              ))}
            </Card>
          </Spot>
        ) : null}
        {who === "OPT" && fwd.length ? (
          <Spot id="teachers.live">
            <Card title="His option systems on live prices" sub="The recorder's 1-minute prices, one lot, full charges. First look at 60 forward sessions; the sessions recorded before the cards are shown apart.">
              {fwd.slice(0, 40).map((r: any, i: number) => (
                <View key={r.id}>{i ? <Divider /> : null}
                  <View style={{ flexDirection: "row", paddingVertical: 6, gap: 8 }}>
                    <Text style={{ color: C.text, fontSize: 13, flex: 1 }} numberOfLines={1}>{nameOf(r.id)}</Text>
                    <Text style={{ color: C.faint, fontSize: 12 }}>{r.forward_sessions} live · {r.before_cards_sessions} before</Text>
                    <Text style={{ color: (r.total_inr ?? 0) >= 0 ? C.good : C.bad, fontSize: 13, fontWeight: "600", minWidth: 76, textAlign: "right" }}>{inr(r.total_inr)}</Text>
                  </View>
                </View>
              ))}
            </Card>
          </Spot>
        ) : null}
        <Segmented value={f} onChange={setF} options={FILTERS.map((x) => ({ key: x.key, label: `${x.label} ${cards.filter((c: any) => inFilter(c, x.key)).length}` }))} />
        <Card>
          {list.map((c: any, i: number) => {
            const [col, soft] = TONE[c.verdict] ?? [C.dim, C.card2];
            const isOpen = open === c.id;
            return (
              <View key={c.id}>
                {i ? <Divider /> : null}
                <Pressable onPress={() => setOpen(isOpen ? null : c.id)} onLongPress={() => ask(`${c.id} ${c.title}`, `Explain ${c.id} (${c.title}) simply: what does the teacher claim, what did the test find, and should it change anything we do?`)}
                  style={({ pressed }) => ({ paddingVertical: 10, gap: 4, opacity: pressed ? 0.6 : 1 })}>
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 8 }}>
                    <Text style={{ color: C.faint, fontSize: 12, width: 54 }}>{c.id.replace("TWT-", "").replace("OPT-", "")}</Text>
                    <Text style={{ color: C.text, fontWeight: "600", fontSize: 14, flex: 1 }}>{c.title}</Text>
                    <View style={{ backgroundColor: soft, borderRadius: 8, paddingHorizontal: 7, paddingVertical: 2 }}><Text style={{ color: col, fontSize: 11, fontWeight: "700" }}>{(c.word ?? c.verdict).toUpperCase()}</Text></View>
                  </View>
                  <Text style={{ color: C.dim, fontSize: 13, lineHeight: 19 }} numberOfLines={isOpen ? undefined : 2}>{c.plain}</Text>
                </Pressable>
                {isOpen ? (
                  <View style={{ gap: 6, paddingBottom: 10 }}>
                    <Text style={{ color: C.faint, fontSize: 12, lineHeight: 17 }}>The rule as tested: {c.rule}</Text>
                    {(c.variants ?? []).map((v: any) => (
                      <View key={v.variant} style={{ flexDirection: "row", gap: 6 }}>
                        <Text style={{ color: C.text, fontSize: 12, flex: 1 }} numberOfLines={1}>{v.variant}</Text>
                        <Text style={{ color: C.faint, fontSize: 11, width: 118, textAlign: "right" }}>{pctx(v.dev?.[0])} (t {tx(v.dev?.[1])})</Text>
                        <Text style={{ color: C.faint, fontSize: 11, width: 118, textAlign: "right" }}>{pctx(v.val?.[0])} (t {tx(v.val?.[1])})</Text>
                        <Text style={{ color: (TONE[v.verdict === "VALIDATED" || v.verdict === "CONDITIONAL" ? "PASSED" : v.verdict === "OPPOSITE" ? "WRONG WAY" : "DID NOT HOLD"] ?? [C.dim])[0], fontSize: 11, width: 92, textAlign: "right" }}>{v.verdict}</Text>
                      </View>
                    ))}
                    {c.variants?.length ? <Text style={{ color: C.faint, fontSize: 11 }}>Columns: 2000-2017, then 2018-2023 (mean difference per trade or per session, and its t).</Text> : null}
                    {c.note ? <Text style={{ color: C.faint, fontSize: 12 }}>{c.note}</Text> : null}
                    <Pressable onPress={() => ask(`${c.id} ${c.title}`, `Explain ${c.id} (${c.title}) simply: what does the teacher claim, what did the test find, and should it change anything we do?`)}>
                      <Text style={{ color: C.accent, fontSize: 13, fontWeight: "600" }}>Ask Ananta about this ›</Text>
                    </Pressable>
                  </View>
                ) : null}
              </View>
            );
          })}
        </Card>
        <T small faint>Bars: z {d.bars?.TWT} (Trade With Trend) and {d.bars?.OPT} (Optionables), across every version tried. {d.variants_tested} versions tested. Registered {d.registered}.</T>
      </Screen>
    </>
  );
}
