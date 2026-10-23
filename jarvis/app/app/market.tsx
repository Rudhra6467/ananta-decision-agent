// The Market screen (Madhav, 22 Oct): after sign-in, choose which Ananta to load. Two cards, each with a live one-line status from
// its own backend. The choice is remembered on this device; "Switch market" in the menu brings this screen back.
import { useEffect, useState } from "react";
import { Platform, Pressable, ScrollView, Text, View } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { api } from "../src/api";
import { C, RADIUS, SPACE, TYPE } from "../src/theme";
import { Market, MARKET_NAME, homeOf, setMarket } from "../src/market";

function Card({ m, title, line, sub, color, onPress }: { m: Market; title: string; line: string; sub: string; color: string; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={`Open ${title}`}
      style={({ pressed }) => ({ backgroundColor: C.card, borderRadius: RADIUS.card, borderWidth: 1, borderColor: pressed ? color : C.line, padding: SPACE.card + 4,
        marginBottom: SPACE.gap, borderLeftWidth: 6, borderLeftColor: color })}>
      <Text style={{ color: C.text, fontSize: TYPE.title, fontWeight: "800" }}>{title}</Text>
      <Text style={{ color: C.dim, fontSize: TYPE.body, marginTop: 6 }}>{sub}</Text>
      <Text style={{ color: color, fontSize: TYPE.meta, fontWeight: "700", marginTop: 10 }}>{line}</Text>
    </Pressable>
  );
}

export default function MarketScreen() {
  const top = useSafeAreaInsets().top;
  const [crypto, setCrypto] = useState("checking…");
  const [india, setIndia] = useState("checking…");
  useEffect(() => {
    api("/health", undefined, 8000, true).then((h: any) => setCrypto(h?.ok ? "running · paper · 60-day evidence window" : "not answering")).catch(() => setCrypto("not reachable right now"));
    api("/india/health", undefined, 8000, true).then((h: any) => setIndia(h?.ok ? `running · paper · data through ${h.data_through}` : "no read model yet")).catch(() => setIndia("not reachable right now"));
  }, []);
  const pick = async (m: Market) => { await setMarket(m); router.replace(homeOf(m) as any); };
  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: SPACE.screen, paddingTop: top + 28, maxWidth: 720, alignSelf: "center", width: "100%" }}>
      <Text style={{ color: C.text, fontSize: TYPE.number, fontWeight: "800" }}>Which Ananta?</Text>
      <Text style={{ color: C.dim, fontSize: TYPE.body, marginTop: 6, marginBottom: 22 }}>
        One sign-in, one place. Each market has its own brain, books and voice; nothing is shared between them. You can switch any time from the menu.
      </Text>
      <Card m="crypto" title={MARKET_NAME.crypto} color={C.accent} line={crypto} onPress={() => pick("crypto")}
        sub="NDAX paper books, the watches, Ask Ananta and voice, the evidence layer." />
      <Card m="india" title={MARKET_NAME.india} color={C.india} line={india} onPress={() => pick("india")}
        sub="NSE stock and index paper books, the reference-traders league, the research gate, and the Telugu brief for father mode." />
      {Platform.OS === "web" ? <Text style={{ color: C.faint, fontSize: TYPE.meta, marginTop: 10 }}>Tip: the choice is kept on this device.</Text> : null}
    </ScrollView>
  );
}
