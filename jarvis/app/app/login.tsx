import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Platform, Text, TextInput, View, StyleSheet } from "react-native";
import { router } from "expo-router";
import { login, server, setServer } from "../src/api";
import { registerPush } from "../src/push";
import { clearMe, routeAfterSignIn } from "../src/visitor";
import { Btn } from "../src/ui";
import { C } from "../src/theme";

export default function Login() {
  const [url, setUrl] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [msg, setMsg] = useState("");
  useEffect(() => { server().then(setUrl); }, []);
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
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.wrap}>
      <Text style={s.title}>Ananta</Text>
      <Text style={s.dim}>Sign in · paper trading only</Text>
      {Platform.OS !== "web" ? (
        <TextInput style={s.in} value={url} onChangeText={setUrl} autoCapitalize="none" placeholder="Server address" placeholderTextColor={C.dim} />
      ) : null}
      <TextInput style={s.in} value={email} onChangeText={setEmail} autoCapitalize="none" keyboardType="email-address" placeholder="Email" placeholderTextColor={C.dim} />
      <TextInput style={s.in} value={pw} onChangeText={setPw} secureTextEntry placeholder="Password" placeholderTextColor={C.dim} />
      <Btn label="Sign in" onPress={go} />
      <Text style={s.dim}>{msg}</Text>
      <Text style={[s.dim, { fontSize: 12, marginTop: 8 }]}>New here? Open the invite link Madhav sent you to create your account.</Text>
    </KeyboardAvoidingView>
  );
}
const s = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, justifyContent: "center", gap: 12 },
  title: { color: C.text, fontSize: 34, fontWeight: "800" },
  dim: { color: C.dim },
  in: { backgroundColor: C.card, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line },
});
