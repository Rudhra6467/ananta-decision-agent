import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, KeyboardAvoidingView, Platform, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { router, useLocalSearchParams } from "expo-router";
import { useScreen } from "../../src/context";
import { confirmWithFaceId } from "../../src/guard";
import { api } from "../../src/api";
import { Bullet, Divider, Pill, Segmented, T } from "../../src/ui";
import { C } from "../../src/theme";

type Msg = { id?: string; role: "user" | "assistant"; text?: string; [k: string]: any };
const MODES = [{ key: "auto", label: "Auto" }, { key: "everyday", label: "Everyday" }, { key: "deep", label: "Deep" }, { key: "max", label: "Max" }];
const MODE_HINT: Record<string, string> = {
  auto: "Auto: free Gemini for everyday questions, Claude Sonnet when it needs investigating.",
  everyday: "Everyday: Gemini Flash, free.", deep: "Deep: Claude Sonnet, about 3-5¢ a question.", max: "Max: Claude Opus, for big research questions (about 10¢+).",
};
const STARTERS = ["How is the market right now?", "What setups are close to triggering?", "How are my trades doing?",
  "What has Hunter been doing today?", "What changed since yesterday?", "What did we learn from the repair shop?"];
const STAGE: Record<string, string> = { observation: "Observation", candidate: "Candidate setup", "candidate setup": "Candidate setup", setup: "Setup",
  decision: "Decision", execution: "Executed", position: "Open position", outcome: "Outcome", evaluation: "Evaluation", learning: "Learning" };

export default function Ask() {
  const params = useLocalSearchParams<{ q?: string; t?: string }>();
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [thread, setThread] = useState<string | null>(null);
  const [text, setText] = useState("");
  const [busy, setBusy] = useState(false);
  const [mode, setMode] = useState("auto");
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
      const r = await api("/v3/ask", { text: q, thread, mode, context: ctx ?? undefined });
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
        <View style={{ flex: 1 }}>
          <Segmented value={mode} onChange={setMode} options={MODES} />
        </View>
        <Text onPress={reset} style={{ color: C.accent, fontWeight: "600" }}>New chat</Text>
      </View>
      <Text style={{ color: C.faint, fontSize: 11, paddingHorizontal: 18, paddingTop: 4 }}>{MODE_HINT[mode]}</Text>
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
            {STARTERS.map((q) => (
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

export function openScreen(sh: any) {
  const to: Record<string, string> = { markets: "/(tabs)/markets", portfolio: "/(tabs)/portfolio", evidence: "/(tabs)/evidence",
    cockpit: "/(tabs)/cockpit", mandate: "/mandate", home: "/(tabs)/today" };
  if (sh.screen === "coin" && sh.coin) router.push(`/coin/${sh.coin}`);
  else if (sh.screen === "trade" && sh.id) router.push(`/trade/${sh.id}`);
  else if (to[sh.screen]) router.push(to[sh.screen] as any);
}

function ActionCard({ a }: { a: any }) {
  const [status, setStatus] = useState<string>(a.status ?? "PENDING");
  const [err, setErr] = useState<string | null>(null);
  const decide = async (confirm: boolean) => {
    if (confirm && !(await confirmWithFaceId("Confirm", a.summary))) return;
    try {
      const r = await api(`/v3/actions/${a.id}`, { confirm });
      setStatus(r.status);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
    }
  };
  return (
    <View style={{ borderWidth: 1, borderColor: C.accent, borderRadius: 12, padding: 12, gap: 8, backgroundColor: C.accentSoft }}>
      <Text style={{ color: C.accent, fontSize: 11, fontWeight: "700", letterSpacing: 0.6 }}>NEEDS YOUR OK</Text>
      <Text style={{ color: C.text, fontSize: 14 }}>{a.summary}</Text>
      {status === "PENDING" ? (
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Pressable onPress={() => decide(false)} style={{ flex: 1, borderWidth: 1, borderColor: C.line, backgroundColor: C.card, borderRadius: 8, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.text, fontWeight: "600" }}>Cancel</Text>
          </Pressable>
          <Pressable onPress={() => decide(true)} style={{ flex: 1, backgroundColor: C.accent, borderRadius: 8, padding: 9, alignItems: "center" }}>
            <Text style={{ color: "#FFF", fontWeight: "700" }}>Confirm</Text>
          </Pressable>
        </View>
      ) : <Text style={{ color: status === "DONE" ? C.good : C.dim, fontWeight: "600" }}>{status === "DONE" ? "✓ Done" : "Cancelled"}</Text>}
      {err ? <Text style={{ color: C.bad, fontSize: 12 }}>{err}</Text> : null}
    </View>
  );
}
