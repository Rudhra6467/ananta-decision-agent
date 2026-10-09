import * as SecureStore from "expo-secure-store";
import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Animated, AppState, Keyboard, KeyboardAvoidingView, Modal, Platform, Pressable, ScrollView, Share, Switch, Text, TextInput, View } from "react-native";
import { requestRecordingPermissionsAsync } from "expo-audio";
import { useFocusEffect, useLocalSearchParams } from "expo-router";
import { getScreen, goTab, setScreen, setVoiceLive, tourCommand, useScreen } from "../../src/context";
import { showToast } from "../../src/blocks";
import { FirstConversation } from "../../src/firstchat";
import * as UI from "../../src/uiagent";
import { clearSpot, setScroller } from "../../src/spotlight";
import { StageCard } from "../../src/voice";
import { ActionCard, openScreen } from "../../src/actions";
import { useData } from "../../src/useData";
import { api } from "../../src/api";
import { micMime, useMic } from "../../src/mic";
import * as TTS from "../../src/tts";
import * as Haptics from "../../src/haptics";
import { VoiceLoop, type Phase } from "../../src/voiceloop";
import { Bullet, Divider, Pill, Segmented, T } from "../../src/ui";
import { C } from "../../src/theme";
import { useMe } from "../../src/visitor";

// Starter questions on an empty conversation (Madhav: a new person should know what to ask)
const STARTERS = ["What's happening here?", "What are we doing here?", "Show me around", "Which coins are we watching?",
  "Show me the trades", "What are the rule gates?", "How do I make a paper trade?", "What should I watch today?"];
// A visitor's own account: questions about their coins and their book
const GUEST_STARTERS = ["Find me a trade", "How are my coins doing?", "How does my practice book work?", "What can you do?", "Show me around"];

type Msg = { id?: string; role: "user" | "assistant"; text?: string; voice?: boolean; [k: string]: any };
const STAGE: Record<string, string> = { observation: "Observation", candidate: "Candidate setup", "candidate setup": "Candidate setup", setup: "Setup",
  decision: "Decision", execution: "Executed", position: "Open position", outcome: "Outcome", evaluation: "Evaluation", learning: "Learning" };

const UserBubble = ({ text, voice }: { text: string; voice?: boolean }) => (
  <View style={{ alignSelf: "flex-end", maxWidth: "85%", backgroundColor: C.accent, borderRadius: 16, borderBottomRightRadius: 4, paddingHorizontal: 14, paddingVertical: 10 }}>
    <Text style={{ color: C.onInk, fontSize: 15, lineHeight: 21 }}>{voice ? "🎙 " : ""}{text}</Text>
  </View>
);

function Answer({ m, onPick, onRate, onSecond, onSpeak, onShow }: { m: Msg; onPick: (q: string) => void; onRate: (v: number) => void; onSecond: () => void; onSpeak?: () => void; onShow?: () => void }) {
  const [layer, setLayer] = useState<"none" | "breakdown" | "evidence">("none");
  if (m.error) {
    return <View style={{ backgroundColor: C.badSoft, borderRadius: 12, padding: 12 }}><Text style={{ color: C.bad }}>{m.error}</Text></View>;
  }
  // plan 4.2: a recommendation always carries a "Why?" chip (it explains the answer from its decision card and the chain)
  const recommends = m.kind === "answer" && !!(m.next_action || m.card || (m.actions ?? []).length);
  const chips: string[] = m.kind === "clarify" ? m.options ?? []
    : [...(recommends && !(m.follow_ups ?? []).some((f: string) => /^why\b/i.test(f)) ? ["Why?"] : []), ...(m.follow_ups ?? [])];
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

      {m.kind === "answer" && m.next_action?.label ? (
        <Pressable onPress={() => onPick(m.next_action.ask)} style={({ pressed }) => ({ backgroundColor: C.accent, borderRadius: 999, paddingHorizontal: 14,
          paddingVertical: 9, alignSelf: "flex-start", opacity: pressed ? 0.75 : 1 })}>
          <Text style={{ color: C.onInk, fontSize: 14, fontWeight: "700" }}>{m.next_action.label}</Text>
        </Pressable>
      ) : null}
      {m.kind === "answer" && m.next_action?.label && m.voice ? <Text style={{ color: C.faint, fontSize: 11, marginTop: -4 }}>Or just say “yes”.</Text> : null}
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
              <Text style={{ color: C.onInk, fontSize: 13, fontWeight: "600" }}>{sh.label} ›</Text>
            </Pressable>
          ))}
        </View>
      ) : null}
      {m.note ? <Text style={{ color: C.faint, fontSize: 11 }}>{m.note}</Text> : null}
      {onShow && m.showable && !m.voice ? (
        <View style={{ backgroundColor: C.accentSoft, borderRadius: 10, padding: 10, gap: 8 }}>
          <Text style={{ color: C.text, fontSize: 13 }}>Want me to show you this on screen? I'll take you there and talk you through it, then keep listening.</Text>
          <Pressable onPress={onShow} style={({ pressed }) => ({ alignSelf: "flex-start", backgroundColor: C.accent, borderRadius: 8, paddingHorizontal: 14, paddingVertical: 8, opacity: pressed ? 0.7 : 1 })}>
            <Text style={{ color: C.onInk, fontWeight: "700" }}>Yes, show me</Text>
          </Pressable>
        </View>
      ) : null}
      <View style={{ flexDirection: "row", alignItems: "center", gap: 14 }}>
        <Text style={{ color: C.faint, fontSize: 11, flex: 1 }}>
          {m.model_label ?? (m.provider === "gemini" ? "Gemini" : "Claude")} · {m.cost_usd ? `${(m.cost_usd * 100).toFixed(1)}¢` : "free"}{m.ms ? ` · ${(m.ms / 1000).toFixed(1)}s` : ""}{m.lookups?.length ? ` · ${m.lookups.length} lookups` : ""}
        </Text>
        {onSpeak && m.answer ? <Text onPress={onSpeak} style={{ fontSize: 15 }}>🔊</Text> : null}
        {!m.second_of && m.id ? <Text onPress={onSecond} style={{ color: C.accent, fontSize: 12, fontWeight: "600" }}>Second opinion</Text> : null}
        <Text onPress={() => onRate(1)} style={{ fontSize: 16, opacity: m.rating === -1 ? 0.3 : 1 }}>{m.rating === 1 ? "👍" : "👍🏻"}</Text>
        <Text onPress={() => onRate(-1)} style={{ fontSize: 16, opacity: m.rating === 1 ? 0.3 : 1 }}>👎</Text>
      </View>
    </View>
  );
}

const Tab = ({ label, on, onPress }: { label: string; on: boolean; onPress: () => void }) => (
  <Pressable onPress={onPress} style={{ backgroundColor: on ? C.text : C.card2, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7 }}>
    <Text style={{ color: on ? C.onInk : C.text, fontWeight: "600", fontSize: 13 }}>{label}</Text>
  </Pressable>
);


// The open conversation lives outside the page, so leaving Ask Ananta and coming back (or the page being rebuilt by a
// navigation) always shows the same conversation (Madhav, 2026-10-06: "inconsistency moving from ask Ananta page to other and
// coming back"). Another person signing in on the same phone or browser starts empty.
const kept: { msgs: Msg[]; thread: string | null; who: string } = { msgs: [], thread: null, who: "" };

// One conversation page (like ChatGPT): type, dictate with the mic, or switch on voice mode, all in the same session.
export default function Ananta() {
  const params = useLocalSearchParams<{ q?: string; t?: string; intro?: string; tab?: string }>();
  const [tabv, setTabv] = useState<"chat" | "now">(params.tab === "now" ? "now" : "chat");     // plan 3.6a: Chat | Ananta now
  useEffect(() => { if (params.tab === "now" || params.tab === "chat") setTabv(params.tab); }, [params.tab, params.t]);
  const [msgs, setMsgs] = useState<Msg[]>(kept.msgs);
  const [thread, setThread] = useState<string | null>(kept.thread);
  useEffect(() => { kept.msgs = msgs; }, [msgs]);
  useEffect(() => { kept.thread = thread; }, [thread]);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  // Two switches: Auto on/off (Ananta picks a lighter or stronger model per question) and Claude / Google (who answers).
  const [autoOn, setAutoOn] = useState(true);
  const [google, setGoogle] = useState(false);
  useEffect(() => {
    (async () => {
      try {
        const [a, g] = await Promise.all([SecureStore.getItemAsync("ask_auto"), SecureStore.getItemAsync("ask_google")]);
        if (a) setAutoOn(a === "1");
        if (g) setGoogle(g === "1");
      } catch { /* */ }
    })();
  }, []);
  const flip = (k: "ask_auto" | "ask_google", v: boolean) => {
    (k === "ask_auto" ? setAutoOn : setGoogle)(v);
    SecureStore.setItemAsync(k, v ? "1" : "0").catch(() => {});
  };
  const [phase, setPhase] = useState<Phase>("off");         // voice mode: off / listening / thinking / speaking
  const live = phase !== "off";
  const [note, setNote] = useState("");
  const [sessions, setSessions] = useState(false);
  const [qcat, setQcat] = useState("new");
  const [err, setErr] = useState<string | null>(null);
  const [ctx, setCtx] = useScreen();
  const { data: sg } = useData("/v3/ask/suggestions", 0);
  const scroll = useRef<ScrollView>(null);
  const lastParam = useRef<string | undefined>(undefined);
  const threadRef = useRef<string | null>(null), modeRef = useRef("auto"), dictating = useRef(false);
  threadRef.current = thread; modeRef.current = google ? (autoOn ? "google_auto" : "google") : (autoOn ? "auto" : "deep");
  useEffect(() => { TTS.init(); }, []);
  const sst = useRef({ offset: { y: 0 }, height: { h: 0 }, content: { h: 0 } }).current;
  useFocusEffect(useCallback(() => { setScreen({ screen: "ananta", label: "Ananta tab: this conversation" }); setScroller({ ref: scroll, ...sst }); }, []));
  const ctxRef = useRef(ctx);
  ctxRef.current = ctx;
  // what is on screen (so Ananta knows where he is) + for spoken answers, which voice to prepare ahead
  const msgsRef = useRef(msgs);
  msgsRef.current = msgs;
  // plan 3.7: the chips on the last answer travel with a spoken question, so saying a chip's words acts like tapping it
  const chipsNow = () => {
    const a = [...msgsRef.current].reverse().find((m) => m.role === "assistant" && m.kind === "answer");
    return a && (a.next_action || a.follow_ups?.length) ? { next: a.next_action, follow: a.follow_ups ?? [] } : undefined;
  };
  const where = (voice = false) => ({ here: getScreen() ?? undefined, about: ctxRef.current ?? undefined,
    tts: voice ? TTS.prepHint() : undefined, chips: voice ? chipsNow() : undefined });
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

  // ---- typed (or dictated) questions: answers are shown, not spoken, and the screen stays where it is ----
  // Madhav (2026-10-03): a silent jump to another screen is confusing. A typed answer only offers "Show me on screen";
  // tapping it walks him through with voice (move, highlight, speak) and then turns voice mode on for follow-ups.
  // A plain navigation command ("open markets", answered instantly by the app) still moves straight away: he asked for that.
  const handleTextAnswer = async (r: any) => {
    if (r.thread) setThread(r.thread);
    const plan = !!(r.tour?.length || r.ui?.length || r.points?.length);
    if (r.mode === "nav" && r.ui?.length && !r.tour?.length) {
      setMsgs((m) => [...m, { role: "assistant", ...r }]);
      const res = await UI.run(r.ui);
      const bad = res.filter((x) => !x.ok);
      if (bad.length) {
        const failNote = `I couldn't open ${bad.map((b) => b.action.label ?? b.action.target).join(", ")}. You're still on ${getScreen()?.label ?? "the same screen"}.`;
        setMsgs((m) => [...m, { role: "assistant", kind: "answer", answer: failNote, model_label: "App" }]);
      }
      return;
    }
    setMsgs((m) => [...m, { role: "assistant", ...r, showable: plan }]);
  };

  const walking = useRef(false);
  const walkThrough = async (m: Msg) => {
    if (walking.current || loopRef.current?.on) return;
    walking.current = true;
    tourCommand("stop");
    TTS.stop();
    Keyboard.dismiss();
    setVoiceLive(true);                                          // the voice bar shows that Ananta is talking
    try {
      if (m.tour?.length) {
        await UI.playTour(m.tour, (t) => TTS.speakText(t), () => walking.current);
      } else {
        let failNote = "";
        if (m.ui?.length) {
          const res = await UI.run(m.ui);
          const bad = res.filter((x) => !x.ok);
          if (bad.length) failNote = `I couldn't open ${bad.map((b) => b.action.label ?? b.action.target).join(", ")}.`;
        }
        const say = [m.speak ?? m.answer ?? "", failNote].filter(Boolean).join(" ");
        if (say) await UI.pointAlong(say, m.points, (parts, onPart) => TTS.speak(parts, onPart));
      }
      if (walking.current) await comeBack();
    } finally {
      walking.current = false;
      setVoiceLive(false);
    }
    startLive();                                                 // then listen: he can carry on by voice
  };

  // plan 3.7: after walking through another screen, Ananta comes back to Ask Ananta and says the closing line
  const comeBack = async () => {
    const away = getScreen()?.screen && getScreen()?.screen !== "ananta";
    if (away) { goTab("/(tabs)/ask"); await new Promise((r) => setTimeout(r, 450)); }
    const line = `That's the walk-through. Want me to pull anything else up? What's next${vmeRef.current?.guest ? "" : ", sir"}?`;
    setMsgs((m) => [...m, { role: "assistant", kind: "answer", model_label: "Ananta", answer: line, voice: true }]);
    await TTS.speakText(line);
  };

  const send = async (q: string) => {
    q = q.trim();
    if (!q || busy) return;
    setText("");
    setErr(null);
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await api("/v3/ask", { text: q, thread: threadRef.current, mode: modeRef.current, context: where() });
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
  const { data: me } = useData("/v3/me", 0);
  const vme = useMe();
  const vmeRef = useRef<any>(vme);
  vmeRef.current = vme;
  useEffect(() => {
    const w = (vme as any)?.who;
    if (!w) return;
    if (kept.who && kept.who !== w) { setMsgs([]); setThread(null); }
    kept.who = w;
  }, [(vme as any)?.who]);
  const loopRef = useRef<VoiceLoop | null>(null);
  const lastActive = useRef(Date.now());
  // He stopped mid-sentence ("I want to know…"): keep it and join it to what he says next (for 20 s)
  const prefixRef = useRef<{ text: string; t: number } | null>(null);
  if (!loopRef.current) {
    loopRef.current = new VoiceLoop({
      micStart: (force, wanted) => micRef.current!.start(force, wanted),
      micStop: () => micRef.current!.cancel(),
      micSend: () => micRef.current!.send(),
      micBusy: () => micRef.current!.busy(),
      micState: () => micRef.current!.state(),
      ask: async (b64, current) => {
        let r: any;
        const pre = prefixRef.current && Date.now() - prefixRef.current.t < 20000 ? prefixRef.current.text : "";
        // a person says "one sec" when a look-up takes a moment; silence feels like a machine
        const ack = setTimeout(() => { if (current()) TTS.playAck(); }, 1500);
        try {
          r = await api("/v3/voice/turn", { audio_b64: b64, mime: micMime(), thread: threadRef.current,
            mode: modeRef.current, context: where(true), prefix: pre || undefined }, 60000);
        } catch (e: any) {
          r = { error: e?.message ?? String(e) };
        } finally {
          clearTimeout(ack);
        }
        if (!current()) return r;                              // cancelled, ended or a new session meanwhile: leave the screen alone
        if (r.ignored) { TTS.stop(); return {}; }              // "hmm", "okay", or the mic hearing Ananta itself: just keep listening
        if (r.partial) {                                       // cut off mid-sentence: wait for the rest
          TTS.stop();
          prefixRef.current = { text: r.heard, t: Date.now() };
          setNote(`“${r.heard}…” go on, I'm listening.`);
          return {};
        }
        prefixRef.current = null;
        if (r.thread) setThread(r.thread);
        if (r.heard) setMsgs((m) => [...m, { role: "user", text: r.heard, voice: true }]);
        if (r.answer || r.error || r.tour?.length) setMsgs((m) => [...m, { role: "assistant", voice: true, ...r }]);
        return r;
      },
      respond: async (r, current) => {
        if (r.tour?.length) {                                  // one step at a time; each step tells the watchdog it is still busy
          await UI.playTour(r.tour, (t) => { loopRef.current?.touch(); return TTS.speakText(t); }, current);
          if (current()) await comeBack();
          return;
        }
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
        // a walk-through of another screen (not a plain "open Watchlists") ends back here with the closing line
        if (current() && r.ui?.length && r.mode !== "nav" && getScreen()?.screen !== "ananta") await comeBack();
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
      const r = await api("/v3/voice/transcribe", { audio_b64: b64, mime: micMime() });
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
    if (loop.on) return;
    setErr(null);
    tourCommand("stop");                                         // a tour that was talking stops
    TTS.stop();
    Keyboard.dismiss();
    prefixRef.current = null;
    TTS.warmAcks().catch(() => {});                              // the "one sec" clips, ready on the phone
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
    if (v === "Phone") TTS.setEngine("phone"); else { TTS.setEngine("natural"); TTS.setVoice(v).then(() => TTS.warmAcks()).catch(() => {}); }
    const sample = () => TTS.speakText(v === "Phone" ? "This is the phone voice." : "Hi Madhav, this is how I sound now.").then(() => undefined);
    if (!loop.on) { sample(); return; }
    loop.aside(sample).then((played) => { if (!played) setNote(`Voice set to ${v}. You'll hear it on the next answer.`); });
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

  // "Start trading -> Use Ananta" (a visitor): Ananta opens the conversation by asking whether to find a trade.
  const lastIntro = useRef<string | undefined>(undefined);
  useEffect(() => {
    if (params.intro !== "find_trade" || params.t === lastIntro.current) return;
    lastIntro.current = params.t;
    loopRef.current?.end();
    setThread(null);
    const nm = vme?.profile?.name || vme?.name || me?.profile?.name || me?.name || "";
    setMsgs([{ role: "assistant", kind: "answer", model_label: "Ananta", answer: `Hi${nm ? ` ${nm}` : ""}! Your practice book is ready. Do you want me to find a trade for you among your coins?`,
      next_action: { label: "Yes, find me a trade", ask: "Yes, find me a trade among my coins." },
      follow_ups: ["First, how are my coins doing?", "How do you pick a trade?", "Not now"] }]);
  }, [params.intro, params.t, vme?.name]);

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

  // plan 3.6a: "Ask Ananta to trade / evaluate": voice on, a greeting, and two choices
  const tradeEvaluate = async () => {
    const sir = !me?.guest;
    const h = new Date().getHours();
    const part = h < 5 ? "Good evening" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
    const nm = me?.profile?.name || me?.name || "";
    const greet = `${part}${sir ? ", sir" : nm ? `, ${nm}` : ""}. Shall I find you a trade, or rate your open positions from weakest to strongest?`;
    setThread(null);
    setMsgs([{ role: "assistant", kind: "answer", model_label: "Ananta", answer: greet,
      next_action: { label: "Find me a trade", ask: "Find me a trade: look at the coins and tell me the best setup right now, with a plan." },
      follow_ups: ["Rate my open positions from weakest to strongest", "What are you watching right now?"] }]);
    await startLive();
    loop.aside(() => TTS.speakText(greet).then(() => undefined)).catch(() => {});
  };
  const openSession = async (th: string) => {
    endLive();
    const r = await api(`/v3/ask/thread/${th}`);
    setMsgs(r.messages);
    setThread(th);
    setSessions(false);
  };

  const qs: string[] = me?.guest ? GUEST_STARTERS : qcat === "new" ? STARTERS : (sg?.[qcat] as string[]) ?? sg?.questions ?? [];
  const micLabel = { idle: "", listening: "Listening…", hearing: "Hearing you…", sending: "Got it…" }[mic.status];
  const hearing = live && phase === "listening" && mic.status === "hearing";
  const liveLabel = phase === "thinking" ? "Thinking…  ·  tap to cancel" : phase === "speaking" ? "Speaking  ·  tap to stop and talk"
    : hearing ? "Hearing you…  ·  tap when done" : mic.status === "sending" ? "Got it…" : "Listening…  just talk";
  const voiceNote = note || (TTS.lastEngine === "phone" && TTS.engine === "natural" ? TTS.lastNote : "");

  const top = (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 16, paddingTop: 8 }}>
      <Pressable onPress={() => setSessions(true)} hitSlop={10} accessibilityLabel="Sessions"
        style={{ width: 34, height: 34, borderRadius: 10, borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" }}>
        <Text style={{ color: C.text, fontSize: 16 }}>☰</Text>
      </Pressable>
      <View style={{ flex: 1 }}>
        <Segmented value={tabv} onChange={(k) => setTabv(k as any)} options={[{ key: "chat", label: "Chat" }, { key: "now", label: "Ananta now" }]} />
      </View>
    </View>
  );
  const drawer = <SessionsDrawer open={sessions} onClose={() => setSessions(false)} onOpen={openSession} onNew={newSession} current={thread} />;
  // Phase 5: a visitor who has not finished the first conversation meets Ananta here first
  if ((vme as any)?.guest && (vme as any)?.onboard && (vme as any).onboard !== "done") {
    return <FirstConversation onDone={() => { setMsgs([{ role: "assistant", kind: "answer", model_label: "Ananta", answer: "That's it. Ask me anything, or tell me what to watch.",
      follow_ups: ["What are you watching for me?", "Show me the setup you like most", "How does a stop work?"] }]); }} />;
  }
  if (tabv === "now") return <View style={{ flex: 1, backgroundColor: C.bg }}>{top}<AnantaNow />{drawer}</View>;

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: C.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
      {top}
      {drawer}
      <View style={{ flexDirection: "row", alignItems: "center", flexWrap: "wrap", rowGap: 4, gap: 8, paddingHorizontal: 16, paddingTop: 8 }}>
        <Text style={{ color: autoOn ? C.text : C.faint, fontWeight: "700" }}>Auto</Text>
        <Switch value={autoOn} onValueChange={(v) => flip("ask_auto", v)} trackColor={{ true: C.accent, false: C.line }} />
        <View style={{ width: 6 }} />
        <Text style={{ color: google ? C.faint : C.text, fontWeight: "700" }}>Claude</Text>
        <Switch value={google} onValueChange={(v) => flip("ask_google", v)} trackColor={{ true: C.accent, false: C.line }} />
        <Text style={{ color: google ? C.text : C.faint, fontWeight: "700" }}>Google</Text>
        <View style={{ flex: 1 }} />
        {msgs.length ? <Text onPress={shareSession} style={{ color: C.accent, fontWeight: "600", marginRight: 12 }}>Share</Text> : null}
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
            <Text style={{ color: C.text, fontSize: 24, fontWeight: "700" }}>{me?.guest ? `Hi ${me?.name || "there"}` : "Hello, sir"}</Text>
            <T dim>{me?.guest ? "Ask me about your coins, your practice book, or the market. Type, tap the mic to dictate, or tap the wave and just talk."
              : "Ask about our portfolio or the market. Type, tap the mic to dictate, or tap the wave to just talk."}</T>
            <Pressable onPress={tradeEvaluate} accessibilityRole="button" style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 10,
              backgroundColor: C.accent, borderRadius: 14, paddingHorizontal: 16, paddingVertical: 13, marginTop: 6, opacity: pressed ? 0.85 : 1 })}>
              <Wave />
              <View style={{ flex: 1 }}>
                <Text style={{ color: C.onInk, fontWeight: "800", fontSize: 16 }}>Ask Ananta to trade / evaluate</Text>
                <Text style={{ color: C.onInk, fontSize: 12, opacity: 0.85 }}>Voice on: find a trade, or rate your open positions</Text>
              </View>
            </Pressable>
            <T small>{me?.guest ? "Or try one of the questions below." : 'New here? Tap "New here" below for questions to start with.'}</T>
          </View>
        ) : null}
        {msgs.map((m, i) => (m.role === "user" ? <UserBubble key={i} text={m.text!} voice={m.voice} /> : (
          <View key={i} style={{ gap: 8 }}>
            <Answer m={m} onPick={(q) => send(q)} onRate={(v) => rate(m, v)} onSecond={() => second(m)}
              onSpeak={live ? undefined : () => { TTS.speak(UI.sentences(m.answer ?? ""), () => {}); }}
              onShow={live ? undefined : () => walkThrough(m)} />
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
          <Text style={{ color: C.onInk, fontSize: 18, fontWeight: "700" }}>↓</Text>
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
            {(me?.guest ? [] : [["new", "New here"], ["portfolio", "Our portfolio"], ["market", "Market & scans"]]).map(([k, l]) => (
              <Pressable key={k} onPress={() => setQcat(k)} style={{ paddingHorizontal: 10, paddingVertical: 4, borderRadius: 999, backgroundColor: qcat === k ? C.text : "transparent" }}>
                <Text style={{ color: qcat === k ? C.onInk : C.dim, fontSize: 12, fontWeight: "600" }}>{l}</Text>
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
              <Text style={{ color: C.onInk, fontWeight: "700" }}>Send</Text>
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
            <Text style={{ color: r === x ? C.onInk : C.text, fontSize: 12 }}>{String(x)}×</Text>
          </Pressable>
        ))}
      </View>
      <View style={{ flexDirection: "row", gap: 6, alignItems: "center", flexWrap: "wrap", justifyContent: "center", paddingHorizontal: 12 }}>
        <Text style={{ color: C.dim, fontSize: 12 }}>Voice</Text>
        {[...TTS.VOICES, "Phone"].map((v) => (
          <Pressable key={v} onPress={() => { setVc(v); onVoice(v); }} style={{ paddingHorizontal: 9, paddingVertical: 4, borderRadius: 999, backgroundColor: vc === v ? C.text : C.card2 }}>
            <Text style={{ color: vc === v ? C.onInk : C.text, fontSize: 12 }}>{v}</Text>
          </Pressable>
        ))}
      </View>
      <Pressable onPress={onEnd} style={{ backgroundColor: C.text, borderRadius: 999, paddingHorizontal: 22, paddingVertical: 9 }}>
        <Text style={{ color: C.onInk, fontWeight: "700" }}>End voice</Text>
      </Pressable>
    </View>
  );
}

const Wave = () => (
  <View style={{ flexDirection: "row", gap: 2, alignItems: "center" }}>
    {[8, 14, 18, 14, 8].map((h, i) => <View key={i} style={{ width: 3, height: h, backgroundColor: C.onInk, borderRadius: 2 }} />)}
  </View>
);

// Sessions in a drawer (plan 3.6b, D10): automatic titles; copy and delete beside each. Deleting: a visitor's is gone for good,
// Madhav's goes to an archive kept 30 days.
function SessionsDrawer({ open, onClose, onOpen, onNew, current }: { open: boolean; onClose: () => void; onOpen: (t: string) => void; onNew: () => void; current: string | null }) {
  const { data: d, reload } = useData(open ? "/v3/ask/threads" : null, 0);
  const copy = async (th: string) => {
    try {
      const txt = (await api(`/v3/ask/thread/${th}/export`)).text;
      if (Platform.OS === "web" && (navigator as any)?.clipboard) { await (navigator as any).clipboard.writeText(txt); showToast("Copied ✓"); }
      else Share.share({ message: txt, title: "Ananta session" });
    } catch { showToast("Could not copy it"); }
  };
  const del = async (th: string) => {
    const ok = Platform.OS === "web" ? window.confirm("Delete this conversation?") : true;
    if (!ok) return;
    try { await api(`/v3/ask/thread/${th}/delete`, {}); showToast("Deleted ✓"); reload(); if (th === current) onNew(); } catch { showToast("Could not delete it"); }
  };
  return (
    <Modal visible={open} transparent animationType="fade" onRequestClose={onClose}>
      <View style={{ flex: 1, flexDirection: "row" }}>
        <View style={{ width: "84%", maxWidth: 380, backgroundColor: C.bg, paddingTop: 54, borderRightWidth: 1, borderRightColor: C.line }}>
          <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingBottom: 10 }}>
            <Text style={{ color: C.text, fontWeight: "800", fontSize: 18, flex: 1 }}>Sessions</Text>
            <Text onPress={() => { onNew(); onClose(); }} style={{ color: C.accent, fontWeight: "700" }}>+ New</Text>
          </View>
          <ScrollView contentContainerStyle={{ paddingHorizontal: 12, gap: 8, paddingBottom: 40 }}>
            {(d?.threads ?? []).length === 0 ? <T dim>No sessions yet.</T> : null}
            {(d?.threads ?? []).map((th: any) => (
              <View key={th.thread} style={{ backgroundColor: th.thread === current ? C.accentSoft : C.card, borderColor: C.line, borderWidth: 1, borderRadius: 12, padding: 10, gap: 6 }}>
                <Pressable onPress={() => onOpen(th.thread)}>
                  <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }} numberOfLines={2}>{th.voice ? "🎙 " : ""}{th.title}</Text>
                  <Text style={{ color: C.faint, fontSize: 12 }}>{th.time} · {Math.ceil(th.messages / 2)} question(s)</Text>
                </Pressable>
                <View style={{ flexDirection: "row", gap: 16 }}>
                  <Text onPress={() => copy(th.thread)} style={{ color: C.accent, fontSize: 13, fontWeight: "600" }}>Copy</Text>
                  <Text onPress={() => del(th.thread)} style={{ color: C.bad, fontSize: 13, fontWeight: "600" }}>Delete</Text>
                </View>
              </View>
            ))}
          </ScrollView>
        </View>
        <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.35)" }} accessibilityLabel="Close sessions" />
      </View>
    </Modal>
  );
}

// Ananta now (plan 3.6a): what Ananta is doing for this account right now, and what changed today. Each line opens its details.
function AnantaNow() {
  const { data: s, loading, reload } = useData("/v3/agent/state", 30000);
  const since = Math.floor(new Date().setHours(0, 0, 0, 0) / 1000);
  const { data: a } = useData(`/v3/agent/activity?since_t=${since}`, 60000);
  const go = (l: any) => {
    const t = String(l.text).toLowerCase();
    if (t.includes("watch")) goTab("/(tabs)/watchlists");
    else if (t.includes("position") || t.includes("monitor")) goTab("/(tabs)/portfolio");
    else if (t.includes("need")) goTab("/(tabs)/today");
  };
  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14 }}>
      <View style={{ backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 14, gap: 4 }}>
        {!s && loading ? <ActivityIndicator color={C.dim} /> : null}
        {(s?.lines ?? []).map((l: any, i: number) => (
          <View key={i}>
            {i ? <Divider /> : null}
            <Pressable onPress={() => go(l)} style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 10 }}>
              <View style={{ width: 10, height: 10, borderRadius: 5, backgroundColor: l.tone === "act" ? C.warn : l.tone === "wait" ? C.accent : C.good }} />
              <Text style={{ color: C.text, fontSize: 16, flex: 1 }}>{l.text}</Text>
              <Text style={{ color: C.faint, fontSize: 18 }}>›</Text>
            </Pressable>
          </View>
        ))}
        {s?.waiting_for ? <T small dim>Waiting for: {s.waiting_for}</T> : null}
      </View>
      <Text style={{ color: C.text, fontWeight: "700", fontSize: 16 }}>What changed today</Text>
      <View style={{ backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: C.line, padding: 14, gap: 8 }}>
        {(a?.events ?? []).length === 0 ? <T dim>Nothing yet today.</T> : null}
        {(a?.events ?? []).slice(0, 20).map((x: any) => (
          <View key={x.id} style={{ gap: 2 }}>
            <Text style={{ color: C.text, fontWeight: "600" }}>{x.title}</Text>
            {x.body ? <Text style={{ color: C.dim, fontSize: 13 }}>{x.body}</Text> : null}
            <Text style={{ color: C.faint, fontSize: 11 }}>{new Date(x.t * 1000).toLocaleTimeString([], { hour: "numeric", minute: "2-digit" })}</Text>
          </View>
        ))}
      </View>
      <Text onPress={reload} style={{ color: C.accent, fontWeight: "600", textAlign: "center" }}>Refresh</Text>
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
