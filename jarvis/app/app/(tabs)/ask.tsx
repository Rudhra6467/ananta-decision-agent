import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Switch, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useScreen } from "../../src/context";
import Voice from "../../src/voice";
import { ActionCard, openScreen } from "../../src/actions";
import { useData } from "../../src/useData";
import { confirmWithFaceId } from "../../src/guard";
import { api } from "../../src/api";
import { Bullet, Divider, Pill, Segmented, T } from "../../src/ui";
import { C } from "../../src/theme";

type Msg = { id?: string; role: "user" | "assistant"; text?: string; [k: string]: any };
const STARTERS = ["How is the market right now?", "What setups are close to triggering?", "How are my trades doing?",
  "What has Hunter been doing today?", "What changed since yesterday?", "What did we learn from the repair shop?"];
const STAGE: Record<string, string> = { observation: "Observation", candidate: "Candidate setup", "candidate setup": "Candidate setup", setup: "Setup",
  decision: "Decision", execution: "Executed", position: "Open position", outcome: "Outcome", evaluation: "Evaluation", learning: "Learning" };

function Chat({ suggestions }: { suggestions: string[] }) {
  const params = useLocalSearchParams<{ q?: string; t?: string }>();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [thread, setThread] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [claude, setClaude] = useState(false);
  const [ctx, setCtx] = useScreen();
  const scroll = useRef<ScrollView>(null);
  const lastParam = useRef<string | undefined>(undefined);

  const send = async (q: string) => {
    q = q.trim();
    if (!q || busy) return;
    setText("");
    setMsgs((m) => [...m, { role: "user", text: q }]);
    setBusy(true);
    try {
      const r = await api("/v3/ask", { text: q, thread, mode: claude ? "deep" : "everyday", context: ctx ?? undefined });
      setThread(r.thread);
      setMsgs((m) => [...m, { role: "assistant", ...r }]);
    } catch (e: any) {
      setMsgs((m) => [...m, { role: "assistant", error: e?.message ?? String(e) }]);
    } finally {
      setBusy(false);
    }
  };
  useEffect(() => {
    if (params.q && params.t !== lastParam.current) {
      lastParam.current = params.t;
      send(String(params.q));
    }
  }, [params.q, params.t]);
  useEffect(() => { setTimeout(() => scroll.current?.scrollToEnd({ animated: true }), 80); }, [msgs.length, busy]);

  const rate = async (m: Msg, v: number) => {
    if (!m.id) return;
    await api("/v3/ask/rate", { id: m.id, rating: v });
    setMsgs((all) => all.map((x) => (x.id === m.id ? { ...x, rating: v } : x)));
  };
  const reset = () => { setMsgs([]); setThread(null); };
  const second = async (m: Msg) => {
    if (!m.id || busy) return;
    setBusy(true);
    try {
      const r = await api("/v3/ask/second", { id: m.id });
      setMsgs((all) => [...all, { role: "assistant", ...r }]);
    } catch (e: any) {
      setMsgs((all) => [...all, { role: "assistant", error: e?.message ?? String(e) }]);
    } finally {
      setBusy(false);
    }
  };

  return (
    <KeyboardAvoidingView style={{ flex: 1, backgroundColor: C.bg }} behavior={Platform.OS === "ios" ? "padding" : undefined} keyboardVerticalOffset={90}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 10, paddingHorizontal: 16, paddingTop: 8 }}>
        <Text style={{ color: claude ? C.faint : C.text, fontWeight: "700" }}>Gemini</Text>
        <Switch value={claude} onValueChange={setClaude} trackColor={{ true: C.accent, false: C.line }} />
        <Text style={{ color: claude ? C.text : C.faint, fontWeight: "700" }}>Claude</Text>
        <Text style={{ color: C.faint, fontSize: 11, flex: 1 }}>{claude ? "~3-5¢ an answer" : "free"}</Text>
        <Text onPress={reset} style={{ color: C.accent, fontWeight: "600" }}>New chat</Text>
      </View>
      <View style={{ flexDirection: "row", gap: 8, paddingHorizontal: 16, paddingTop: 6, alignItems: "center" }}>
        {ctx && ctx.screen !== "ask" ? (
          <Pressable onPress={() => setCtx(null)} style={{ flexDirection: "row", gap: 6, alignItems: "center", backgroundColor: C.accentSoft, borderRadius: 999, paddingHorizontal: 10, paddingVertical: 5, flexShrink: 1 }}>
            <Text style={{ color: C.accent, fontSize: 12 }} numberOfLines={1}>About: {ctx.label}</Text>
            <Text style={{ color: C.accent, fontSize: 12, fontWeight: "700" }}>✕</Text>
          </Pressable>
        ) : <Text style={{ color: C.faint, fontSize: 12, flex: 1 }}>Tip: long-press anything in the app to ask about it.</Text>}
        <View style={{ flex: ctx ? 1 : 0 }} />
        <Text onPress={() => router.push("/mandate")} style={{ color: C.accent, fontSize: 12, fontWeight: "600" }}>Your mandate</Text>
      </View>
      <ScrollView ref={scroll} contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 24 }} keyboardShouldPersistTaps="handled">
        {msgs.length === 0 ? (
          <View style={{ gap: 10 }}>
            <Text style={{ color: C.text, fontSize: 22, fontWeight: "700" }}>Ask Ananta</Text>
            <T dim>Ask about the market, setups, trades, the portfolio or what the repair shop learned. Answers come only from Ananta's own data, and say when the evidence is thin.</T>
            {(suggestions.length ? suggestions : STARTERS).map((q) => (
              <Pressable key={q} onPress={() => send(q)} style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 12, padding: 13 }}>
                <Text style={{ color: C.text, fontSize: 15 }}>{q}</Text>
              </Pressable>
            ))}
          </View>
        ) : null}
        {msgs.map((m, i) => (m.role === "user" ? <UserBubble key={i} text={m.text!} /> : <Answer key={i} m={m} onPick={send} onRate={(v) => rate(m, v)} onSecond={() => second(m)} />))}
        {busy ? (
          <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
            <ActivityIndicator color={C.dim} />
            <T dim>Ananta is looking through the data…</T>
          </View>
        ) : null}
      </ScrollView>
      {msgs.length ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={{ flexGrow: 0 }} contentContainerStyle={{ gap: 8, paddingHorizontal: 12, paddingBottom: 8 }}>
          {(suggestions.length ? suggestions : STARTERS).map((q) => (
            <Pressable key={q} onPress={() => send(q)} style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 7 }}>
              <Text style={{ color: C.text, fontSize: 13 }}>{q}</Text>
            </Pressable>
          ))}
        </ScrollView>
      ) : null}
      <View style={{ flexDirection: "row", alignItems: "flex-end", gap: 8, padding: 12, borderTopWidth: 1, borderTopColor: C.line, backgroundColor: C.card }}>
        <TextInput value={text} onChangeText={setText} placeholder="Ask about trades or markets…" placeholderTextColor={C.faint} multiline
          style={{ flex: 1, maxHeight: 110, fontSize: 15, color: C.text, backgroundColor: C.bg, borderRadius: 18, paddingHorizontal: 14, paddingTop: 10, paddingBottom: 10 }} />
        <Pressable onPress={() => send(text)} disabled={busy || !text.trim()}
          style={{ backgroundColor: busy || !text.trim() ? C.line : C.accent, borderRadius: 18, paddingHorizontal: 16, paddingVertical: 10 }}>
          <Text style={{ color: "#FFF", fontWeight: "700" }}>Send</Text>
        </Pressable>
      </View>
    </KeyboardAvoidingView>
  );
}

const UserBubble = ({ text }: { text: string }) => (
  <View style={{ alignSelf: "flex-end", maxWidth: "85%", backgroundColor: C.accent, borderRadius: 16, borderBottomRightRadius: 4, paddingHorizontal: 14, paddingVertical: 10 }}>
    <Text style={{ color: "#FFF", fontSize: 15, lineHeight: 21 }}>{text}</Text>
  </View>
);

function Answer({ m, onPick, onRate, onSecond }: { m: Msg; onPick: (q: string) => void; onRate: (v: number) => void; onSecond: () => void }) {
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
          {m.model_label ?? (m.provider === "gemini" ? "Gemini" : "Claude")} · {m.cost_usd ? `${(m.cost_usd * 100).toFixed(1)}¢` : "free"}{m.ms ? ` · ${(m.ms / 1000).toFixed(0)}s` : ""}{m.lookups?.length ? ` · ${m.lookups.length} lookups` : ""}
        </Text>
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

export default function Ananta() {
  const [tab, setTab] = useState("chat");
  const params = useLocalSearchParams<{ q?: string; t?: string }>();
  useEffect(() => { if (params.q) setTab("chat"); }, [params.t]);
  const { data: sg } = useData("/v3/ask/suggestions", 0);
  const suggestions: string[] = sg?.questions ?? [];
  return (
    <View style={{ flex: 1, backgroundColor: C.bg }}>
      <View style={{ paddingHorizontal: 16, paddingTop: 8 }}>
        <Segmented value={tab} onChange={setTab} options={[{ key: "chat", label: "Chat" }, { key: "voice", label: "Voice" }, { key: "history", label: "History" }]} />
      </View>
      <View style={{ flex: 1, display: tab === "chat" ? "flex" : "none" }}><Chat suggestions={suggestions} /></View>
      {tab === "voice" ? <Voice ActionCard={ActionCard} openScreen={openScreen} suggestions={suggestions} /> : null}
      {tab === "history" ? <History /> : null}
    </View>
  );
}

function History() {
  const { data: d } = useData("/v3/ask/threads");
  const [open, setOpen] = useState<string | null>(null);
  const { data: t } = useData(open ? `/v3/ask/thread/${open}` : null, 0);
  if (open && t) {
    return (
      <ScrollView contentContainerStyle={{ padding: 16, gap: 12 }}>
        <Text onPress={() => setOpen(null)} style={{ color: C.accent, fontWeight: "600" }}>‹ All conversations</Text>
        {t.messages.map((m: any, i: number) => (m.role === "user" ? <UserBubble key={i} text={m.text} /> :
          <Answer key={i} m={m} onPick={() => {}} onRate={async (v) => { await api("/v3/ask/rate", { id: m.id, rating: v }); }} onSecond={() => {}} />))}
      </ScrollView>
    );
  }
  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 10 }}>
      {(d?.threads ?? []).length === 0 ? <T dim>No conversations yet.</T> : null}
      {(d?.threads ?? []).map((th: any) => (
        <Pressable key={th.thread} onPress={() => setOpen(th.thread)} style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 12, padding: 12, gap: 2 }}>
          <Text style={{ color: C.text, fontSize: 15 }} numberOfLines={2}>{th.voice ? "🎙 " : ""}{th.title}</Text>
          <Text style={{ color: C.faint, fontSize: 12 }}>{th.time} · {Math.ceil(th.messages / 2)} question(s)</Text>
        </Pressable>
      ))}
    </ScrollView>
  );
}
