// The front door. On the website (livetrading247.com) someone who is not signed in first sees what Ananta is, a few honest live
// numbers (/v3/public/status: paper only, results against random, tests and rebuilds), how to get an invite, then sign-in.
// On the phone app it stays a plain sign-in screen.
import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Linking, Platform, ScrollView, Text, TextInput, View, StyleSheet } from "react-native";
import { login, server, setServer } from "../src/api";
import { registerPush } from "../src/push";
import { clearMe, routeAfterSignIn } from "../src/visitor";
import { Btn } from "../src/ui";
import { C, live } from "../src/theme";

const CONTACT = "vamsimadhav@livetrading247.com";

export default function Login() {
  const [url, setUrl] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [msg, setMsg] = useState("");
  const [st, setSt] = useState<any>(null);
  useEffect(() => {
    server().then((u) => {
      setUrl(u);
      if (Platform.OS === "web") fetch(`${u}/v3/public/status`).then((r) => r.json()).then(setSt).catch(() => {});
    });
  }, []);
  const go = async () => {
    setMsg("Signing in…");
    try {
      await setServer(url.trim());
      await login(email.trim(), pw);
      registerPush().then((m) => console.log(m)).catch(() => {});
      clearMe();
      await routeAfterSignIn();
    } catch (e: any) {
      setMsg(e?.message ?? "Could not sign in");
    }
  };
  const signIn = (
    <View style={s.card}>
      <Text style={s.h}>Sign in</Text>
      {Platform.OS !== "web" ? (
        <TextInput style={s.in} value={url} onChangeText={setUrl} autoCapitalize="none" placeholder="Server address" placeholderTextColor={C.dim} />
      ) : null}
      <TextInput style={s.in} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="Name or email" placeholderTextColor={C.dim} />
      <TextInput style={s.in} value={pw} onChangeText={setPw} secureTextEntry placeholder="Password" placeholderTextColor={C.dim} onSubmitEditing={go} />
      <Btn label="Sign in" onPress={go} />
      {msg ? <Text style={s.dim}>{msg}</Text> : null}
      <Text style={[s.dim, { fontSize: 12 }]}>New here? Open the invite link you were sent to create your account.</Text>
    </View>
  );
  if (Platform.OS !== "web") {
    return (
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={[s.wrap, { justifyContent: "center", padding: 24 }]}>
        <Text style={s.title}>Ananta</Text>
        <Text style={s.dim}>Paper trading only</Text>
        {signIn}
      </KeyboardAvoidingView>
    );
  }
  const n = (x: any, d = "–") => (x == null ? d : String(x));
  return (
    <ScrollView style={s.wrap} contentContainerStyle={{ padding: 24, paddingTop: 48, gap: 18, maxWidth: 720, width: "100%", alignSelf: "center" }}>
      <View style={{ gap: 8 }}>
        <Text style={s.kicker}>ANANTA · BUILT ON CLAUDE</Text>
        <Text style={s.title}>An AI trading partner that shows its work.</Text>
        <Text style={s.lead}>
          Ananta watches the crypto market for you, finds trade setups, and explains every idea: what it found, why, what would prove it
          wrong, and what it is doing about it. It runs on paper money while it proves itself.
        </Text>
      </View>

      <View style={{ gap: 10 }}>
        <Point title="Watches for you" text="Pick your coins. Ananta checks them every 15 minutes, day and night, and tells you, asks you first, or takes the paper trade: your choice, per watch." />
        <Point title="Shows its work" text="Every idea arrives as a decision card. Ask “why?” at any time and it answers from the same seven-step decision chain it trades by, by voice or text." />
        <Point title="Proves before it trades" text={`A rule is used only after a test on years of prices (${n(st?.reviews, "23")} tests so far). Every night the whole day is rebuilt from raw prices to check each decision (${n(st?.rebuilds)} rebuilds, ${n(st?.mismatches)} mismatches).`} />
      </View>

      <View style={s.card}>
        <Text style={s.h}>Where it stands today, live</Text>
        <Text style={s.body}>
          Day {n(st?.days)} of live paper trading · {n(st?.trades_scored)} trades scored · {n(st?.events)} of {n(st?.goal_events, "10")} independent market events needed for a verdict.
        </Text>
        <Text style={s.body}>
          Real paper trades: {st?.real_per_100 != null ? `${st.real_per_100 >= 0 ? "+" : "-"}$${Math.abs(st.real_per_100).toFixed(2)}` : "–"} per $100 traded.
          Random entries, the bar to beat: {st?.random_per_100 != null ? `${st.random_per_100 >= 0 ? "+" : "-"}$${Math.abs(st.random_per_100).toFixed(2)}` : "–"}.
        </Text>
        <Text style={s.dimSmall}>Too early to call; we publish the numbers either way. Paper money only: no real money is traded, and nothing here is financial advice.</Text>
      </View>

      <View style={s.card}>
        <Text style={s.h}>Try it</Text>
        <Text style={s.body}>Ananta is in a small private pilot. To get an invite, or to talk about the project, write to us.</Text>
        <Text onPress={() => Linking.openURL(`mailto:${CONTACT}?subject=Ananta`)} style={[s.body, { color: C.accent, fontWeight: "700" }]}>{CONTACT}</Text>
      </View>

      {signIn}
      <Text style={[s.dimSmall, { textAlign: "center", marginBottom: 30 }]}>© Ananta · livetrading247.com</Text>
    </ScrollView>
  );
}

function Point({ title, text }: { title: string; text: string }) {
  return (
    <View style={s.card}>
      <Text style={s.h}>{title}</Text>
      <Text style={s.body}>{text}</Text>
    </View>
  );
}

const s = live(() => StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  kicker: { color: C.accent, fontSize: 12, fontWeight: "800", letterSpacing: 1 },
  title: { color: C.text, fontSize: 32, fontWeight: "800", lineHeight: 38 },
  lead: { color: C.text, fontSize: 17, lineHeight: 25 },
  h: { color: C.text, fontSize: 17, fontWeight: "700" },
  body: { color: C.text, fontSize: 15, lineHeight: 22 },
  dim: { color: C.dim },
  dimSmall: { color: C.dim, fontSize: 12, lineHeight: 17 },
  card: { backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10 },
  in: { backgroundColor: C.bg, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line },
}));
