// Zones: price bands (not lines) where the market reacted before. Markets shows which coins are inside a zone now;
// the coin page shows the zones around the price, and while price is inside one, the lookout (chain, your setups, a plan).
import { Pressable, Text, View } from "react-native";
import { router } from "expo-router";
import { askAbout } from "./context";
import { Divider, Pill, T, price } from "./ui";
import { C } from "./theme";

const KIND: Record<string, string> = {
  SWING: "swing level", EXTREME: "52-week extreme", "AVERAGE-50": "50-day average", "AVERAGE-200": "200-day average", BASE: "base edge",
};
const kinds = (z: any) => (z.kinds ?? []).map((k: string) => KIND[k] ?? k).join(" + ") + (z.tier ? ` (${z.tier.toLowerCase()})` : "");
const band = (z: any) => `${price(z.bot)} – ${price(z.top)}`;
const OUT: Record<string, string> = { HELD: C.good, BROKEN: C.bad, OPEN: C.dim };

function History({ h }: { h: string }) {
  return h === "SUPPORTED" ? <Pill text="HISTORY ✓" color={C.good} bg={C.goodSoft} /> : <Pill text="UNPROVEN" color={C.dim} bg={C.card2} />;
}

export function ZonesBoard({ d }: { d: any }) {
  if (!d?.coins?.length) return <T small>{d?.note ?? "Waiting for daily candles."}</T>;
  const inside = d.coins.filter((r: any) => r.in_zone);
  return (
    <View style={{ gap: 4 }}>
      <T small>{inside.length ? `${inside.length} of ${d.coins.length} coins are inside a zone at the ${d.day} close. Inside a zone Ananta starts its lookout.` :
        `No coin is inside a zone at the ${d.day} close.`}</T>
      {inside.map((r: any, i: number) => (
        <View key={r.coin}>
          {i ? <Divider /> : null}
          <Pressable onPress={() => router.push(`/coin/${r.coin}`)} delayLongPress={350}
            onLongPress={() => askAbout({ screen: "markets", label: `${r.coin} is inside a zone: ${kinds(r.inside[0])}` }, `${r.coin} is in a zone. What should I watch?`)}
            style={({ pressed }) => ({ paddingVertical: 8, flexDirection: "row", gap: 10, alignItems: "center", opacity: pressed ? 0.6 : 1 })}>
            <Text style={{ color: C.text, fontWeight: "700", width: 44 }}>{r.coin}</Text>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.text, fontSize: 13 }}>{kinds(r.inside[0])}</Text>
              <Text style={{ color: C.dim, fontSize: 12 }}>{band(r.inside[0])}</Text>
            </View>
            <History h={r.inside[0].history} />
          </Pressable>
        </View>
      ))}
      {(d.recent ?? []).length ? (
        <>
          <Divider />
          <T small>Recent zone entries: {(d.recent ?? []).slice(0, 6).map((v: any) => `${v.coin} ${v.day.slice(5)} ${v.outcome.toLowerCase()}`).join(" · ")}</T>
        </>
      ) : null}
      <T small>History (review #6): zones hold a little more often than random price bands; the 200-day average and overlapping zones the most. Entering a zone is not a trade by itself.</T>
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
          {look.chain ? <T small>Decision chain: {look.chain.summary}</T> : null}
          {(look.your_setups ?? []).filter((x: any) => x.state === "FIRED" || x.state === "CLOSE").map((x: any) => (
            <T key={x.variant} small>Your setup: {x.name} {x.met} of {x.of}</T>
          ))}
          <T small>Watch the reaction inside the zone: a long lower wick, volume, momentum turning, BTC. That is what decides it (review #7 is testing which ones matter).</T>
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
