// The feedback form (Madhav, Oct 12): a visitor's account lasts 3 days. After that, signing in opens this form instead of the app.
// They answer a few questions about Ananta once; Madhav reads every answer (Cockpit › Additional features › Visitor feedback).
import { useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, StyleSheet, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { api, getExpiredForm } from "../src/api";
import { Btn } from "../src/ui";
import { C, live } from "../src/theme";

export default function FeedbackForm() {
  const f = getExpiredForm();
  const [a, setA] = useState<Record<string, string>>({});
  const [msg, setMsg] = useState("");
  const [done, setDone] = useState(false);
  const back = <Btn label="Back to sign in" kind="secondary" onPress={() => router.replace("/login")} />;
  if (!f) return <View style={s.wrap}><Text style={s.text}>Please sign in again to open the form.</Text>{back}</View>;
  if (done || f.answered) {
    return (
      <View style={s.wrap}>
        <Text style={s.title}>Thank you{f.name ? `, ${f.name}` : ""}</Text>
        <Text style={s.text}>{done ? "Your answers are with Madhav. Thank you for trying Ananta." : f.message}</Text>
        {back}
      </View>
    );
  }
  const set = (id: string, v: string) => setA((x) => ({ ...x, [id]: v }));
  const send = async () => {
    setMsg("Sending…");
    try {
      await api("/auth/feedback", { form_token: f.form_token, answers: a });
      setDone(true);
    } catch (e: any) { setMsg(e?.message ?? "Could not send; try again"); }
  };
  const Chip = ({ id, v, label }: { id: string; v: string; label?: string }) => (
    <Pressable onPress={() => set(id, v)} accessibilityRole="button"
      style={[s.chip, a[id] === v ? { borderColor: C.accent, backgroundColor: C.accentSoft } : null]}>
      <Text style={{ color: a[id] === v ? C.accent : C.text, fontWeight: "600" }}>{label ?? v}</Text>
    </Pressable>
  );
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, backgroundColor: C.bg }}>
      <ScrollView contentContainerStyle={[s.wrap, { justifyContent: "flex-start", paddingTop: 48 }]}>
        <Text style={s.title}>Ananta</Text>
        <Text style={s.text}>{f.message}</Text>
        {f.questions.map((q: any, i: number) => (
          <View key={q.id} style={s.card}>
            <Text style={s.q}>{i + 1}. {q.q}{q.required ? " *" : ""}</Text>
            {q.kind === "scale" ? (
              <>
                <View style={s.row}>{["1", "2", "3", "4", "5"].map((v) => <Chip key={v} id={q.id} v={v} />)}</View>
                <Text style={s.dim}>1 = {q.low} · 5 = {q.high}</Text>
              </>
            ) : q.kind === "choice" ? (
              <View style={s.row}>{(q.options ?? []).map((v: string) => <Chip key={v} id={q.id} v={v} />)}</View>
            ) : (
              <TextInput style={s.in} value={a[q.id] ?? ""} onChangeText={(v) => set(q.id, v)} multiline maxLength={2000}
                placeholder="Your answer" placeholderTextColor={C.dim} />
            )}
          </View>
        ))}
        <Btn label="Send to Madhav" onPress={send} />
        {msg ? <Text style={s.dim}>{msg}</Text> : null}
        <Text style={s.dim}>* needed. Your answers go only to Madhav.</Text>
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

const s = live(() => StyleSheet.create({
  wrap: { flexGrow: 1, backgroundColor: C.bg, padding: 24, justifyContent: "center", gap: 14, maxWidth: 560, width: "100%", alignSelf: "center" },
  title: { color: C.text, fontSize: 32, fontWeight: "800" },
  text: { color: C.text, fontSize: 15, lineHeight: 21 },
  q: { color: C.text, fontSize: 15, fontWeight: "600", lineHeight: 21 },
  dim: { color: C.dim, fontSize: 13 },
  card: { backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 14, gap: 10 },
  row: { flexDirection: "row", flexWrap: "wrap", gap: 8 },
  chip: { borderRadius: 999, borderWidth: 1, borderColor: C.line, paddingHorizontal: 14, paddingVertical: 8, backgroundColor: C.card },
  in: { backgroundColor: C.bg, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line, minHeight: 70, textAlignVertical: "top" },
}));
