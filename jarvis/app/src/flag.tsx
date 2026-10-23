// The Flag button (Madhav, 23 Oct): on any screen, in either market, say what is wrong, choose how to fix it, and Ananta's repair
// worker fixes it and tells you. SAFE fixes (words, screens, voice, reports) are built, tested and put live by the worker; anything
// near trading comes back as a plan for your yes (jarvis/service/fixflow.py decides the lane in code). Owner only.
import { useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { router, usePathname } from "expo-router";
import { api } from "./api";
import { getScreen } from "./context";
import { getMarket } from "./market";
import { useMe } from "./visitor";
import { C, RADIUS, SPACE, TYPE } from "./theme";

type Opt = { title: string; what: string; lane: "SAFE" | "DECISION"; does: string };
type Triage = { num: number; diagnosis: string; options: Opt[]; say?: string };
const HIDE = ["/login", "/join", "/feedback", "/market", "/welcome", "/password", "/flags"];

export function FlagButton() {
  const me = useMe();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  if (!me || me.guest || HIDE.some((h) => path.startsWith(h))) return null;
  return (
    <>
      <View pointerEvents="box-none" style={{ position: "absolute", left: 12, bottom: 92 }}>
        <Pressable onPress={() => setOpen(true)} accessibilityRole="button" accessibilityLabel="Flag a problem on this screen"
          style={({ pressed }) => ({ backgroundColor: pressed ? C.warnSoft : C.card, borderColor: C.warn, borderWidth: 1, borderRadius: 999,
            width: 36, height: 36, alignItems: "center", justifyContent: "center", shadowColor: "#000", shadowOpacity: 0.15, shadowRadius: 6 })}>
          <Text style={{ color: C.warn, fontWeight: "800", fontSize: 15 }}>⚑</Text>
        </Pressable>
      </View>
      {open ? <FlagSheet path={path} onClose={() => setOpen(false)} /> : null}
    </>
  );
}

function FlagSheet({ path, onClose }: { path: string; onClose: () => void }) {
  const here = getScreen();
  const market = getMarket() === "india" ? "india" : "crypto";
  const screen = here?.label || here?.screen || path;
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [tri, setTri] = useState<Triage | null>(null);
  const [done, setDone] = useState("");

  const send = async () => {
    if (!text.trim()) { setMsg("Say what is wrong first."); return; }
    setBusy(true); setMsg("");
    try { setTri(await api<Triage>("/v3/flags", { text: text.trim(), market, screen, route: path }, 60000)); }
    catch (e: any) { setMsg(e?.message ?? "Could not send; try again."); }
    setBusy(false);
  };
  const choose = async (i: number) => {
    if (!tri) return;
    setBusy(true); setMsg("");
    try { const r = await api<{ say: string }>(`/v3/flags/${tri.num}/choose`, { option: i }); setDone(r.say); }
    catch (e: any) { setMsg(e?.message ?? "Could not send; try again."); }
    setBusy(false);
  };

  return (
    <Modal transparent animationType="slide" onRequestClose={onClose}>
      <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, justifyContent: "flex-end", backgroundColor: "rgba(0,0,0,0.35)" }}>
        <View style={{ backgroundColor: C.bg, borderTopLeftRadius: 20, borderTopRightRadius: 20, padding: SPACE.card + 4, maxHeight: "85%" }}>
          <ScrollView keyboardShouldPersistTaps="handled">
            <Text style={{ color: C.text, fontSize: TYPE.title, fontWeight: "800" }}>Flag a problem</Text>
            <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 4 }}>{market === "india" ? "Indian market" : "Crypto"} · {screen}</Text>
            {done ? (
              <>
                <Text style={{ color: C.text, fontSize: TYPE.body, marginTop: 16, lineHeight: 22 }}>{done}</Text>
                <Row label="See my flags" onPress={() => { onClose(); router.push("/flags"); }} />
                <Row label="Close" onPress={onClose} secondary />
              </>
            ) : !tri ? (
              <>
                <TextInput value={text} onChangeText={setText} placeholder="What is wrong here?" placeholderTextColor={C.faint} multiline autoFocus
                  style={{ color: C.text, backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: RADIUS.card, padding: 12,
                    minHeight: 96, marginTop: 14, fontSize: TYPE.body, textAlignVertical: "top" }} />
                <Text style={{ color: C.faint, fontSize: TYPE.meta, marginTop: 8 }}>Ananta files it on the repair board now and offers ways to fix it.</Text>
                {busy ? <ActivityIndicator style={{ marginTop: 16 }} color={C.accent} /> : <Row label="Send" onPress={send} />}
                <Row label="Cancel" onPress={onClose} secondary />
              </>
            ) : (
              <>
                <Text style={{ color: C.text, fontSize: TYPE.body, marginTop: 14, lineHeight: 22 }}>Request {tri.num}. {tri.diagnosis}</Text>
                <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 10, fontWeight: "700" }}>CHOOSE HOW TO FIX IT</Text>
                {tri.options.map((o, i) => (
                  <Pressable key={i} disabled={busy} onPress={() => choose(i)} accessibilityRole="button" accessibilityLabel={`Fix: ${o.title}`}
                    style={({ pressed }) => ({ backgroundColor: pressed ? C.card2 : C.card, borderColor: o.lane === "SAFE" ? C.line : C.warn,
                      borderWidth: 1, borderRadius: RADIUS.card, padding: 12, marginTop: 10 })}>
                    <Text style={{ color: C.text, fontWeight: "700", fontSize: TYPE.body }}>{o.title}</Text>
                    <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 4, lineHeight: 19 }}>{o.what}</Text>
                    <Text style={{ color: o.lane === "SAFE" ? C.good : C.warn, fontSize: TYPE.meta, marginTop: 6, fontWeight: "700" }}>{o.does}</Text>
                  </Pressable>
                ))}
                {busy ? <ActivityIndicator style={{ marginTop: 16 }} color={C.accent} /> : null}
                <Row label="Leave it on the board for now" onPress={onClose} secondary />
              </>
            )}
            {msg ? <Text style={{ color: C.bad, marginTop: 10 }}>{msg}</Text> : null}
          </ScrollView>
        </View>
      </KeyboardAvoidingView>
    </Modal>
  );
}

function Row({ label, onPress, secondary }: { label: string; onPress: () => void; secondary?: boolean }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button"
      style={{ backgroundColor: secondary ? C.card2 : C.accent, borderRadius: RADIUS.card, padding: 12, alignItems: "center", marginTop: 12 }}>
      <Text style={{ color: secondary ? C.text : C.onInk, fontWeight: "700" }}>{label}</Text>
    </Pressable>
  );
}
