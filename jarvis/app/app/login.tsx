// The front door. On the website (livetrading247.com) a signed-out visitor sees the product page (src/landing.tsx: black and gold,
// the app in a phone frame, live numbers from /v3/public/status) with sign-in at the bottom. On the phone app it stays a plain
// sign-in screen.
import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, Text, TextInput, View, StyleSheet } from "react-native";
import { login, server, setServer } from "../src/api";
import { registerPush } from "../src/push";
import { clearMe, routeAfterSignIn } from "../src/visitor";
import { Btn } from "../src/ui";
import { C, live } from "../src/theme";
import { LANDING_COLORS as K, Landing } from "../src/landing";

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
  if (Platform.OS !== "web") {
    return (
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={[s.wrap, { justifyContent: "center", padding: 24 }]}>
        <Text style={s.title}>Ananta</Text>
        <Text style={s.dim}>Paper trading only</Text>
        <View style={s.card}>
          <Text style={s.h}>Sign in</Text>
          <TextInput style={s.in} value={url} onChangeText={setUrl} autoCapitalize="none" placeholder="Server address" placeholderTextColor={C.dim} />
          <TextInput style={s.in} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="Name or email" placeholderTextColor={C.dim} />
          <TextInput style={s.in} value={pw} onChangeText={setPw} secureTextEntry placeholder="Password" placeholderTextColor={C.dim} onSubmitEditing={go} />
          <Btn label="Sign in" onPress={go} />
          {msg ? <Text style={s.dim}>{msg}</Text> : null}
          <Text style={[s.dim, { fontSize: 12 }]}>New here? Open the invite link you were sent to create your account.</Text>
        </View>
      </KeyboardAvoidingView>
    );
  }
  const field = { backgroundColor: K.bg, color: K.text, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 13, borderWidth: 1, borderColor: K.line, fontSize: 16 } as const;
  const signIn = (
    <View style={{ backgroundColor: K.surface, borderRadius: 20, borderWidth: 1, borderColor: K.line, padding: 20, gap: 12 }}>
      <TextInput style={field} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="Name or email" placeholderTextColor={K.faint} />
      <TextInput style={field} value={pw} onChangeText={setPw} secureTextEntry placeholder="Password" placeholderTextColor={K.faint} onSubmitEditing={go} />
      <Pressable onPress={go} accessibilityRole="button" style={({ pressed }) => ({ backgroundColor: K.gold, borderRadius: 12, paddingVertical: 14, alignItems: "center", opacity: pressed ? 0.75 : 1 })}>
        <Text style={{ color: "#141518", fontWeight: "800", fontSize: 16 }}>Sign in</Text>
      </Pressable>
      {msg ? <Text style={{ color: K.dim }}>{msg}</Text> : null}
      <Text style={{ color: K.faint, fontSize: 12 }}>New here? Open the invite link you were sent to create your account.</Text>
    </View>
  );
  return <Landing st={st} contact={CONTACT} signIn={signIn} />;
}

const s = live(() => StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg },
  title: { color: C.text, fontSize: 32, fontWeight: "800", lineHeight: 38 },
  h: { color: C.text, fontSize: 17, fontWeight: "700" },
  dim: { color: C.dim },
  card: { backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10 },
  in: { backgroundColor: C.bg, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line },
}));
