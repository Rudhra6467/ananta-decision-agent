// A new visitor's first minutes: their name, the coins they want to watch, (the tour over their own tabs), practice capital,
// then a one-second "ready" screen and their Books. Each answer is saved as it is given, so they can stop and come back.
import { useEffect, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { Btn } from "../src/ui";
import { CoinPicker, loadMe, setup, useMe } from "../src/visitor";
import { C } from "../src/theme";

export default function Welcome() {
  const m = useMe();
  const [name, setName] = useState("");
  const [coins, setCoins] = useState<string[]>([]);
  const [cap, setCap] = useState<number | null>(null);
  const [msg, setMsg] = useState("");
  const [ready, setReady] = useState(false);
  useEffect(() => { loadMe(); }, []);
  useEffect(() => {
    if (!m) return;
    if (!m.guest) { router.replace("/(tabs)/today"); return; }
    if (!name) setName(m.profile?.name || m.name || "");
    if (!coins.length && m.profile?.coins?.length) setCoins(m.profile.coins);
    if (m.stage === "tour") router.replace("/(tabs)/today");          // the tour runs over their own tabs
    if ((m.stage === "ready" || m.stage === "trading") && !ready) router.replace("/(tabs)/portfolio");
  }, [m?.stage]);

  const save = async (body: object) => {
    setMsg("");
    try { await setup(body); } catch (e: any) { setMsg(e?.message ?? String(e)); throw e; }
  };
  const addCapital = async () => {
    if (!cap) return;
    try { await save({ capital: cap }); } catch { return; }
    setReady(true);                                     // the small "start trading" screen, then their Books
    setTimeout(() => router.replace("/(tabs)/portfolio"), 1200);
  };

  if (ready) {
    return (
      <View style={{ flex: 1, backgroundColor: C.accent, alignItems: "center", justifyContent: "center", padding: 24, gap: 10 }}>
        <Text style={{ color: C.onInk, fontSize: 15, fontWeight: "600", opacity: 0.85 }}>${cap?.toLocaleString()} of practice money added</Text>
        <Text style={{ color: C.onInk, fontSize: 30, fontWeight: "800", textAlign: "center" }}>Let's start trading</Text>
      </View>
    );
  }
  const stage = m?.stage;
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, backgroundColor: C.bg }}>
      <ScrollView contentContainerStyle={{ padding: 24, paddingTop: 70, gap: 16, maxWidth: 560, width: "100%", alignSelf: "center" }} keyboardShouldPersistTaps="handled">
        <Text style={{ color: C.accent, fontSize: 12, fontWeight: "700", letterSpacing: 0.8 }}>
          {stage === "name" ? "STEP 1 OF 4" : stage === "coins" ? "STEP 2 OF 4" : "STEP 4 OF 4"}
        </Text>
        {!m ? <Text style={{ color: C.dim }}>One moment…</Text> : null}

        {stage === "name" ? (
          <>
            <Text style={{ color: C.text, fontSize: 28, fontWeight: "800" }}>Hi, I'm Ananta.</Text>
            <Text style={{ color: C.text, fontSize: 17, lineHeight: 24 }}>I'll help you learn to trade crypto with practice money. What should I call you?</Text>
            <TextInput value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor={C.faint} autoFocus
              onSubmitEditing={() => name.trim() && save({ name: name.trim() }).catch(() => {})}
              style={{ backgroundColor: C.card, color: C.text, borderRadius: 12, padding: 14, borderWidth: 1, borderColor: C.line, fontSize: 17 }} />
            <Btn label="Continue" onPress={() => name.trim() ? save({ name: name.trim() }).catch(() => {}) : setMsg("Enter a name")} />
          </>
        ) : null}

        {stage === "coins" ? (
          <>
            <Text style={{ color: C.text, fontSize: 26, fontWeight: "800" }}>Nice to meet you, {m?.profile?.name}.</Text>
            <Text style={{ color: C.text, fontSize: 17, lineHeight: 24 }}>Pick a few coins you'd like to watch and talk about. You can change them any time.</Text>
            <CoinPicker value={coins} onChange={setCoins} choices={m?.coin_choices ?? []} />
            <Btn label={coins.length ? `Watch ${coins.length} coin${coins.length === 1 ? "" : "s"}` : "Pick at least one"}
              onPress={() => coins.length ? save({ coins }).catch(() => {}) : setMsg("Pick at least one coin")} />
          </>
        ) : null}

        {stage === "capital" ? (
          <>
            <Text style={{ color: C.text, fontSize: 26, fontWeight: "800" }}>Add your practice capital</Text>
            <Text style={{ color: C.text, fontSize: 17, lineHeight: 24 }}>This is paper money for practice. Nothing real is spent, and you can start over any time.</Text>
            <View style={{ flexDirection: "row", gap: 12 }}>
              {(m?.capitals ?? [1000, 2000]).map((c) => (
                <Pressable key={c} onPress={() => setCap(c)} style={{ flex: 1, borderRadius: 14, borderWidth: 2, borderColor: cap === c ? C.accent : C.line,
                  backgroundColor: cap === c ? C.accentSoft : C.card, paddingVertical: 22, alignItems: "center" }}>
                  <Text style={{ color: cap === c ? C.accent : C.text, fontSize: 24, fontWeight: "800" }}>${c.toLocaleString()}</Text>
                  <Text style={{ color: C.dim, fontSize: 12 }}>practice money</Text>
                </Pressable>
              ))}
            </View>
            <Btn label={cap ? `Add $${cap.toLocaleString()}` : "Choose an amount"} onPress={addCapital} />
          </>
        ) : null}

        {msg ? <Text style={{ color: C.bad }}>{msg}</Text> : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}
