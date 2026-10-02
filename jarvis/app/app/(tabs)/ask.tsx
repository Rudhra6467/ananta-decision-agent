import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Animated, AppState, Keyboard, KeyboardAvoidingView, Platform, Pressable, ScrollView, Share, Switch, Text, TextInput, View } from "react-native";
import { requestRecordingPermissionsAsync } from "expo-audio";
import { useFocusEffect, useLocalSearchParams } from "expo-router";
import { getScreen, setScreen, setVoiceLive, useScreen } from "../../src/context";
import * as UI from "../../src/uiagent";
import { clearSpot, setScroller } from "../../src/spotlight";
import { StageCard } from "../../src/voice";
import { ActionCard, openScreen } from "../../src/actions";
import { useData } from "../../src/useData";
import { api } from "../../src/api";
import { useMic } from "../../src/mic";
import * as TTS from "../../src/tts";
import * as Haptics from "../../src/haptics";
import { VoiceLoop, type Phase } from "../../src/voiceloop";
import { Bullet, Divider, Pill, Segmented, T } from "../../src/ui";
import { C } from "../../src/theme";

type Msg = { id?: string; role: "user" | "assistant"; text?: string; voice?: boolean; [k: string]: any };
const STAGE: Record<string, string> = { observation: "Observation", candidate: "Candidate setup", "candidate setup": "Candidate setup", setup: "Setup",
  decision: "Decision", execution: "Executed", position: "Open position", outcome: "Outcome", evaluation: "Evaluation", learning: "Learning" };

const UserBubble = ({ text, voice }: { text: string; voice?: boolean }) => (
  <View style={{ alignSelf: "flex-end", maxWidth: "85%", backgroundColor: C.accent, borderRadius: 16, borderBottomRightRadius: 4, paddingHorizontal: 14, paddingVertical: 10 }}>
    <Text style={{ color: "#FFF", fontSize: 15, lineHeight: 21 }}>{voice ? "🎙 " : ""}{text}</Text>
  </View>
);

function Answer({ m, onPick, onRate, onSecond, onSpeak }: { m: Msg; onPick: (q: string) => void; onRate: (v: number) => void; onSecond: () => void; onSpeak?: () => void }) {
  const [layer, setLayer] = useState<"none" | "breakdown" | "evidence">("none");
  if (m.error) {
    return <View style={{ backgroundColor: C.badSoft, borderRadius: 12, padding: 12 }}><Text style={{ color: C.bad }}>{m.error}</Text></View>;
  }
  const chips: string[] = m.kind === "clarify" ? m.options ?? [] : m.follow_ups ?? [];
  return (
    <View style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 16, borderTopLeftRadius: 4, padding: 14, gap: 10, maxWidth: "96%" }}>
      <View style={{ flexDirection: "row", gap: 6, flexWrap: "wrap" }}>
        {m.second_of ? <Pill text="SECOND OPINION" color={C.text} bg={C.card2} /> : null}
        {m.stage ? <Pill text={(STAGE[String(m.stage).toLowerCase()] ?? m.stage).toUpperCase()} color={C.accent} bg={C.accentSoft} /> : null}
        {m.kind === "clarify" ? <Pill text="DID YOU MEAN" color={C.warn} bg={C.warnSoft} /> : null}
        {m.kind === "out_of_scope" ? <Pill text="OUTSIDE MY AREA" /> : null}
        {m.outside ? <Pill text={`FROM AI · ${m.outside.source ?? "outside our system"}`} color={C.warn} bg={C.warnSoft} /> : null}
        {m.kind === "cannot_do_yet" ? <Pill text="CAN'T DO THAT YET" color={C.warn} bg={C.warnSoft} /> : null}
      </View>
      <Text style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>{m.answer}</Text>
      {m.assumption ? <T small>Assumed: {m.assumption}</T> : null}
      {m.outside ? <Text style={{ color: C.faint, fontSize: 11 }}>{m.outside.note}</Text> : null}

      {m.kind === "answer" && (m.breakdown?.length || m.evidence?.length) ? (
        <View style={{ flexDirection: "row", gap: 8 }}>
          {m.breakdown?.length ? <Tab label="Break it down" on={layer === "breakdown"} onPress={() => setLayer(layer === "breakdown" ? "none" : "breakdown")} /> : null}
          {m.evidence?.length ? <Tab label="Show evidence" on={layer === "evidence"} onPress={() => setLayer(layer === "evidence" ? "none" : "evidence")} /> : null}
        </View>
      ) : null}
      {layer === "breakdown" ? <View style={{ gap: 6 }}>{m.breakdown.map((b: string, i: number) => <Bullet key={i}>{b}</Bullet>)}</View> : null}
      {layer === "evidence" ? (
        <View style={{ backgroundColor: C.bg, borderRadius: 10, padding: 10 }}>
          {m.evidence.map((e: any, i: number) => (
            <View key={i}>
              {i ? <Divider /> : null}
              <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 10, paddingVertical: 7 }}>
                <View style={{ flex: 1 }}>
                  <Text style={{ color: C.text, fontSize: 13 }}>{e.label}</Text>
                  <Text style={{ color: C.faint, fontSize: 11 }}>{[e.source, e.time].filter(Boolean).join(" · ")}</Text>
                </View>
                <View style={{ alignItems: "flex-end", maxWidth: "50%", gap: 4 }}>
                  <Text style={{ color: C.text, fontSize: 13, fontWeight: "600", textAlign: "right" }}>{String(e.value)}</Text>
                  {e.screen ? (
                    <Text onPress={() => showEvidence(e)} style={{ color: C.accent, fontSize: 12, fontWeight: "700" }}>Show me ›</Text>
                  ) : null}
                </View>
              </View>
            </View>
          ))}
        </View>
      ) : null}

      {chips.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {chips.map((c, i) => (
            <Pressable key={i} onPress={() => onPick(c)} style={{ borderColor: C.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 7 }}>
              <Text style={{ color: C.accent, fontSize: 13 }}>{c}</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      {(m.actions ?? []).map((a: any) => <ActionCard key={a.id} a={a} />)}
      {m.show?.length ? (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {m.show.map((sh: any, i: number) => (
            <Pressable key={i} onPress={() => openScreen(sh)} style={{ backgroundColor: C.text, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7 }}>
              <Text style={{ color: "#FFF", fontSize: 13, fontWeight: "600" }}>{sh.label} ›</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      {m.note ? <Text style={{ color: C.faint, fontSize: 11 }}>{m.note}</Text> : null}
      <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
        <Text style={{ color: C.faint, fontSize: 11, flex: 1 }}>
          {m.model_label ?? (m.provider === "gemini" ? "Gemini" : "Claude")} · {m.cost_usd ? `${(m.cost_usd * 100).toFixed(1)}¢` : "free"}{m.ms ? ` · ${(m.ms / 1000).toFixed(1)}s` : ""}{m.lookups?.length ? ` · ${m.lookups.length} lookups` : ""}
        </Text>
        {onSpeak && m.answer ? <Text onPress={onSpeak} style={{ fontSize: 15 }}>🔊</Text> : null}
        {!m.second_of ? <Text onPress={onSecond} style={{ color: C.accent, fontSize: 12, fontWeight: "600" }}>Second opinion</Text> : null}
        <Text onPress={() => onRate(1)} style={{ fontSize: 16, opacity: m.rating === -1 ? 0.3 : 1 }}>{m.rating === 1 ? "👍" : "👍🏻"}</Text>
        <Text onPress={() => onRate(-1)} style={{ fontSize: 16, opacity: m.rating === 1 ? 0.3 : 1 }}>👎</Text>
      </View>
    </View>
  );
}

const Tab = ({ label, on, onPress }: { label: string; on: boolean; onPress: () => void }) => (
  <Pressable onPress={onPress} style={{ backgroundColor: on ? C.text : C.card2, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7 }}>
    <Text style={{ color: on ? "#FFF" : C.text, fontWeight: "600", fontSize: 13 }}>{label}</Text>
  </Pressable>
);


// One conversation page (like ChatGPT): type, dictate with the mic, or switch on voice mode, all in the same session.
export default function Ananta() {
  const params = useLocalSearchParams<{ q?: string; t?: string }>();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [thread, setThread] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [claude, setClaude] = useState(false);
  const [phase, setPhase] = useState<Phase>("off");         // voice mode: off / listening / thinking / speaking
  const live = phase !== "off";
  const [note, setNote] = useState("");
  const [sessions, setSessions] = useState(false);
  const [qcat, setQcat] = useState("portfolio");
  const [err, setErr] = useState<string | null>(null);
  const [ctx, setCtx] = useScreen();
  const { data: sg } = useData("/v3/ask/suggestions", 0);
  const scroll = useRef<ScrollView>(null);
  const lastParam = useRef<string | undefined>(undefined);
  const threadRef = useRef<string | null>(null), claudeRef = useRef(false), dictating = useRef(false);
  threadRef.current = thread; claudeRef.current = claude;
  useEffect(() => { TTS.init(); }, []);
  const sst = useRef({ offset: { y: 0 }, height: { h: 0 }, content: { h: 0 } }).current;
  useFocusEffect(useCallback(() => { setScreen({ screen: "ananta", label: "Ananta tab: this conversation" }); setScroller({ ref: scroll, ...sst }); }, []));
  const ctxRef = useRef(ctx);
  ctxRef.current = ctx;
  // what is on screen (so Ananta knows where he is) + for spoken answers, which voice to prepare ahead
  const where = (voice = false) => ({ here: getScreen() ?? undefined, about: ctxRef.current ?? undefined,
    tts: voice ? TTS.prepHint() : undefined });
  useEffect(() => { setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 80); }, [msgs.length, busy]);
  const [kb, setKb] = useState(false);
  useEffect(() => {
    const a = Keyboard.addListener("keyboardWillShow", () => setKb(true)), b = Keyboard.addListener("keyboardWillHide", () => setKb(false));
    const c = Keyboard.addListener("keyboardDidShow", () => setKb(true)), d = Keyboard.addListener("keyboardDidHide", () => setKb(false));
    return () => { a.remove(); b.remove(); c.remove(); d.remove(); };
  }, []);
  const [atEnd, setAtEnd] = useState(true);
  const checkEnd = () => setAtEnd(sst.content.h - (sst.offset.y + sst.height.h) < 160);
  const shareSession = async () => {
    let txt = "";
    try { if (thread) txt = (await api(`/v3/ask/thread/${thread}/export`)).text; } catch { /* use what is on screen */ }
    if (!txt) txt = msgs.map((m) => (m.role === "user" ? `MADHAV${m.voice ? " (voice)" : ""}: ${m.text}` : `ANANTA (${m.model_label ?? ""}${m.ms ? `, ${(m.ms / 1000).toFixed(1)}s` : ""}): ${m.answer ?? m.error ?? ""}`)).join("\n\n");
    if (txt) Share.share({ message: txt, title: "Ananta session" });
  };

  // ---- typed (or dictated) questions: answers are shown, not spoken ----
  const handleTextAnswer = async (r: any) => {
    if (r.thread) setThread(r.thread);
    setMsgs((m) => [...m, { role: "assistant", ...r }]);
    if (r.tour?.length) {                                      // guided tour: talk + move + point, step by step
      await UI.playTour(r.tour, (t) => TTS.speakText(t));
      return;
    }
    if (r.ui?.length) {                                         // move the screen first (only what really happened counts)
      const res = await UI.run(r.ui);
      const bad = res.filter((x) => !x.ok);
      if (bad.length) {
        const failNote = `I couldn't open ${bad.map((b) => b.action.label ?? b.action.target).join(", ")}. You're still on ${getScreen()?.label ?? "the same screen"}.`;
        setMsgs((m) => [...m, { role: "assistant", kind: "answer", answer: failNote, model_label: "App" }]);
      }
    }
    if (r.points?.length) UI.pointAlong(r.answer ?? "", r.points);
  };

  const send = async (q: string) => {
    q = q.trim();
    if (!q || busy) return;
    setText("");
    setErr(null);
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await api("/v3/ask", { text: q, thread: threadRef.current, mode: claudeRef.current ? "deep" : "auto", context: where() });
      handleTextAnswer(r);
    } catch (e: any) {
      handleTextAnswer({ error: e?.message ?? String(e) });
    } finally {
      setBusy(false);
    }
  };

  // ---- voice mode: one state machine (src/voiceloop.ts) drives listen -> think -> speak -> listen ----
  // What Ananta says aloud for an answer: the answer, the "did you mean" choices, and any screen it could not open.
  const spokenText = (r: any, failNote: string) => {
    let t = String(r.error ?? r.answer ?? "");
    const opts: string[] = r.kind === "clarify" ? (r.options ?? []).slice(0, 4) : [];
    if (opts.length && !opts.every((o) => t.toLowerCase().includes(String(o).toLowerCase()))) {
      t += ` Did you mean ${opts.slice(0, -1).join(", ")}${opts.length > 1 ? ", or " : ""}${opts[opts.length - 1]}?`;
    }
    return [t, failNote].filter(Boolean).join(" ");
  };

  const micRef = useRef<ReturnType<typeof useMic> | null>(null);
  const loopRef = useRef<VoiceLoop | null>(null);
  const lastActive = useRef(Date.now());
  if (!loopRef.current) {
    loopRef.current = new VoiceLoop({
      micStart: (force) => micRef.current!.start(force),
      micStop: () => micRef.current!.cancel(),
      micSend: () => micRef.current!.send(),
      micBusy: () => micRef.current!.busy(),
      micHearing: () => micRef.current!.hearing(),
      ask: async (b64) => {
        try {
          const r = await api("/v3/voice/turn", { audio_b64: b64, mime: "audio/wav", thread: threadRef.current,
            mode: claudeRef.current ? "deep" : "auto", context: where(true) }, 60000);
          if (r.thread) setThread(r.thread);
          if (r.heard) setMsgs((m) => [...m, { role: "user", text: r.heard, voice: true }]);
          if (r.answer || r.error || r.tour?.length) setMsgs((m) => [...m, { role: "assistant", voice: true, ...r }]);
          return r;
        } catch (e: any) {
          const r = { error: e?.message ?? String(e) };
          setMsgs((m) => [...m, { role: "assistant", voice: true, ...r }]);
          return r;
        }
      },
      respond: async (r, current) => {
        if (r.tour?.length) { await UI.playTour(r.tour, (t) => TTS.speakText(t), current); return; }
        let failNote = "";
        if (r.ui?.length && current()) {                       // move the screen first, then talk about it
          const res = await UI.run(r.ui);
          const bad = res.filter((x) => !x.ok);
          if (bad.length) {
            failNote = `I couldn't open ${bad.map((b) => b.action.label ?? b.action.target).join(", ")}. You're still on ${getScreen()?.label ?? "the same screen"}.`;
            setMsgs((m) => [...m, { role: "assistant", kind: "answer", answer: failNote, model_label: "App" }]);
          }
        }
        if (!current()) return;
        // the service already made the audio for r.speak (voice_id); a note about a screen that didn't open is added on top
        const base = r.speak ?? spokenText(r, "");
        const t = failNote ? `${base} ${failNote}`.trim() : base;
        const id = failNote ? undefined : r.voice_id;
        if (t) await UI.pointAlong(t, r.points, (parts, onPart) => TTS.speak(parts, onPart, id));
      },
      stopSpeaking: () => { TTS.stop(); clearSpot(); },
      onPhase: (p) => {
        setPhase(p);
        setVoiceLive(p !== "off");
        lastActive.current = Date.now();
        if (p === "thinking") Haptics.tap();                     // you feel it when Ananta got your question
        if (p !== "listening") setNote("");
      },
      onNote: (m) => setNote(m),
    });
  }
  const loop = loopRef.current;

  const onTurn = async (b64: string) => {
    if (loop.on) { loop.onAudio(b64); return; }
    if (!dictating.current) return;
    dictating.current = false;                                   // mic button: the words become the question
    setBusy(true);
    try {
      const r = await api("/v3/voice/transcribe", { audio_b64: b64, mime: "audio/wav" });
      setBusy(false);
      if (r.text) send(r.text); else setErr("I didn't catch that. Try again a little closer to the phone.");
    } catch (e: any) {
      setBusy(false);
      setErr(e?.message ?? String(e));
    }
  };
  const onNoSpeech = () => {
    if (loop.on) { loop.onNoSpeech(); return; }
    if (dictating.current) { dictating.current = false; setErr("I didn't hear anything. Tap the mic and try again."); }
  };
  const mic = useMic(onTurn, onNoSpeech);
  micRef.current = mic;

  const startLive = async () => {
    if (loop.on) return;                                         // extra taps do nothing
    const p = await requestRecordingPermissionsAsync();
    if (!p.granted) { setErr("Microphone permission is off. Allow it for Expo Go in iPhone Settings."); return; }
    setErr(null);
    TTS.stop();
    Keyboard.dismiss();
    loop.start();
  };
  const endLive = () => { loop.end(); clearSpot(); };
  const dictate = async () => {
    if (mic.status !== "idle") { mic.send(); return; }
    dictating.current = true;
    const ok = await mic.start();
    if (!ok) { dictating.current = false; setErr("Microphone permission is off. Allow it for Expo Go in iPhone Settings."); }
  };
  const pickVoice = (v: string) => {
    if (v === "Phone") TTS.setEngine("phone"); else { TTS.setEngine("natural"); TTS.setVoice(v); }
    const sample = () => TTS.speakText(v === "Phone" ? "This is the phone voice." : "Hi Madhav, this is how I sound now.").then(() => undefined);
    if (loop.on) loop.aside(sample); else sample();
  };

  // voice mode: the watchdog (repairs anything stuck), coming back from the background, and auto-off after 5 quiet minutes
  useEffect(() => {
    if (!live) return;
    const id = setInterval(() => {
      loop.tick();
      if (Date.now() - lastActive.current > 5 * 60000) { endLive(); setErr("Voice mode turned itself off after 5 quiet minutes."); }
    }, 1000);
    const sub = AppState.addEventListener("change", (s) => { if (s === "active") loop.resume(); });
    return () => { clearInterval(id); sub.remove(); };
  }, [live]);
  useEffect(() => { if (mic.status === "hearing") lastActive.current = Date.now(); }, [mic.status]);
  useEffect(() => () => { loop.end(); }, []);

  useEffect(() => {
    if (params.q && params.t !== lastParam.current) {
      lastParam.current = params.t;
      send(String(params.q));
    }
  }, [params.q, params.t]);

  const rate = async (m: Msg, v: number) => {
    if (!m.id) return;
    await api("/v3/ask/rate", { id: m.id, rating: v });
    setMsgs((all) => all.map((x) => (x.id === m.id ? { ...x, rating: v } : x)));
  };
  const second = async (m: Msg) => {
    if (!m.id || busy) return;
    setBusy(true);
    try { handleTextAnswer(await api("/v3/ask/second", { id: m.id })); } catch (e: any) { handleTextAnswer({ error: e?.message }); } finally { setBusy(false); }
  };
  const newSession = () => { endLive(); setMsgs([]); setThread(null); setSessions(false); };
  const openSession = async (th: string) => {
    endLive();
    const r = await api(`/v3/ask/thread/${th}`);
    setMsgs(r.messages);
    setThread(th);
    setSessions(false);
  };

  const qs: string[] = (sg?.[qcat] as string[]) ?? sg?.questions ?? [];
  const micLabel = { idle: "", listening: "Listening…", hearing: "Hearing you…", sending: "Got it…" }[mic.status];
  const hearing = live && phase === "listening" && mic.status === "hearing";
  const liveLabel = phase === "thinking" ? "Thinking…  ·  tap to cancel" : phase === "speaking" ? "Speaking  ·  tap to stop and talk"
    : hearing ? "Hearing you…  ·  tap when done" : mic.status === "sending" ? "Got it…" : "Listening…  just talk";
  const voiceNote = note || (TTS.lastEngine === "phone" && TTS.engine === "natural" ? TTS.lastNote : "");

  if (sessions) return <Sessions onOpen={openSession} onNew={newSession} onBack={() => setSessions(false)} />;

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: C.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, paddingTop: 8 }}>
        <Text style={{ color: claude ? C.faint : C.text, fontWeight: "700" }}>Auto</Text>
        <Switch value={claude} onValueChange={setClaude} trackColor={{ true: C.accent, false: C.line }} />
        <Text style={{ color: claude ? C.text : C.faint, fontWeight: "700" }}>Claude</Text>
        <View style={{ flex: 1 }} />
        {msgs.length ? <Text onPress={shareSession} style={{ color: C.accent, fontWeight: "600", marginRight: 12 }}>Share</Text> : null}
        <Text onPress={() => setSessions(true)} style={{ color: C.accent, fontWeight: "600" }}>Sessions</Text>
        <Text onPress={newSession} style={{ color: C.accent, fontWeight: "600", marginLeft: 12 }}>New</Text>
      </View>
      {ctx && ctx.screen !== "ask" ? (
        <Pressable onPress={() => setCtx(null)} style={{ alignSelf: "flex-start", marginHorizontal: 16, marginTop: 6, flexDirection: "row", gap: 6, backgroundColor: C.accentSoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 }}>
          <Text style={{ color: C.accent, fontSize: 12 }} numberOfLines={1}>About: {ctx.label}  ✕</Text>
        </Pressable>
      ) : null}

      <View style={{ flex: 1 }}>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 24 }} keyboardShouldPersistTaps="handled" keyboardDismissMode="interactive"
        onScroll={(e) => { sst.offset.y = e.nativeEvent.contentOffset.y; checkEnd(); }} scrollEventThrottle={64}
        onLayout={(e) => { sst.height.h = e.nativeEvent.layout.height; checkEnd(); }} onContentSizeChange={(_, h) => { sst.content.h = h; checkEnd(); }}>
        {msgs.length === 0 ? (
          <View style={{ gap: 8, paddingTop: 20 }}>
            <Text style={{ color: C.text, fontSize: 24, fontWeight: "700" }}>Hi Madhav</Text>
            <T dim>Ask about our portfolio or the market. Type, tap the mic to dictate, or tap the wave to just talk.</T>
          </View>
        ) : null}
        {msgs.map((m, i) => (m.role === "user" ? <UserBubble key={i} text={m.text!} voice={m.voice} /> : (
          <View key={i} style={{ gap: 8 }}>
            <Answer m={m} onPick={(q) => send(q)} onRate={(v) => rate(m, v)} onSecond={() => second(m)}
              onSpeak={live ? undefined : () => { UI.pointAlong(m.answer ?? "", m.points, (parts, onPart) => TTS.speak(parts, onPart)); }} />
            {m.voice && i === msgs.length - 1 ? (m.show ?? []).slice(0, 1).map((sh: any, k: number) => <StageCard key={k} sh={sh} open={() => openScreen(sh)} />) : null}
          </View>
        )))}
        {busy && !live ? (
          <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
            <ActivityIndicator color={C.dim} />
            <T dim>Ananta is looking…</T>
          </View>
        ) : null}
        {err ? <Text style={{ color: C.bad }}>{err}</Text> : null}
      </ScrollView>
      {!atEnd ? (
        <Pressable onPress={() => scroll.current?.scrollToEnd({ animated: true })} accessibilityLabel="Jump to latest"
          style={{ position: "absolute", right: 16, bottom: 12, width: 40, height: 40, borderRadius: 20, backgroundColor: C.text, alignItems: "center", justifyContent: "center", opacity: 0.9 }}>
          <Text style={{ color: "#FFF", fontSize: 18, fontWeight: "700" }}>↓</Text>
        </Pressable>
      ) : null}
      {kb ? (
        <Pressable onPress={() => Keyboard.dismiss()} accessibilityLabel="Hide keyboard"
          style={{ position: "absolute", left: 16, bottom: 12, flexDirection: "row", gap: 6, alignItems: "center", backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6 }}>
          <Text style={{ color: C.text, fontSize: 13, fontWeight: "600" }}>⌄ Hide keyboard</Text>
        </Pressable>
      ) : null}
      </View>

      {!live ? (
        <View style={{ gap: 6, paddingBottom: 6 }}>
          <View style={{ flexDirection: "row", gap: 6, paddingHorizontal: 12 }}>
            {[["portfolio", "Our portfolio"], ["market", "Market & scans"]].map(([k, l]) => (
              <Pressable key={k} onPress={() => setQcat(k)} style={{ paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, backgroundColor: qcat === k ? C.text : "transparent" }}>
                <Text style={{ color: qcat === k ? "#FFF" : C.dim, fontSize: 12, fontWeight: "600" }}>{l}</Text>
              </Pressable>
            ))}
          </View>
          <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 12 }}>
            {qs.map((q) => (
              <Pressable key={q} onPress={() => send(q)} style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 7 }}>
                <Text style={{ color: C.text, fontSize: 13 }}>{q}</Text>
              </Pressable>
            ))}
          </ScrollView>
        </View>
      ) : null}

      {live ? (
        <LivePanel label={liveLabel} phase={phase} hearing={hearing} level={mic.level} note={voiceNote}
          onOrb={() => { Haptics.soft(); loop.tap(); }} onEnd={endLive} onVoice={pickVoice}
          rateLabel={TTS.rate} onRate={(r) => TTS.setRate(r)} />
      ) : (
        <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 8, padding: 10, borderTopWidth: 1, borderTopColor: C.line, backgroundColor: C.card }}>
          <Pressable onPress={dictate} style={{ width: 40, height: 40, borderRadius: 20, alignItems: "center", justifyContent: "center",
            backgroundColor: mic.status !== "idle" ? C.bad : C.card2 }}>
            <Text style={{ fontSize: 18 }}>{mic.status !== "idle" ? "■" : "🎙"}</Text>
          </Pressable>
          <TextInput value={mic.status !== "idle" ? micLabel : text} editable={mic.status === "idle"} onChangeText={setText}
            placeholder="Ask Ananta…" placeholderTextColor={C.faint} multiline
            style={{ flex: 1, maxHeight: 110, fontSize: 15, color: C.text, backgroundColor: C.bg, borderRadius: 20, paddingHorizontal: 14, paddingTop: 10, paddingBottom: 10 }} />
          {text.trim() ? (
            <Pressable onPress={() => send(text)} disabled={busy}
              style={{ backgroundColor: busy ? C.line : C.accent, borderRadius: 20, paddingHorizontal: 16, height: 40, justifyContent: "center" }}>
              <Text style={{ color: "#FFF", fontWeight: "700" }}>Send</Text>
            </Pressable>
          ) : (
            <Pressable onPress={startLive} style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: C.accent, alignItems: "center", justifyContent: "center" }}>
              <Wave />
            </Pressable>
          )}
        </View>
      )}
    </KeyboardAvoidingView>
  );
}

// Voice mode panel. The orb shows what Ananta is doing; one tap always does the obvious thing:
// blue = listening (tap: restart the mic) · red = hearing you (tap: done talking) · amber = thinking (tap: cancel) ·
// green = speaking (tap: stop and talk).
function LivePanel({ label, phase, hearing, level, note, onOrb, onEnd, rateLabel, onRate, onVoice }: {
  label: string; phase: Phase; hearing: boolean; level: number; note: string; onOrb: () => void; onEnd: () => void;
  rateLabel: number; onRate: (r: number) => void; onVoice: (v: string) => void;
}) {
  const pulse = useRef(new Animated.Value(1)).current;
  const [r, setR] = useState(rateLabel);
  const [vc, setVc] = useState(TTS.engine === "phone" ? "Phone" : TTS.voice);
  const fast = phase === "thinking";
  useEffect(() => {
    const d = fast ? 350 : 800;
    const a = Animated.loop(Animated.sequence([Animated.timing(pulse, { toValue: fast ? 1.06 : 1.1, duration: d, useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: d, useNativeDriver: true })]));
    a.start();
    return () => a.stop();
  }, [fast]);
  const lv = Math.max(0, Math.min(1, (level + 60) / 50));
  const color = phase === "speaking" ? C.good : phase === "thinking" ? C.warn : hearing ? C.bad : C.accent;
  return (
    <View style={{ alignItems: "center", gap: 10, paddingVertical: 14, borderTopWidth: 1, borderTopColor: C.line, backgroundColor: C.card }}>
      <Pressable onPress={onOrb} hitSlop={16} accessibilityLabel={label}>
        <Animated.View style={{ transform: [{ scale: hearing ? 1 + lv * 0.25 : pulse }], width: 92, height: 92, borderRadius: 46,
          backgroundColor: color, opacity: 0.92 }} />
      </Pressable>
      <Text style={{ color: C.text, fontWeight: "600" }}>{label}</Text>
      {note ? <Text style={{ color: C.dim, fontSize: 12, textAlign: "center", paddingHorizontal: 20 }}>{note}</Text> : null}
      <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
        <Text style={{ color: C.dim, fontSize: 12 }}>Speed</Text>
        {TTS.RATES.map((x) => (
          <Pressable key={x} onPress={() => { setR(x); onRate(x); }} style={{ paddingHorizontal: 9, paddingVertical: 4, borderRadius: 999, backgroundColor: r === x ? C.text : C.card2 }}>
            <Text style={{ color: r === x ? "#FFF" : C.text, fontSize: 12 }}>{String(x)}×</Text>
          </Pressable>
        ))}
      </View>
      <View style={{ flexDirection: "row", gap: 6, alignItems: "center", flexWrap: "wrap", justifyContent: "center", paddingHorizontal: 12 }}>
        <Text style={{ color: C.dim, fontSize: 12 }}>Voice</Text>
        {[...TTS.VOICES, "Phone"].map((v) => (
          <Pressable key={v} onPress={() => { setVc(v); onVoice(v); }} style={{ paddingHorizontal: 9, paddingVertical: 4, borderRadius: 999, backgroundColor: vc === v ? C.text : C.card2 }}>
            <Text style={{ color: vc === v ? "#FFF" : C.text, fontSize: 12 }}>{v}</Text>
          </Pressable>
        ))}
      </View>
      <Pressable onPress={onEnd} style={{ backgroundColor: C.text, borderRadius: 999, paddingHorizontal: 22, paddingVertical: 9 }}>
        <Text style={{ color: "#FFF", fontWeight: "700" }}>End voice</Text>
      </Pressable>
    </View>
  );
}

const Wave = () => (
  <View style={{ flexDirection: "row", gap: 2, alignItems: "center" }}>
    {[8, 14, 18, 14, 8].map((h, i) => <View key={i} style={{ width: 3, height: h, backgroundColor: "#FFF", borderRadius: 2 }} />)}
  </View>
);

function Sessions({ onOpen, onNew, onBack }: { onOpen: (t: string) => void; onNew: () => void; onBack: () => void }) {
  const { data: d } = useData("/v3/ask/threads", 0);
  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: 16, gap: 10 }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <Text onPress={onBack} style={{ color: C.accent, fontWeight: "600" }}>‹ Back</Text>
        <Text onPress={onNew} style={{ color: C.accent, fontWeight: "600" }}>+ New session</Text>
      </View>
      {(d?.threads ?? []).length === 0 ? <T dim>No sessions yet.</T> : null}
      {(d?.threads ?? []).map((th: any) => (
        <Pressable key={th.thread} onPress={() => onOpen(th.thread)} style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 12, padding: 12, gap: 2 }}>
          <Text style={{ color: C.text, fontSize: 15 }} numberOfLines={2}>{th.voice ? "🎙 " : ""}{th.title}</Text>
          <Text style={{ color: C.faint, fontSize: 12 }}>{th.time} · {Math.ceil(th.messages / 2)} question(s)</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}

// "Show me" on an evidence row: open where that number lives and make it glow.
async function showEvidence(e: any) {
  const t = String(e.screen);
  const res = await UI.run([{ do: t.startsWith("coin:") || t.startsWith("trade:") ? "open" : "go_to", target: t, label: e.label }]);
  if (res[0]?.ok && e.spot) {
    const { focusSpot } = await import("../../src/spotlight");
    focusSpot(String(e.spot), 4000);
  }
}
