// The invite page (livetrading247.com/join?code=...): a visitor Madhav invited picks their name and password and lands in
// their own practice book ($1,000 of paper money, empty history). The code in the link is the key; it works once.
import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Platform, StyleSheet, Text, TextInput } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { api } from "../src/api";
import { clearMe } from "../src/visitor";
import { Btn } from "../src/ui";
import { C } from "../src/theme";

export default function Join() {
  const { code } = useLocalSearchParams<{ code?: string }>();
  const [inv, setInv] = useState<{ name: string; email: string } | null>(null);
  const [bad, setBad] = useState("");
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [pw, setPw] = useState("");
  const [pw2, setPw2] = useState("");
  const [msg, setMsg] = useState("");

  useEffect(() => {
    if (!code) { setBad("This link has no invite code. Ask Madhav for a new link."); return; }
    api<{ name: string; email: string }>(`/auth/invite/${encodeURIComponent(String(code))}`)
      .then((r) => { setInv(r); setName(r.name || ""); setEmail(r.email || ""); })
      .catch((e) => setBad(e?.message ?? "This invite link does not work."));
  }, [code]);

  const go = async () => {
    if (pw !== pw2) { setMsg("The two passwords are different."); return; }
    setMsg("Creating your account…");
    try {
      const r = await api<{ token: string }>("/auth/join", { code, name: name.trim(), email: email.trim(), password: pw });
      await SecureStore.setItemAsync("jarvis_token", r.token);
      clearMe();
      router.replace("/welcome");                         // their name, their coins, the tour, their capital
    } catch (e: any) {
      setMsg(e?.message ?? "Could not create the account");
    }
  };

  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={s.wrap}>
      <Text style={s.title}>Ananta</Text>
      {bad ? (
        <>
          <Text style={s.text}>{bad}</Text>
          <Btn label="Go to sign in" kind="secondary" onPress={() => router.replace("/login")} />
        </>
      ) : !inv ? (
        <Text style={s.dim}>Checking your invite…</Text>
      ) : (
        <>
          <Text style={s.text}>Madhav invited you to try his paper-trading assistant. You get your own practice book with $1,000 of
            paper money (not real money). Everything you do stays in your book.</Text>
          <TextInput style={s.in} value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor={C.dim} />
          <TextInput style={[s.in, inv.email ? { color: C.dim } : null]} value={email} onChangeText={setEmail} editable={!inv.email}
            autoCapitalize="none" keyboardType="email-address" placeholder="Your email" placeholderTextColor={C.dim} />
          <TextInput style={s.in} value={pw} onChangeText={setPw} secureTextEntry placeholder="Choose a password (8+ characters)" placeholderTextColor={C.dim} />
          <TextInput style={s.in} value={pw2} onChangeText={setPw2} secureTextEntry placeholder="Password again" placeholderTextColor={C.dim} />
          <Btn label="Create my account" onPress={go} />
          <Text style={s.dim}>{msg}</Text>
        </>
      )}
    </KeyboardAvoidingView>
  );
}

const s = StyleSheet.create({
  wrap: { flex: 1, backgroundColor: C.bg, padding: 24, justifyContent: "center", gap: 12, maxWidth: 480, width: "100%", alignSelf: "center" },
  title: { color: C.text, fontSize: 34, fontWeight: "800" },
  text: { color: C.text, fontSize: 15, lineHeight: 21 },
  dim: { color: C.dim },
  in: { backgroundColor: C.card, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line },
});
