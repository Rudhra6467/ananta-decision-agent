// Cockpit › Additional features › Change password (Madhav only, Oct 12). The current password first, then the new one twice.
// Every other device signed in to his account is signed out; this one stays in.
import { useState } from "react";
import { TextInput } from "react-native";
import { Stack } from "expo-router";
import { api } from "../src/api";
import { confirmWithFaceId } from "../src/guard";
import { Btn, Card, Screen, T } from "../src/ui";
import { C } from "../src/theme";

export default function PasswordPage() {
  const [cur, setCur] = useState("");
  const [n1, setN1] = useState("");
  const [n2, setN2] = useState("");
  const [msg, setMsg] = useState("");
  const [ok, setOk] = useState(false);
  const field = { backgroundColor: C.card2, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line, marginBottom: 8 } as const;
  const go = async () => {
    setOk(false);
    if (n1.length < 10) { setMsg("The new password needs at least 10 characters."); return; }
    if (n1 !== n2) { setMsg("The two new passwords are different."); return; }
    if (!(await confirmWithFaceId("Change your password?", "Every other device signed in to your account will be signed out."))) return;
    setMsg("Changing…");
    try {
      const r = await api<{ signed_out_elsewhere: number }>("/v3/account/password", { current: cur, new: n1 });
      setCur(""); setN1(""); setN2(""); setOk(true);
      setMsg(`Password changed. ${r.signed_out_elsewhere ? `${r.signed_out_elsewhere} other sign-in${r.signed_out_elsewhere > 1 ? "s were" : " was"} ended.` : "No other device was signed in."}`);
    } catch (e: any) { setMsg(e?.message ?? "Not changed"); }
  };
  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: "Change password", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
        headerTintColor: C.text, headerBackTitle: "Back" }} />
      <Screen loading={false} onRefresh={() => {}}>
        <Card sub="Use at least 10 characters. Other devices signed in to your account are signed out; this one stays in.">
          <TextInput style={field} value={cur} onChangeText={setCur} secureTextEntry placeholder="Current password" placeholderTextColor={C.dim} />
          <TextInput style={field} value={n1} onChangeText={setN1} secureTextEntry placeholder="New password" placeholderTextColor={C.dim} />
          <TextInput style={field} value={n2} onChangeText={setN2} secureTextEntry placeholder="New password again" placeholderTextColor={C.dim} onSubmitEditing={go} />
          <Btn label="Change password" onPress={go} />
          {msg ? <T small style={{ color: ok ? C.good : C.bad, marginTop: 6 }}>{msg}</T> : null}
        </Card>
        <T small dim>Signing in on any device also ends by itself after 3 hours without use.</T>
      </Screen>
    </>
  );
}
