// Teach Ananta my voice (Madhav, 27 Oct: "Yes for speaker recognition model"): read six short sentences once, and Ananta knows a voice
// message is his even without "it's me". Only a voice print (192 numbers) is kept on the Mac; no recording is stored. Re-teach or forget any time.
import { useCallback, useEffect, useRef, useState } from "react";
import { Pressable, ScrollView, Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { setScreen } from "../src/context";
import { api } from "../src/api";
import { micMime, useMic } from "../src/mic";
import { C, RADIUS, SPACE, TYPE } from "../src/theme";

const SENTENCES = [
  "Ananta, how did the Nifty close today?",
  "Show me my holdings and the practice book.",
  "Yes to all your recommendations.",
  "What is the rupee doing against the dollar?",
  "Flag this: the options card is not loading.",
  "Ananta, it's me, Madhav. Antha okay na?",
];

// 5 Nov (the 20-day synopsis: 20 of his 52 voice turns since 31 Oct came back unsure): longer, everyday sentences folded into the print he has
const MORE = [
  "Hey Ananta, what happened in the market today and what did we do on paper?",
  "Tell me what is waiting for my yes, and give me your advice on each one.",
  "How is the options line doing, and when is the twenty session review?",
  "Look at my holdings and tell me which ones you would cut and what you would buy instead.",
  "Ananta, I'm back. Let's continue with the crypto side now.",
  "Okay Ananta, good job. Let's talk again before the market opens tomorrow.",
];

type Status = { enrolled: boolean; pending: number; need: number; count?: number; enrolled_at?: string;
  thresholds?: { accept: number; reject: number; provisional: boolean } };
type Mode = "idle" | "enrol" | "test";

export default function VoiceId() {
  const [st, setSt] = useState<Status | null>(null);
  const [mode, setMode] = useState<Mode>("idle");
  const [step, setStep] = useState(0);
  const [adding, setAdding] = useState(false);
  const addingRef = useRef(false);
  addingRef.current = adding;
  const list = adding ? MORE : SENTENCES;
  const [msg, setMsg] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<{ speaker: string; score: number | null; speech_s?: number; why?: string } | null>(null);
  const modeRef = useRef<Mode>("idle");
  const stepRef = useRef(0);
  modeRef.current = mode;
  stepRef.current = step;

  const load = useCallback(async () => {
    try { setSt(await api<Status>("/v3/voice/speaker/status")); }
    catch (e: any) { setMsg(e?.message ?? "Could not reach the voice server"); }
  }, []);
  useEffect(() => { load(); }, [load]);
  useFocusEffect(useCallback(() => { setScreen({ screen: "voiceid", label: "Teach Ananta my voice: read six sentences so Ananta knows it's you" }); }, []));

  const onTurn = async (b64: string) => {
    setBusy(true);
    try {
      if (modeRef.current === "enrol") {
        const r = await api<any>("/v3/voice/speaker/enrol", { audio_b64: b64, mime: micMime() });
        if (!r.ok) { setMsg(r.why || "That one didn't work: please read the whole sentence again."); setBusy(false); return; }
        const next = stepRef.current + 1;
        const n = (addingRef.current ? MORE : SENTENCES).length;
        if (next >= n) {
          setMode("idle");
          setStep(0);
          setMsg(addingRef.current ? `Added ${n} more sentences: Ananta knows your voice better now${r.total ? ` (from ${r.total} sentences)` : ""}.`
            : "Ananta knows your voice now. Tap 'Test my voice' to check it.");
          setAdding(false);
          await load();
        } else {
          setStep(next);
          setMsg(addingRef.current ? `Got it (${next} of ${n}).`
            : r.done ? "Your voice print is ready; one more sentence makes it steadier." : `Got it (${r.count} of ${n}).`);
        }
      } else if (modeRef.current === "test") {
        const r = await api<any>("/v3/voice/speaker/test", { audio_b64: b64, mime: micMime() });
        setResult(r);
        setMode("idle");
        setMsg("");
      }
    } catch (e: any) {
      setMsg(e?.message ?? String(e));
    }
    setBusy(false);
  };
  const onNoSpeech = () => setMsg("I didn't hear anything. Tap the button and read the sentence.");
  const mic = useMic(onTurn, onNoSpeech);
  const listening = mic.status === "listening" || mic.status === "hearing";

  const startEnrol = async (more = false) => {
    setResult(null);
    try { await api("/v3/voice/speaker/start", more ? { add: true } : {}); } catch { /* the old print stays until the new one is ready */ }
    setAdding(more);
    setStep(0);
    setMode("enrol");
    setMsg(more ? "Six everyday sentences, read the way you normally talk to Ananta. Tap Record, read, then stop talking."
      : "Tap Record, read the sentence in your normal voice, then stop talking.");
  };
  const record = async () => {
    setMsg("");
    const ok = await mic.start();
    if (!ok) setMsg("The microphone is blocked. Allow it for this app or site, then try again.");
  };
  const test = async () => {
    setResult(null);
    setMode("test");
    setMsg("Say anything for two or three seconds.");
    const ok = await mic.start();
    if (!ok) { setMode("idle"); setMsg("The microphone is blocked. Allow it for this app or site, then try again."); }
  };
  const forget = async () => {
    try { await api("/v3/voice/speaker/reset", {}); setMsg("Ananta has forgotten your voice print."); setResult(null); await load(); }
    catch (e: any) { setMsg(e?.message ?? "Could not reset"); }
  };

  const verdict = (r: NonNullable<typeof result>) => r.speaker === "madhav" ? "That's you, sir." : r.speaker === "not_madhav" ? "That doesn't sound like you."
    : r.why ? `Not sure: ${r.why}.` : "Not sure: in between, or too short.";
  const btn = (label: string, onPress: () => void, primary = false, disabled = false) => (
    <Pressable onPress={onPress} disabled={disabled} accessibilityRole="button"
      style={({ pressed }) => ({ backgroundColor: primary ? C.accent : C.card, borderColor: C.line, borderWidth: primary ? 0 : 1, borderRadius: RADIUS.card,
        paddingVertical: 12, paddingHorizontal: 16, marginTop: 10, opacity: disabled ? 0.5 : pressed ? 0.7 : 1, alignItems: "center" })}>
      <Text style={{ color: primary ? C.bg : C.text, fontWeight: "700" }}>{label}</Text>
    </Pressable>
  );

  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: SPACE.card, paddingTop: 56, paddingBottom: 120 }}>
      <Pressable onPress={() => router.back()} accessibilityRole="button"><Text style={{ color: C.accent, fontWeight: "700" }}>‹ Back</Text></Pressable>
      <Text style={{ color: C.text, fontSize: TYPE.title, fontWeight: "800", marginTop: 8 }}>Teach Ananta my voice</Text>
      <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 4 }}>
        Read six short sentences once. Then a voice message counts as you even without "it's me", and someone else's voice can't say yes for you.
        Only a voice print stays on your Mac; no recording is kept.
      </Text>

      <View style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: RADIUS.card, padding: 12, marginTop: 12 }}>
        <Text style={{ color: C.text, fontWeight: "700" }}>
          {st?.enrolled ? "Ananta knows your voice" : "Not taught yet"}
        </Text>
        <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 2 }}>
          {st?.enrolled ? `From ${st.count} sentences${st.enrolled_at ? ` · ${new Date(st.enrolled_at).toLocaleDateString()}` : ""}` : "Takes about a minute."}
        </Text>
      </View>

      {mode === "enrol" ? (
        <View style={{ backgroundColor: C.card, borderColor: C.accent, borderWidth: 1, borderRadius: RADIUS.card, padding: 14, marginTop: 12 }}>
          <Text style={{ color: C.dim, fontSize: TYPE.meta }}>Sentence {step + 1} of {list.length}</Text>
          <Text style={{ color: C.text, fontSize: 20, fontWeight: "700", marginTop: 6 }}>{list[step]}</Text>
          {btn(listening ? (mic.status === "hearing" ? "Hearing you…" : "Listening…") : busy ? "Saving…" : "Record", record, true, listening || busy)}
          {btn("Cancel", () => { mic.cancel(); setMode("idle"); setAdding(false); setMsg(""); }, false, busy)}
        </View>
      ) : (
        <>
          {st?.enrolled ? btn("Add more of my voice", () => startEnrol(true), true, busy || listening) : null}
          {btn(st?.enrolled ? "Teach it again" : "Start: read six sentences", () => startEnrol(false), !st?.enrolled, busy || listening)}
          {st?.enrolled ? btn(mode === "test" && listening ? "Listening…" : "Test my voice", test, false, busy || listening) : null}
          {st?.enrolled ? btn("Forget my voice", forget, false, busy || listening) : null}
        </>
      )}

      {result ? (
        <View style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: RADIUS.card, padding: 12, marginTop: 12 }}>
          <Text style={{ color: result.speaker === "madhav" ? C.good : result.speaker === "not_madhav" ? C.bad : C.warn, fontWeight: "800" }}>{verdict(result)}</Text>
          <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 2 }}>
            Match {result.score != null ? `${Math.round(result.score * 100)}%` : "not measured"}
            {st?.thresholds ? ` · counts as you from ${Math.round(st.thresholds.accept * 100)}%` : ""}
            {result.speech_s != null ? ` · ${result.speech_s.toFixed(1)} s of speech` : ""}
          </Text>
        </View>
      ) : null}
      {msg ? <Text style={{ color: C.text, marginTop: 12 }}>{msg}</Text> : null}
    </ScrollView>
  );
}
