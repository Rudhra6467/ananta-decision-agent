// The public front page of livetrading247.com (signed-out visitors on the web): a product page, not an article. Black and gold
// (the Bat palette, fixed here so the page looks the same for everyone), one headline, two buttons, the app itself in a phone
// frame with live numbers, four live figures, three short reasons, then sign-in. Numbers come from /v3/public/status.
import { useRef } from "react";
import { Linking, Pressable, ScrollView, Text, View, useWindowDimensions } from "react-native";

const K = {
  bg: "#08090B", surface: "#121418", surface2: "#1A1D22", line: "#262930", text: "#F2F0EA", dim: "#9A9DA4", faint: "#6E727A",
  gold: "#F2CF66", goldSoft: "#2B2614", good: "#5CCB92", bad: "#F2796F",
};
export const LANDING_COLORS = K;

const usd = (x?: number | null) => (x == null ? "–" : `${x >= 0 ? "+" : "−"}$${Math.abs(x).toFixed(2)}`);
const n = (x: any, d = "–") => (x == null ? d : String(x));

function Phone({ st }: { st: any }) {
  return (
    <View style={{ width: 300, alignSelf: "center", borderRadius: 44, padding: 10, backgroundColor: "#1B1D21", borderWidth: 1, borderColor: "#34373D",
      shadowColor: K.gold, shadowOpacity: 0.18, shadowRadius: 60, shadowOffset: { width: 0, height: 20 } }}>
      <View style={{ borderRadius: 36, backgroundColor: K.bg, overflow: "hidden", padding: 16, gap: 12 }}>
        <View style={{ alignSelf: "center", width: 90, height: 22, borderRadius: 12, backgroundColor: "#000", marginBottom: 4 }} />
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
          <Text style={{ color: K.text, fontWeight: "800", fontSize: 17 }}>Good evening</Text>
          <View style={{ backgroundColor: K.goldSoft, borderRadius: 999, paddingHorizontal: 9, paddingVertical: 3 }}>
            <Text style={{ color: K.gold, fontSize: 11, fontWeight: "800" }}>PAPER</Text>
          </View>
        </View>
        <Text style={{ color: K.dim, fontSize: 12 }}>Watching {n(st?.coins_watched, "393")} coins · every rule on every coin</Text>

        <View style={{ backgroundColor: K.surface, borderRadius: 18, padding: 14, gap: 8, borderWidth: 1, borderColor: K.line }}>
          <Text style={{ color: K.gold, fontSize: 11, fontWeight: "800", letterSpacing: 1 }}>DECISION CARD · EXAMPLE</Text>
          {[["Found", "A short dip in an uptrend"], ["Why", "History favours this setup on big coins"], ["Wrong if", "It closes under the support zone"],
            ["Doing", "$100 paper trade, stop set"]].map(([k, v]) => (
            <View key={k} style={{ flexDirection: "row", gap: 8 }}>
              <Text style={{ color: K.faint, fontSize: 12, width: 58 }}>{k}</Text>
              <Text style={{ color: K.text, fontSize: 12, flex: 1 }}>{v}</Text>
            </View>
          ))}
        </View>

        <View style={{ flexDirection: "row", gap: 10 }}>
          <View style={{ flex: 1, backgroundColor: K.surface, borderRadius: 16, padding: 12, borderWidth: 1, borderColor: K.line }}>
            <Text style={{ color: K.faint, fontSize: 11 }}>Real trades</Text>
            <Text style={{ color: (st?.real_per_100 ?? 0) >= 0 ? K.good : K.bad, fontSize: 18, fontWeight: "800" }}>{usd(st?.real_per_100)}</Text>
            <Text style={{ color: K.faint, fontSize: 10 }}>per $100</Text>
          </View>
          <View style={{ flex: 1, backgroundColor: K.surface, borderRadius: 16, padding: 12, borderWidth: 1, borderColor: K.line }}>
            <Text style={{ color: K.faint, fontSize: 11 }}>Random entries</Text>
            <Text style={{ color: K.dim, fontSize: 18, fontWeight: "800" }}>{usd(st?.random_per_100)}</Text>
            <Text style={{ color: K.faint, fontSize: 10 }}>the bar to beat</Text>
          </View>
        </View>

        <View style={{ backgroundColor: K.surface, borderRadius: 16, padding: 12, borderWidth: 1, borderColor: K.line, gap: 6 }}>
          <Text style={{ color: K.dim, fontSize: 11 }}>Ask Ananta</Text>
          <Text style={{ color: K.text, fontSize: 12 }}>“Why didn’t you take Solana today?”</Text>
          <Text style={{ color: K.gold, fontSize: 12 }}>Answers from the same rules it trades by.</Text>
        </View>
      </View>
    </View>
  );
}

function Btn({ label, onPress, ghost }: { label: string; onPress: () => void; ghost?: boolean }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => ({ backgroundColor: ghost ? "transparent" : K.gold,
      borderWidth: 1, borderColor: ghost ? "#3A3D44" : K.gold, borderRadius: 12, paddingHorizontal: 22, paddingVertical: 14, opacity: pressed ? 0.75 : 1 })}>
      <Text style={{ color: ghost ? K.text : "#141518", fontWeight: "800", fontSize: 16 }}>{label}</Text>
    </Pressable>
  );
}

function Stat({ value, label }: { value: string; label: string }) {
  return (
    <View style={{ flexGrow: 1, flexBasis: 140, backgroundColor: K.surface, borderRadius: 18, padding: 18, borderWidth: 1, borderColor: K.line, gap: 4 }}>
      <Text style={{ color: K.text, fontSize: 30, fontWeight: "800" }}>{value}</Text>
      <Text style={{ color: K.dim, fontSize: 13 }}>{label}</Text>
    </View>
  );
}

function Reason({ mark, title, text }: { mark: string; title: string; text: string }) {
  return (
    <View style={{ flexGrow: 1, flexBasis: 220, backgroundColor: K.surface, borderRadius: 18, padding: 20, borderWidth: 1, borderColor: K.line, gap: 10 }}>
      <View style={{ width: 38, height: 38, borderRadius: 12, backgroundColor: K.goldSoft, alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: K.gold, fontSize: 18, fontWeight: "800" }}>{mark}</Text>
      </View>
      <Text style={{ color: K.text, fontSize: 18, fontWeight: "800" }}>{title}</Text>
      <Text style={{ color: K.dim, fontSize: 15, lineHeight: 22 }}>{text}</Text>
    </View>
  );
}

export function Landing({ st, contact, signIn }: { st: any; contact: string; signIn: React.ReactNode }) {
  const { width } = useWindowDimensions();
  const wide = width >= 900;
  const scroll = useRef<ScrollView>(null);
  const signY = useRef(0);
  const toSignIn = () => scroll.current?.scrollTo({ y: Math.max(0, signY.current - 24), animated: true });
  const invite = () => Linking.openURL(`mailto:${contact}?subject=Ananta%20invite`);
  const pad = wide ? 48 : 20;
  return (
    <ScrollView ref={scroll} style={{ flex: 1, backgroundColor: K.bg }} contentContainerStyle={{ paddingBottom: 40 }}>
      <View style={{ maxWidth: 1120, width: "100%", alignSelf: "center", paddingHorizontal: pad }}>
        <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between", paddingVertical: 22 }}>
          <Text style={{ color: K.text, fontSize: 18, fontWeight: "800", letterSpacing: 6 }}>ANANT<Text style={{ color: K.gold }}>A</Text></Text>
          <Pressable onPress={toSignIn} accessibilityRole="button" style={{ borderWidth: 1, borderColor: "#3A3D44", borderRadius: 999, paddingHorizontal: 16, paddingVertical: 8 }}>
            <Text style={{ color: K.text, fontWeight: "700" }}>Sign in</Text>
          </Pressable>
        </View>

        <View style={{ flexDirection: wide ? "row" : "column", alignItems: "center", gap: wide ? 56 : 36, paddingTop: wide ? 48 : 20, paddingBottom: 48 }}>
          <View style={{ flex: wide ? 1 : undefined, gap: 22, alignItems: wide ? "flex-start" : "center" }}>
            <View style={{ backgroundColor: K.goldSoft, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6 }}>
              <Text style={{ color: K.gold, fontSize: 12, fontWeight: "800", letterSpacing: 1 }}>BUILT ON CLAUDE · PAPER TRADING</Text>
            </View>
            <Text style={{ color: K.text, fontSize: wide ? 58 : 40, lineHeight: wide ? 64 : 46, fontWeight: "800", textAlign: wide ? "left" : "center" }}>
              The AI trading partner that <Text style={{ color: K.gold }}>shows its work.</Text>
            </Text>
            <Text style={{ color: K.dim, fontSize: wide ? 20 : 17, lineHeight: wide ? 30 : 26, textAlign: wide ? "left" : "center", maxWidth: 520 }}>
              It watches the whole crypto market, explains every idea, and proves each rule on paper before it ever trades.
            </Text>
            <View style={{ flexDirection: "row", gap: 12, flexWrap: "wrap", justifyContent: wide ? "flex-start" : "center" }}>
              <Btn label="Request an invite" onPress={invite} />
              <Btn label="Sign in" onPress={toSignIn} ghost />
            </View>
          </View>
          <View style={{ flex: wide ? 1 : undefined, alignItems: "center" }}>
            <Phone st={st} />
          </View>
        </View>

        <Text style={{ color: K.faint, fontSize: 12, fontWeight: "800", letterSpacing: 1.5, marginBottom: 12 }}>LIVE, RIGHT NOW</Text>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12 }}>
          <Stat value={n(st?.coins_watched, "393")} label="coins watched live" />
          <Stat value={n(st?.trades_scored)} label="paper trades scored" />
          <Stat value={`${n(st?.events)}/${n(st?.goal_events, "10")}`} label="market days toward a verdict" />
          <Stat value={n(st?.mismatches, "0")} label={`mismatches in ${n(st?.rebuilds)} nightly rebuilds`} />
        </View>
        <Text style={{ color: K.faint, fontSize: 13, lineHeight: 19, marginTop: 10 }}>
          Too early to call, and we publish the numbers either way. Day {n(st?.days)} of paper trading.
        </Text>

        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 12, marginTop: 40 }}>
          <Reason mark="◎" title="Watches everything" text="Every coin, every rule, around the clock. You choose: it tells you, asks first, or takes the paper trade." />
          <Reason mark="?" title="Explains every idea" text="What it found, why, what would prove it wrong, and what it is doing. Ask “why?” by voice or text." />
          <Reason mark="✓" title="Proves before it trades" text={`Each rule is tested on years of prices (${n(st?.reviews, "23")} tests so far) and must beat random entries.`} />
        </View>

        <View onLayout={(e) => { signY.current = e.nativeEvent.layout.y; }} style={{ marginTop: 56, alignItems: "center", gap: 14 }}>
          <Text style={{ color: K.text, fontSize: 28, fontWeight: "800", textAlign: "center" }}>Already invited?</Text>
          <View style={{ width: "100%", maxWidth: 420 }}>{signIn}</View>
          <Text style={{ color: K.dim, fontSize: 14, textAlign: "center" }}>
            No invite yet? <Text onPress={invite} style={{ color: K.gold, fontWeight: "700" }}>{contact}</Text>
          </Text>
        </View>

        <Text style={{ color: K.faint, fontSize: 12, lineHeight: 18, textAlign: "center", marginTop: 48 }}>
          Paper money only: no real money is traded, and nothing here is financial advice.{"\n"}© Ananta · livetrading247.com
        </Text>
      </View>
    </ScrollView>
  );
}
