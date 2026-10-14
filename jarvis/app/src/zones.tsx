// Zones: price bands (not lines) where the market reacted before. Markets shows which coins are inside a zone now;
// the coin page shows the zones around the price, and while price is inside one, the lookout (chain, your setups, a plan).
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { askAbout } from "./context";
import { Divider, Pill, T, price } from "./ui";
import { C, live } from "./theme";

const KIND: Record<string, string> = {
  SWING: "swing level", EXTREME: "52-week extreme", "AVERAGE-50": "50-day average", "AVERAGE-200": "200-day average", BASE: "base edge",
};
const kinds = (z: any) => (z.kinds ?? []).map((k: string) => KIND[k] ?? k).join(" + ") + (z.tier ? ` (${z.tier.toLowerCase()})` : "");
const band = (z: any) => `${price(z.bot)} – ${price(z.top)}`;
const OUT: Record<string, string> = live(() => ({ HELD: C.good, BROKEN: C.bad, OPEN: C.dim }));

function History({ h }: { h: string }) {
  return h === "SUPPORTED" ? <Pill text="HISTORY ✓" color={C.good} bg={C.goodSoft} /> : <Pill text="UNPROVEN" color={C.dim} bg={C.card2} />;
}

const LEVEL: Record<string, { text: string; color: string; bg: string }> = live(() => ({
  HIGH: { text: "LOOK NOW", color: C.good, bg: C.goodSoft }, WATCH: { text: "WATCH", color: C.warn, bg: C.warnSoft }, LOW: { text: "QUIET", color: C.dim, bg: C.card2 },
}));

export function ZonesBoard({ d }: { d: any }) {
  if (!d?.coins?.length) return <T small>{d?.note ?? "Waiting for daily candles."}</T>;
  const inside = d.coins.filter((r: any) => r.attention?.level !== "LOW");
  return (
    <View style={{ gap: 4 }}>
      <T small>{inside.length ? `Where Ananta is looking at the ${d.day} close (${(d.in_zone ?? []).length} of ${d.coins.length} coins sit inside a zone):` :
        `Nothing needs a closer look at the ${d.day} close.`}</T>
      {inside.map((r: any, i: number) => (
        <View key={r.coin}>
          {i ? <Divider /> : null}
          <Pressable onPress={() => router.push(`/coin/${r.coin}`)} delayLongPress={350}
            onLongPress={() => askAbout({ screen: "markets", label: `${r.coin}: attention ${r.attention.level}, ${r.attention.why.join("; ")}` }, `${r.coin} is in a zone. What should I watch?`)}
            style={({ pressed }) => ({ paddingVertical: 8, flexDirection: "row", gap: 10, alignItems: "center", opacity: pressed ? 0.6 : 1 })}>
            <Text style={{ color: C.text, fontWeight: "700", width: 44 }}>{r.coin}</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.text, fontSize: 13 }}>{r.inside[0] || r.tested ? `${kinds(r.inside[0] ?? r.tested)} · ${band(r.inside[0] ?? r.tested)}` : "near a zone"}</Text>
              <Text style={{ color: C.dim, fontSize: 12 }} numberOfLines={2}>{(r.attention?.why ?? []).slice(1).join(" · ")}</Text>
            </View>
            <Pill text={LEVEL[r.attention.level].text} color={LEVEL[r.attention.level].color} bg={LEVEL[r.attention.level].bg} />
          </Pressable>
        </View>
      ))}
      {(d.recent ?? []).length ? (
        <>
          <Divider />
          <T small>Recent zone entries: {(d.recent ?? []).slice(0, 6).map((v: any) => `${v.coin} ${v.day.slice(5)} ${v.outcome.toLowerCase()}`).join(" · ")}</T>
        </>
      ) : null}
      <T small>History: zones hold a little more often than random price bands (the 200-day average and overlapping zones the most). Inside a zone, the market decided most: with BTC above its 50-day average zones held 68% of the time vs 50% (2018-23). Wicks and volume added nothing on their own.</T>
    </View>
  );
}

function ZoneRow({ z, label }: { z: any; label: string }) {
  return (
    <View style={{ flexDirection: "row", gap: 8, alignItems: "center", paddingVertical: 4 }}>
      <View style={{ flex: 1 }}>
        <Text style={{ color: C.faint, fontSize: 11, fontWeight: "700", letterSpacing: 0.5 }}>{label}</Text>
        <Text style={{ color: C.text, fontSize: 13, fontWeight: "600" }}>{band(z)} <Text style={{ color: C.faint, fontWeight: "400" }}>
          {z.state === "INSIDE" ? "· price is here" : `· ${z.distance_pct > 0 ? "+" : ""}${z.distance_pct}%`}</Text></Text>
        <Text style={{ color: C.dim, fontSize: 12 }}>{kinds(z)}{z.held != null ? ` · held ${z.held} of ${z.touches} visits` : ""}</Text>
      </View>
      <History h={z.history} />
    </View>
  );
}

export function ZonesCoin({ d }: { d: any }) {
  if (!d) return <T small>No zone map for this coin yet (it needs a year of daily candles).</T>;
  const look = d.lookout;
  return (
    <View style={{ gap: 4 }}>
      {d.next_resistance ? <ZoneRow z={d.next_resistance} label="NEXT ZONE ABOVE" /> : null}
      {(d.inside ?? []).map((z: any, i: number) => <ZoneRow key={i} z={z} label="INSIDE NOW" />)}
      {d.next_support ? <ZoneRow z={d.next_support} label="NEXT ZONE BELOW" /> : null}
      {look ? (
        <>
          <Divider />
          <Text style={{ color: C.faint, fontSize: 11, fontWeight: "700", letterSpacing: 0.6 }}>LOOKOUT (PRICE IS IN A ZONE)</Text>
          {look.plan ? <T small>The zone held if {look.plan.held_if}; it is wrong if {look.plan.wrong_if} (a stop there is {look.plan.stop_pct}% away).</T> : null}
          {(look.reactions ?? []).map((x: any) => (
            <View key={x.id} style={{ flexDirection: "row", gap: 6 }}>
              <Text style={{ color: x.present ? C.text : C.faint, width: 18, fontWeight: "800" }}>{x.present ? "✓" : "·"}</Text>
              <Text style={{ flex: 1, color: x.present ? C.text : C.faint, fontSize: 12 }}>{x.name}
                <Text style={{ color: x.history === "PASS" ? C.good : C.faint }}>{x.history === "PASS" ? "  · history: matters" : "  · history: adds nothing alone"}</Text></Text>
            </View>
          ))}
          {look.news ? <T small>News ({look.news.day}): <Text style={{ color: look.news.verdict === "BLOCK" ? C.bad : look.news.verdict === "CAUTION" ? C.warn : C.good, fontWeight: "700" }}>{look.news.verdict}</Text> · {look.news.why}</T> : null}
          {look.chain ? <T small>Decision chain: {look.chain.summary}</T> : null}
          {(look.your_setups ?? []).filter((x: any) => x.state === "FIRED" || x.state === "CLOSE").map((x: any) => (
            <T key={x.variant} small>Your setup: {x.name} {x.met} of {x.of}</T>
          ))}
          {look.attention ? <T small>Attention: {look.attention.level === "HIGH" ? "look now" : look.attention.level === "WATCH" ? "watch" : "quiet"}. {look.attention.why.join("; ")}.</T> : null}
        </>
      ) : null}
      {(d.visits ?? []).length ? (
        <>
          <Divider />
          {(d.visits ?? []).slice(0, 4).map((v: any, i: number) => (
            <Text key={i} style={{ color: C.dim, fontSize: 12 }}>Entered {band(v)} on {v.day}: <Text style={{ color: OUT[v.outcome] ?? C.dim, fontWeight: "700" }}>{v.outcome.toLowerCase()}</Text></Text>
          ))}
        </>
      ) : null}
    </View>
  );
}
