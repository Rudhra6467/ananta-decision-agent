import { useCallback, useEffect, useRef, useState } from "react";
import { ActivityIndicator, Animated, KeyboardAvoidingView, Platform, Pressable, ScrollView, Switch, Text, TextInput, View } from "react-native";
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
        {m.kind === "cannot_do_yet" ? <Pill text="CAN'T DO THAT YET" color={C.warn} bg={C.warnSoft} /> : null}
      </View>
      <Text style={{ color: C.text, fontSize: 15, lineHeight: 22 }}>{m.answer}</Text>
      {m.assumption ? <T small>Assumed: {m.assumption}</T> : null}

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
                <Text style={{ color: C.text, fontSize: 13, fontWeight: "600", maxWidth: "50%", textAlign: "right" }}>{String(e.value)}</Text>
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
  const [live, setLive] = useState(false);                 // voice mode
  const [speaking, setSpeaking] = useState(false);
  const [sessions, setSessions] = useState(false);
  const [qcat, setQcat] = useState("portfolio");
  const [err, setErr] = useState<string | null>(null);
  const [ctx, setCtx] = useScreen();
  const { data: sg } = useData("/v3/ask/suggestions", 0);
  const scroll = useRef<ScrollView>(null);
  const lastParam = useRef<string | undefined>(undefined);
  const liveRef = useRef(false), threadRef = useRef<string | null>(null), claudeRef = useRef(false), dictating = useRef(false);
  liveRef.current = live; threadRef.current = thread; claudeRef.current = claude;
  useEffect(() => { TTS.init(); }, []);
  const sst = useRef({ offset: { y: 0 }, height: { h: 0 }, content: { h: 0 } }).current;
  useFocusEffect(useCallback(() => { setScreen({ screen: "ananta", label: "Ananta tab: this conversation" }); setScroller({ ref: scroll, ...sst }); }, []));
  const where = () => ({ here: getScreen() ?? undefined, about: ctx ?? undefined });
  useEffect(() => { setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 80); }, [msgs.length, busy]);

  const listenAgain = () => { if (liveRef.current) setTimeout(() => mic.start(), 250); };
  const speak = (t: string) => {
    setSpeaking(true);
    TTS.say(t, () => { setSpeaking(false); listenAgain(); });
  };

  const handleAnswer = async (r: any, spoken: boolean) => {
    if (r.thread) setThread(r.thread);
    setMsgs((m) => [...m, { role: "assistant", voice: spoken, ...r }]);
    let failNote = "";
    if (r.ui?.length) {                                         // move the screen first, then talk (only what really happened counts)
      const res = await UI.run(r.ui);
      const bad = res.filter((x) => !x.ok);
      if (bad.length) {
        failNote = `I couldn't open ${bad.map((b) => b.action.label ?? b.action.target).join(", ")}. You're still on ${getScreen()?.label ?? "the same screen"}.`;
        setMsgs((m) => [...m, { role: "assistant", kind: "answer", answer: failNote, model_label: "App" }]);
      }
    }
    if (spoken && liveRef.current) {
      const t = [r.error ?? r.answer, failNote].filter(Boolean).join(" ");
      if (!t) { listenAgain(); return; }
      setSpeaking(true);
      UI.pointAlong(t, r.points, (parts, onPart) => TTS.sayParts(parts, onPart, () => { setSpeaking(false); clearSpot(); listenAgain(); }));
    } else if (r.points?.length) {
      UI.pointAlong(r.answer ?? "", r.points);
    }
  };

  const send = async (q: string, spoken = false) => {
    q = q.trim();
    if (!q || busy) return;
    setText("");
    setErr(null);
    setMsgs((m) => [...m, { role: "user", text: q, voice: spoken }]);
    setBusy(true);
    try {
      const r = await api("/v3/ask", { text: q, thread: threadRef.current, mode: claudeRef.current ? "deep" : "everyday", context: where() });
      handleAnswer(r, spoken || liveRef.current);
    } catch (e: any) {
      handleAnswer({ error: e?.message ?? String(e) }, spoken || liveRef.current);
    } finally {
      setBusy(false);
    }
  };

  const onTurn = async (b64: string) => {
    setBusy(true);
    try {
      if (dictating.current) {                                     // mic button: words go into the question and are sent
        dictating.current = false;
        const r = await api("/v3/voice/transcribe", { audio_b64: b64, mime: "audio/wav" });
        setBusy(false);
        if (r.text) send(r.text, false); else setErr("I didn't catch that. Try again a little closer to the phone.");
        return;
      }
      const r = await api("/v3/voice/turn", { audio_b64: b64, mime: "audio/wav", thread: threadRef.current,
        mode: claudeRef.current ? "deep" : "everyday", context: where() });
      if (r.heard) setMsgs((m) => [...m, { role: "user", text: r.heard, voice: true }]);
      if (!r.heard && !r.answer) { setBusy(false); listenAgain(); return; }      // nothing said: keep listening quietly
      handleAnswer(r, true);
    } catch (e: any) {
      handleAnswer({ error: e?.message ?? String(e) }, true);
    } finally {
      setBusy(false);
    }
  };
  const mic = useMic(onTurn, () => { if (liveRef.current) listenAgain(); });

  const startLive = async () => {
    TTS.stop();
    setLive(true);
    liveRef.current = true;
    setVoiceLive(true);
    const ok = await mic.start();
    if (!ok) { setLive(false); setErr("Microphone permission is off. Allow it for Expo Go in iPhone Settings."); }
  };
  const endLive = () => { setLive(false); liveRef.current = false; setVoiceLive(false); TTS.stop(); setSpeaking(false); mic.cancel(); };
  const dictate = async () => {
    if (mic.status !== "idle") { mic.send(); return; }
    dictating.current = true;
    const ok = await mic.start();
    if (!ok) { dictating.current = false; setErr("Microphone permission is off. Allow it for Expo Go in iPhone Settings."); }
  };

  // live mode: auto-off after 5 quiet minutes
  const lastActive = useRef(Date.now());
  useEffect(() => { lastActive.current = Date.now(); }, [msgs.length]);
  useEffect(() => {
    if (!live) return;
    const id = setInterval(() => { if (Date.now() - lastActive.current > 5 * 60000) { endLive(); setErr("Voice mode turned itself off after 5 quiet minutes."); } }, 10000);
    return () => clearInterval(id);
  }, [live]);

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
    try { handleAnswer(await api("/v3/ask/second", { id: m.id }), false); } catch (e: any) { handleAnswer({ error: e?.message }, false); } finally { setBusy(false); }
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
  const liveLabel = busy ? "Thinking…" : speaking ? "Speaking · tap to interrupt" : mic.status === "hearing" ? "Hearing you…" : mic.status === "sending" ? "Got it…" : "Listening… just talk";

  if (sessions) return <Sessions onOpen={openSession} onNew={newSession} onBack={() => setSessions(false)} />;

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: C.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 8, paddingHorizontal: 16, paddingTop: 8 }}>
        <Text style={{ color: claude ? C.faint : C.text, fontWeight: "700" }}>Gemini</Text>
        <Switch value={claude} onValueChange={setClaude} trackColor={{ true: C.accent, false: C.line }} />
        <Text style={{ color: claude ? C.text : C.faint, fontWeight: "700" }}>Claude</Text>
        <View style={{ flex: 1 }} />
        <Text onPress={() => setSessions(true)} style={{ color: C.accent, fontWeight: "600" }}>Sessions</Text>
        <Text onPress={newSession} style={{ color: C.accent, fontWeight: "600", marginLeft: 12 }}>New</Text>
      </View>
      {ctx && ctx.screen !== "ask" ? (
        <Pressable onPress={() => setCtx(null)} style={{ alignSelf: "flex-start", marginHorizontal: 16, marginTop: 6, flexDirection: "row", gap: 6, backgroundColor: C.accentSoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 4 }}>
          <Text style={{ color: C.accent, fontSize: 12 }} numberOfLines={1}>About: {ctx.label}  ✕</Text>
        </Pressable>
      ) : null}

      <ScrollView ref={scroll} contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 24 }} keyboardShouldPersistTaps="handled"
        onScroll={(e) => { sst.offset.y = e.nativeEvent.contentOffset.y; }} scrollEventThrottle={64}
        onLayout={(e) => { sst.height.h = e.nativeEvent.layout.height; }} onContentSizeChange={(_, h) => { sst.content.h = h; }}>
        {msgs.length === 0 ? (
          <View style={{ gap: 8, paddingTop: 20 }}>
            <Text style={{ color: C.text, fontSize: 24, fontWeight: "700" }}>Hi Madhav</Text>
            <T dim>Ask about our portfolio or the market. Type, tap the mic to dictate, or tap the wave to just talk.</T>
          </View>
        ) : null}
        {msgs.map((m, i) => (m.role === "user" ? <UserBubble key={i} text={m.text!} voice={m.voice} /> : (
          <View key={i} style={{ gap: 8 }}>
            <Answer m={m} onPick={(q) => send(q)} onRate={(v) => rate(m, v)} onSecond={() => second(m)}
              onSpeak={() => { TTS.stop(); setSpeaking(true); UI.pointAlong(m.answer ?? "", m.points, (parts, onPart) => TTS.sayParts(parts, onPart, () => { setSpeaking(false); clearSpot(); listenAgain(); })); }} />
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
        <LivePanel label={liveLabel} hearing={mic.status === "hearing"} speaking={speaking} level={mic.level}
          onOrb={() => { if (speaking) { TTS.stop(); } else if (mic.status === "hearing") mic.send(); }} onEnd={endLive}
          rateLabel={TTS.rate} onRate={(r) => TTS.setRate(r)} voiceName={TTS.voiceLabel()} />
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

function LivePanel({ label, hearing, speaking, level, onOrb, onEnd, rateLabel, onRate, voiceName }: {
  label: string; hearing: boolean; speaking: boolean; level: number; onOrb: () => void; onEnd: () => void;
  rateLabel: number; onRate: (r: number) => void; voiceName: string;
}) {
  const pulse = useRef(new Animated.Value(1)).current;
  const [r, setR] = useState(rateLabel);
  useEffect(() => {
    const a = Animated.loop(Animated.sequence([Animated.timing(pulse, { toValue: 1.1, duration: 700, useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: 700, useNativeDriver: true })]));
    a.start();
    return () => a.stop();
  }, []);
  const lv = Math.max(0, Math.min(1, (level + 60) / 50));
  return (
    <View style={{ alignItems: "center", gap: 10, paddingVertical: 14, borderTopWidth: 1, borderTopColor: C.line, backgroundColor: C.card }}>
      <Pressable onPress={onOrb}>
        <Animated.View style={{ transform: [{ scale: hearing ? 1 + lv * 0.25 : pulse }], width: 92, height: 92, borderRadius: 46,
          backgroundColor: speaking ? C.good : hearing ? C.bad : C.accent, opacity: 0.92 }} />
      </Pressable>
      <Text style={{ color: C.text, fontWeight: "600" }}>{label}</Text>
      <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
        <Text style={{ color: C.dim, fontSize: 12 }}>Voice speed</Text>
        {[0.9, 1.0, 1.1, 1.2].map((x) => (
          <Pressable key={x} onPress={() => { setR(x); onRate(x); }} style={{ paddingHorizontal: 9, paddingVertical: 4, borderRadius: 999, backgroundColor: r === x ? C.text : C.card2 }}>
            <Text style={{ color: r === x ? "#FFF" : C.text, fontSize: 12 }}>{x.toFixed(1)}×</Text>
          </Pressable>
        ))}
      </View>
      <Text style={{ color: C.faint, fontSize: 11 }}>Voice: {voiceName}</Text>
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
