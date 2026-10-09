// The first conversation (build plan Phase 5): a new visitor meets Ananta inside Ask Ananta. The service decides the words and the
// next step (jarvis/service/onboard.py); this screen shows the conversation so far, says Ananta's line (when voice is allowed),
// and offers the answer as taps or a small box. Saved as it goes: leave halfway and it resumes where you stopped.
import { useEffect, useRef, useState } from "react";
import { KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { requestRecordingPermissionsAsync } from "expo-audio";
import { api } from "./api";
import { DecisionCard, showToast } from "./blocks";
import { goTab, setTour, takeTourCommand } from "./context";
import { C } from "./theme";
import * as TTS from "./tts";
import { unlockAudio } from "./webaudio";
import { loadMe } from "./visitor";

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));
const tz = () => { try { return Intl.DateTimeFormat().resolvedOptions().timeZone; } catch { return undefined; } };

// the one-minute look at what else Ananta does (plan 5.7), over the visitor's own screens
const TOUR: { go: () => void; say: string }[] = [
  { go: () => goTab("/(tabs)/today"), say: "This is Home: your practice money on top, then what I'm doing for you today, and the market." },
  { go: () => goTab("/(tabs)/portfolio"), say: "Books holds every trade. Each one carries a stamp: your initials when you placed it, or my name and the setup when I did." },
  { go: () => goTab("/(tabs)/watchlists"), say: "Your watch lives in Watchlists, with its mode. When a coin gets close, it says so, and you can change the mode any time." },
  { go: () => router.push("/evidence"), say: "This is the Evidence. Every rule I trade by was tested on history first. When a rule keeps losing, it goes to the repair shop to be fixed." },
  { go: () => router.push("/coin/BTC"), say: "Want to trade yourself? Tap Buy on any coin's page, or the plus on a coin. Your trade gets your initials, and I watch it for you." },
];

export function FirstConversation({ onDone }: { onDone: () => void }) {
  const [p, setP] = useState<any>(null);
  const [err, setErr] = useState("");
  const [busy, setBusy] = useState(false);
  const voice = useRef(false);
  const scroll = useRef<ScrollView>(null);
  const spoken = useRef("");

  const show = (r: any) => {
    setP(r);
    setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 60);
    if (voice.current && r?.say && r.say !== spoken.current) {           // voice says the line; the screen shows the rest
      spoken.current = r.say;
      TTS.speakText(r.say);
    }
  };
  useEffect(() => { api("/v3/onboard").then(show).catch((e) => setErr(e?.message ?? String(e))); TTS.init(); }, []);

  const send = async (value: any) => {
    if (!p || busy) return;
    setBusy(true);
    setErr("");
    try {
      if (p.step === "permission") {
        unlockAudio();                                                   // the same tap allows the microphone and unlocks sound
        if (value === "voice") {
          const perm = await requestRecordingPermissionsAsync().catch(() => ({ granted: false }));
          voice.current = true;
          if (!perm.granted) showToast("No microphone: I'll speak, and you can type");
        }
      }
      const r = await api("/v3/onboard", { step: p.step, value, tz: tz() });
      if (r.step === "acts") await itActs(r);
      else if (p.step === "tour") await finish(value === "yes");
      else show(r);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    } finally {
      setBusy(false);
    }
  };

  // "It acts": the watch is running; Watchlists opens with it glowing, then back here for what comes next
  const itActs = async (r: any) => {
    show(r);
    if (voice.current) await TTS.speakText(r.say); else await sleep(2500);
    goTab({ pathname: "/(tabs)/watchlists", params: { glow: r.watch?.id ?? "", t: String(Date.now()) } } as any);
    if (r.watch?.order_placed) setTimeout(() => showToast("Order placed ✓"), 900);
    await sleep(4500);
    goTab("/(tabs)/ask");
    await sleep(500);
    const n = await api("/v3/onboard", { step: "acts", value: "seen" });
    show(n);
  };

  const finish = async (tour: boolean) => {
    if (tour) {
      takeTourCommand();
      for (let i = 0; i < TOUR.length; i++) {
        const st = TOUR[i];
        setTour({ active: true, i: i + 1, n: TOUR.length + 1, text: st.say });
        st.go();
        await sleep(700);
        if (takeTourCommand() === "stop") break;
        if (voice.current) await TTS.speakText(st.say); else await sleep(4200);
        if (takeTourCommand() === "stop") break;
      }
      setTour({ active: false, i: 0, n: 0, text: "" });
      goTab("/(tabs)/ask");
      await sleep(400);
    }
    const last = "That's it. Ask me anything, or tell me what to watch.";
    if (voice.current) TTS.speakText(last);
    await loadMe();
    onDone();
  };

  const log: any[] = p?.log ?? [];
  return (
    <KeyboardAvoidingView behavior={Platform.OS === "ios" ? "padding" : undefined} style={{ flex: 1, backgroundColor: C.bg }} keyboardVerticalOffset={90}>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 40 }} keyboardShouldPersistTaps="handled">
        {log.map((m, i) => <Bubble key={i} who={m.who} text={m.text} />)}
        {p ? <Bubble who="ananta" text={p.say} live /> : <Text style={{ color: C.dim }}>One moment…</Text>}
        {p?.note ? <Text style={{ color: C.dim, fontSize: 13, lineHeight: 19, marginLeft: 4 }}>{p.note}</Text> : null}
        {p?.card ? <DecisionCard card={p.card} title="The setup" /> : null}
        {p?.input ? <Answer input={p.input} busy={busy} onSend={send} /> : null}
        {err ? <Text style={{ color: C.bad }}>{err}</Text> : null}
      </ScrollView>
    </KeyboardAvoidingView>
  );
}

function Bubble({ who, text, live }: { who: string; text: string; live?: boolean }) {
  const me = who === "you";
  return (
    <View style={{ alignSelf: me ? "flex-end" : "flex-start", maxWidth: "88%", backgroundColor: me ? C.accent : C.card, borderWidth: me ? 0 : 1,
      borderColor: live ? C.accent : C.line, borderRadius: 16, borderBottomRightRadius: me ? 4 : 16, borderTopLeftRadius: me ? 16 : 4, paddingHorizontal: 14, paddingVertical: 10 }}>
      <Text style={{ color: me ? C.onInk : C.text, fontSize: 15, lineHeight: 22 }}>{text}</Text>
    </View>
  );
}

function Opt({ label, on, onPress, wide }: { label: string; on?: boolean; onPress: () => void; wide?: boolean }) {
  return (
    <Pressable onPress={onPress} style={({ pressed }) => ({ borderRadius: wide ? 12 : 999, paddingHorizontal: 14, paddingVertical: wide ? 12 : 9, borderWidth: 1,
      borderColor: on ? C.accent : C.line, backgroundColor: on ? C.accentSoft : C.card, opacity: pressed ? 0.7 : 1, width: wide ? "100%" : undefined })}>
      <Text style={{ color: on ? C.accent : C.text, fontWeight: "600", fontSize: 14 }}>{label}</Text>
    </Pressable>
  );
}

function Go({ label, onPress, off }: { label: string; onPress: () => void; off?: boolean }) {
  return (
    <Pressable onPress={onPress} disabled={off} style={({ pressed }) => ({ backgroundColor: off ? C.card2 : C.accent, borderRadius: 12, paddingVertical: 12,
      alignItems: "center", opacity: pressed ? 0.8 : 1 })}>
      <Text style={{ color: off ? C.faint : C.onInk, fontWeight: "800", fontSize: 15 }}>{label}</Text>
    </Pressable>
  );
}

function Answer({ input, busy, onSend }: { input: any; busy: boolean; onSend: (v: any) => void }) {
  const [name, setName] = useState(input.value ?? "");
  const [coins, setCoins] = useState<string[]>(input.value ?? []);
  const [cap, setCap] = useState<number>(input.value ?? 5000);
  useEffect(() => { if (input.type === "coins") setCoins(input.value ?? []); if (input.type === "capital") setCap(input.value ?? 5000); }, [input.type]);
  const opts: any[] = input.options ?? [];
  if (input.type === "choice") {
    const long = opts.some((o) => String(o[1]).length > 22);
    return (
      <View style={{ flexDirection: long ? "column" : "row", flexWrap: "wrap", gap: 8, opacity: busy ? 0.5 : 1 }}>
        {opts.map(([k, l]) => <Opt key={k} label={l} wide={long} onPress={() => onSend(k)} />)}
      </View>
    );
  }
  if (input.type === "card") {
    return (
      <View style={{ backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 14, gap: 8 }}>
        {(input.items ?? []).map((x: string, i: number) => <Text key={i} style={{ color: C.text, fontSize: 14, lineHeight: 20 }}>✦  {x}</Text>)}
        <Go label={opts[0]?.[1] ?? "Continue"} onPress={() => onSend(opts[0]?.[0] ?? "ok")} off={busy} />
      </View>
    );
  }
  if (input.type === "name") {
    return (
      <View style={{ flexDirection: "row", gap: 8 }}>
        <TextInput value={name} onChangeText={setName} placeholder="Your name" placeholderTextColor={C.faint} autoFocus maxLength={40}
          onSubmitEditing={() => name.trim() && onSend(name.trim())}
          style={{ flex: 1, backgroundColor: C.card, color: C.text, borderRadius: 12, borderWidth: 1, borderColor: C.line, paddingHorizontal: 14, paddingVertical: 11, fontSize: 16 }} />
        <Pressable onPress={() => name.trim() && onSend(name.trim())} style={{ backgroundColor: name.trim() ? C.accent : C.card2, borderRadius: 12, paddingHorizontal: 16, justifyContent: "center" }}>
          <Text style={{ color: name.trim() ? C.onInk : C.faint, fontWeight: "800" }}>Send</Text>
        </Pressable>
      </View>
    );
  }
  if (input.type === "coins") {
    return (
      <View style={{ gap: 10 }}>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {opts.map(([k, l]) => <Opt key={k} label={l} on={coins.includes(k)} onPress={() => setCoins(coins.includes(k) ? coins.filter((c) => c !== k) : [...coins, k])} />)}
        </View>
        <Go label={coins.length ? `Continue with ${coins.length} coin${coins.length === 1 ? "" : "s"}` : "Pick at least one"} off={!coins.length || busy} onPress={() => onSend(coins)} />
      </View>
    );
  }
  if (input.type === "capital") {
    return (
      <View style={{ gap: 10 }}>
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {opts.map((v: number) => <Opt key={v} label={`$${(v / 1000).toFixed(0)}k`} on={cap === v} onPress={() => setCap(v)} />)}
        </View>
        <Go label={`Practise with $${cap.toLocaleString()}`} off={busy} onPress={() => onSend(cap)} />
      </View>
    );
  }
  return null;
}
