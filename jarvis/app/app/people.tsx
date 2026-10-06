// People (Madhav only): his main account, the visitors he invited, and invite links. A visitor opens the link, picks a
// name and password, and gets their own practice book. Removing a visitor stops their sign-in at once (their book is archived).
import { useState } from "react";
import { Alert, Platform, Share, Text, TextInput, View } from "react-native";
import { Stack } from "expo-router";
import { api } from "../src/api";
import { Btn, Busy, Card, Divider, ErrorBox, Line, Screen, Section, T } from "../src/ui";
import { useData } from "../src/useData";
import { C } from "../src/theme";

const when = (t?: number) => (t ? new Date(t * 1000).toLocaleDateString(undefined, { month: "short", day: "numeric" }) : "–");

async function ask(title: string, body: string): Promise<boolean> {
  if (Platform.OS === "web") return window.confirm(`${title}\n\n${body}`);
  return new Promise((res) => Alert.alert(title, body, [{ text: "Cancel", onPress: () => res(false) },
    { text: "Remove", style: "destructive", onPress: () => res(true) }]));
}

async function shareLink(link: string, name: string) {
  const text = `${name ? `Hi ${name}! ` : ""}Here is your invite to Ananta (paper trading only, no real money): ${link}`;
  if (Platform.OS === "web") {
    try { await navigator.clipboard.writeText(link); window.alert("Link copied. Paste it to the person you invited."); } catch { window.prompt("Copy this link:", link); }
    return;
  }
  await Share.share({ message: text });
}

export default function PeoplePage() {
  return (
    <>
      <Stack.Screen options={{ headerShown: true, title: "People", headerStyle: { backgroundColor: C.bg }, headerShadowVisible: false,
        headerTintColor: C.text, headerBackTitle: "Cockpit" }} />
      <People />
    </>
  );
}

function People() {
  const { data: d, err, loading, reload } = useData("/v3/people", 0);
  const [name, setName] = useState("");
  const [email, setEmail] = useState("");
  const [made, setMade] = useState<{ link: string; name: string } | null>(null);
  const [msg, setMsg] = useState("");
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;

  const invite = async () => {
    setMsg("");
    try {
      const r = await api<{ link: string; name: string }>("/v3/people/invite", { name: name.trim(), email: email.trim() });
      setMade(r); setName(""); setEmail(""); reload();
    } catch (e: any) { setMsg(e?.message ?? String(e)); }
  };
  const remove = async (key: string, label: string, isInvite: boolean) => {
    const ok = await ask(isInvite ? "Cancel this invite?" : `Remove ${label}?`,
      isInvite ? "The link stops working." : "Their sign-in stops working at once. Their practice book is archived, not deleted.");
    if (!ok) return;
    await api("/v3/people/remove", { email: key });
    reload();
  };

  return (
    <Screen loading={loading} onRefresh={reload}>
      <Section title="Main account" />
      <Card>
        <Line label={d.owner.name} value="Owner" sub={d.owner.email} />
      </Card>

      <Section title="Invite someone" />
      <Card sub="They open the link, choose their own name and password, and start with $1,000 of paper money in their own practice book.">
        <TextInput value={name} onChangeText={setName} placeholder="Their name (they can change it)" placeholderTextColor={C.dim}
          style={{ backgroundColor: C.card2, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line, marginBottom: 8 }} />
        <TextInput value={email} onChangeText={setEmail} placeholder="Their email (optional: fixes the email for this link)" placeholderTextColor={C.dim}
          autoCapitalize="none" keyboardType="email-address"
          style={{ backgroundColor: C.card2, color: C.text, borderRadius: 10, padding: 12, borderWidth: 1, borderColor: C.line, marginBottom: 10 }} />
        <Btn label="Make invite link" onPress={invite} />
        {msg ? <T small style={{ color: C.bad, marginTop: 6 }}>{msg}</T> : null}
        {made ? (
          <View style={{ marginTop: 12, gap: 8 }}>
            <T small>Invite ready (works once, for 7 days):</T>
            <Text selectable style={{ color: C.accent, fontSize: 13 }}>{made.link}</Text>
            <Btn label={Platform.OS === "web" ? "Copy link" : "Share link"} kind="secondary" onPress={() => shareLink(made.link, made.name)} />
          </View>
        ) : null}
      </Card>

      <Section title={`Visitors (${d.visitors.length})`} />
      <Card>
        {d.visitors.length ? d.visitors.map((v: any, i: number) => (
          <View key={v.email}>
            {i ? <Divider /> : null}
            <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 8 }}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: C.text, fontWeight: "600" }}>{v.name}</Text>
                <T small>{v.email} · joined {when(v.joined_t)} · last in {when(v.last_login_t)}</T>
              </View>
              <Btn small kind="danger" label="Remove" onPress={() => remove(v.email, v.name, false)} />
            </View>
          </View>
        )) : <T dim small>No visitors yet. Make an invite link above.</T>}
      </Card>

      {d.invites.length ? (
        <>
          <Section title="Invites not used yet" />
          <Card>
            {d.invites.map((v: any, i: number) => {
              const link = `https://livetrading247.com/join?code=${v.code}`;
              return (
                <View key={v.code}>
                  {i ? <Divider /> : null}
                  <View style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingVertical: 8 }}>
                    <View style={{ flex: 1 }}>
                      <Text style={{ color: C.text, fontWeight: "600" }}>{v.name || "Anyone with the link"}</Text>
                      <T small>{v.email || "any email"} · until {when(v.expires_t)}</T>
                    </View>
                    <Btn small kind="secondary" label={Platform.OS === "web" ? "Copy" : "Share"} onPress={() => shareLink(link, v.name)} />
                    <Btn small kind="danger" label="Cancel" onPress={() => remove(v.code, v.name, true)} />
                  </View>
                </View>
              );
            })}
          </Card>
        </>
      ) : null}
    </Screen>
  );
}
