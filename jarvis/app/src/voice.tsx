// Voice session: talk to Ananta, hear the answer, and watch the "stage" show the charts and cards it talks about.
import { useEffect, useRef, useState } from "react";
import { ActivityIndicator, Animated, Pressable, ScrollView, Switch, Text, View } from "react-native";
import * as Speech from "expo-speech";
import {
  AudioQuality, IOSOutputFormat, RecordingPresets, requestRecordingPermissionsAsync, setAudioModeAsync,
  useAudioRecorder, useAudioRecorderState,
} from "expo-audio";
import { api } from "./api";
import { CandleChart } from "./charts";
import { useScreen } from "./context";
import { useData } from "./useData";
import { Bullet, Divider, Pill, Segmented, T, pct, price, usd, usdSigned } from "./ui";
import { C, pnlColor } from "./theme";

const WAV = {
  ...RecordingPresets.HIGH_QUALITY,
  extension: ".wav",
  sampleRate: 16000,
  numberOfChannels: 1,
  bitRate: 256000,
  isMeteringEnabled: true,
  ios: { extension: ".wav", outputFormat: IOSOutputFormat.LINEARPCM, audioQuality: AudioQuality.HIGH, sampleRate: 16000,
    linearPCMBitDepth: 16, linearPCMIsBigEndian: false, linearPCMIsFloat: false },
  android: { ...RecordingPresets.HIGH_QUALITY.android, sampleRate: 16000, numberOfChannels: 1 },
} as any;

const VERB: Record<string, string> = {
  overview: "Checked what Ananta is doing", market: "Read the market", setups: "Checked setup conditions", strategy: "Looked at a strategy",
  trades: "Pulled the trades", trade: "Opened a trade", portfolio: "Checked the portfolio", history: "Looked up history",
  evidence: "Checked the evidence", knowledge: "Searched research notes", changes: "Read recent activity", report: "Read the report",
  mandate: "Read your mandate", propose_mandate_change: "Prepared a mandate change", alerts: "Checked your alerts",
  propose_alert: "Prepared an alert", manual_book: "Checked your paper book", propose_paper_order: "Prepared a paper order",
  start_research: "Started a research job",
};

type Turn = { heard: string; r: any };

async function toBase64(uri: string): Promise<string> {
  const blob = await (await fetch(uri)).blob();
  return await new Promise((res, rej) => {
    const fr = new FileReader();
    fr.onerror = () => rej(new Error("could not read the recording"));
    fr.onloadend = () => res(String(fr.result).split(",")[1] ?? "");
    fr.readAsDataURL(blob);
  });
}

export default function Voice({ ActionCard, openScreen, suggestions = [] }: { ActionCard: any; openScreen: (sh: any) => void; suggestions?: string[] }) {
  const rec = useAudioRecorder(WAV);
  const st = useAudioRecorderState(rec, 150);
  const [status, setStatusS] = useState<"off" | "listening" | "thinking" | "speaking">("off");
  const [on, setOnS] = useState(false);
  const [claude, setClaude] = useState(false);
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thread, setThread] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);
  const [ctx] = useScreen();
  const statusRef = useRef("off"), onRef = useRef(false), threadRef = useRef<string | null>(null), claudeRef = useRef(false);
  const loudAt = useRef(0), startedAt = useRef(0), lastSpeech = useRef(0), heardVoice = useRef(false), busy = useRef(false);
  const pulse = useRef(new Animated.Value(1)).current;
  const setStatus = (x: any) => { statusRef.current = x; setStatusS(x); };
  threadRef.current = thread;
  claudeRef.current = claude;

  useEffect(() => {
    if (status !== "listening") { pulse.setValue(1); return; }
    const a = Animated.loop(Animated.sequence([Animated.timing(pulse, { toValue: 1.12, duration: 600, useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: 600, useNativeDriver: true })]));
    a.start();
    return () => a.stop();
  }, [status]);

  // While the voice bot is on: send after ~1.6 s of quiet once you have spoken; restart quietly when nothing is said;
  // switch itself off after 5 minutes without speech (so it never runs up costs or battery unnoticed).
  useEffect(() => {
    if (statusRef.current !== "listening" || busy.current) return;
    const m = st.metering ?? -160;
    const now = Date.now();
    if (m > -38) { loudAt.current = now; heardVoice.current = true; lastSpeech.current = now; }
    if (heardVoice.current && now - loudAt.current > 1600) { send(); return; }
    if (!heardVoice.current && now - startedAt.current > 12000) { restartQuietly(); return; }
    if (now - lastSpeech.current > 5 * 60 * 1000) { turnOff("Voice turned itself off after 5 quiet minutes."); }
  }, [st.metering, st.durationMillis]);

  useEffect(() => () => { onRef.current = false; Speech.stop(); try { rec.stop(); } catch { /* */ } }, []);

  const listen = async () => {
    if (!onRef.current) return;
    try {
      await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
      await rec.prepareToRecordAsync();
      rec.record();
      startedAt.current = Date.now();
      loudAt.current = Date.now();
      heardVoice.current = false;
      setStatus("listening");
    } catch (e: any) {
      turnOff(`Could not start the microphone: ${e?.message ?? e}`);
    }
  };

  const restartQuietly = async () => {
    busy.current = true;
    try { await rec.stop(); } catch { /* */ }
    busy.current = false;
    listen();
  };

  const turnOn = async () => {
    setErr(null);
    const p = await requestRecordingPermissionsAsync();
    if (!p.granted) { setErr("Microphone permission is off. Allow it for Expo Go in iPhone Settings."); return; }
    onRef.current = true;
    setOnS(true);
    lastSpeech.current = Date.now();
    listen();
  };

  const turnOff = async (why?: string) => {
    onRef.current = false;
    setOnS(false);
    Speech.stop();
    if (statusRef.current === "listening") { try { await rec.stop(); } catch { /* */ } }
    try { await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true }); } catch { /* */ }
    setStatus("off");
    if (why) setErr(why);
  };

  const speakThen = (text: string) => {
    if (!onRef.current) { setStatus("off"); return; }
    setStatus("speaking");
    Speech.speak(text, {
      rate: 1.0,
      onDone: () => { if (onRef.current) setTimeout(listen, 300); else setStatus("off"); },
      onStopped: () => { if (onRef.current) setTimeout(listen, 300); else setStatus("off"); },
      onError: () => { if (onRef.current) listen(); },
    });
  };

  const handle = (r: any) => {
    if (r.thread) setThread(r.thread);
    setTurns((t) => [{ heard: r.heard ?? r._q ?? "", r }, ...t]);
    const say = r.error ? r.error : r.answer;
    if (say && onRef.current) speakThen(say);
    else if (onRef.current) listen();
    else setStatus("off");
  };

  const send = async () => {
    if (busy.current) return;
    busy.current = true;
    setStatus("thinking");
    try {
      await rec.stop();
      const uri = rec.uri;
      if (!uri) throw new Error("no recording");
      const b64 = await toBase64(uri);
      const r = await api("/v3/voice/turn", { audio_b64: b64, mime: "audio/wav", thread: threadRef.current,
        mode: claudeRef.current ? "deep" : "everyday", context: ctx ?? undefined });
      lastSpeech.current = Date.now();
      handle(r);
    } catch (e: any) {
      setErr(e?.message ?? String(e));
      if (onRef.current) listen(); else setStatus("off");
    } finally {
      busy.current = false;
    }
  };

  // Tap a predefined question: asked as text, answered aloud (if the bot is on) and on screen.
  const askText = async (q: string) => {
    if (busy.current) return;
    busy.current = true;
    Speech.stop();
    if (statusRef.current === "listening") { try { await rec.stop(); } catch { /* */ } }
    setStatus("thinking");
    try {
      const r = await api("/v3/ask", { text: q, thread: threadRef.current, mode: claudeRef.current ? "deep" : "everyday", context: ctx ?? undefined });
      handle({ ...r, _q: q });
    } catch (e: any) {
      setErr(e?.message ?? String(e));
      if (onRef.current) listen(); else setStatus("off");
    } finally {
      busy.current = false;
    }
  };

  const onMic = () => {
    if (!on) turnOn();
    else if (status === "speaking") Speech.stop();          // interrupt: goes straight back to listening
    else if (status === "listening" && heardVoice.current) send();
  };

  const cur = turns[0]?.r;
  const label = { off: "Voice is off", listening: "Listening… just talk, pause when done", thinking: "Ananta is looking…",
    speaking: "Speaking… tap the circle to interrupt" }[status];
  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 40 }}>
      <View style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 14, paddingHorizontal: 14 }}>
        <SwitchRow label="Voice bot" sub={on ? "On: keeps listening and answering until you turn it off" : "Off: not listening"}
          value={on} onChange={(v) => (v ? turnOn() : turnOff())} />
        <Divider />
        <SwitchRow label={claude ? "Claude" : "Gemini"} sub={claude ? "Claude Sonnet · about 3-5¢ an answer, faster and deeper" : "Gemini Flash · free, can be slow when busy"}
          value={claude} onChange={setClaude} />
      </View>
      <View style={{ alignItems: "center", gap: 10, paddingVertical: 8 }}>
        <Pressable onPress={onMic} disabled={status === "thinking"}>
          <Animated.View style={{ transform: [{ scale: pulse }], width: 112, height: 112, borderRadius: 56, alignItems: "center", justifyContent: "center",
            backgroundColor: status === "listening" ? C.bad : status === "speaking" ? C.good : status === "off" ? C.faint : C.accent }}>
            {status === "thinking" ? <ActivityIndicator color="#FFF" size="large" /> : <MicGlyph />}
          </Animated.View>
        </Pressable>
        <Text style={{ color: C.text, fontWeight: "600" }}>{label}</Text>
        {status === "listening" ? <Level db={st.metering ?? -160} /> : null}
        {ctx ? <T small>Context: {ctx.label}</T> : null}
        {err ? <Text style={{ color: C.bad, textAlign: "center" }}>{err}</Text> : null}
      </View>
      {suggestions.length ? (
        <ScrollView horizontal showsHorizontalScrollIndicator={false} contentContainerStyle={{ gap: 8 }}>
          {suggestions.map((q) => (
            <Pressable key={q} onPress={() => askText(q)} style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 8 }}>
              <Text style={{ color: C.text, fontSize: 13 }}>{q}</Text>
            </Pressable>
          ))}
        </ScrollView>
      ) : null}

      {cur ? (
        <View style={{ gap: 12 }}>
          <View style={{ backgroundColor: C.card2, borderRadius: 12, padding: 12 }}>
            <Text style={{ color: C.dim, fontSize: 12 }}>You said</Text>
            <Text style={{ color: C.text, fontSize: 15 }}>{turns[0].heard || "…"}</Text>
          </View>
          <View style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 14, padding: 14, gap: 10 }}>
            <View style={{ flexDirection: "row", gap: 6 }}>
              {cur.stage ? <Pill text={String(cur.stage).toUpperCase()} color={C.accent} bg={C.accentSoft} /> : null}
              {cur.model_label ? <Pill text={`${cur.model_label} · ${cur.cost_usd ? `${(cur.cost_usd * 100).toFixed(1)}¢` : "free"}`} /> : null}
            </View>
            <Text style={{ color: cur.error ? C.bad : C.text, fontSize: 16, lineHeight: 23 }}>{cur.error ?? cur.answer}</Text>
            {(cur.actions ?? []).map((a: any) => <ActionCard key={a.id} a={a} />)}
          </View>

          {(cur.show ?? []).length ? <Text style={{ color: C.dim, fontSize: 12, fontWeight: "700", letterSpacing: 0.8 }}>ON STAGE</Text> : null}
          {(cur.show ?? []).map((sh: any, i: number) => <StageCard key={`${turns.length}-${i}`} sh={sh} open={() => openScreen(sh)} />)}

          {cur.breakdown?.length ? (
            <View style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 14, padding: 14, gap: 6 }}>
              <Text style={{ color: C.dim, fontSize: 12, fontWeight: "700", letterSpacing: 0.8 }}>BREAKDOWN</Text>
              {cur.breakdown.map((b: string, i: number) => <Bullet key={i}>{b}</Bullet>)}
            </View>
          ) : null}
          {cur.lookups?.length ? (
            <View style={{ gap: 4 }}>
              <Text style={{ color: C.dim, fontSize: 12, fontWeight: "700", letterSpacing: 0.8 }}>WHAT ANANTA DID</Text>
              {cur.lookups.map((l: string, i: number) => <Text key={i} style={{ color: C.dim, fontSize: 13 }}>✓ {VERB[l] ?? l}</Text>)}
            </View>
          ) : null}
        </View>
      ) : (
        <View style={{ gap: 6 }}>
          <T dim>Turn the voice bot on and just talk, or tap a question above.</T>
          <T small>Your voice is sent once to Google Gemini (free) to turn it into text; the recording is not kept.</T>
        </View>
      )}

      {turns.length > 1 ? (
        <View style={{ gap: 6 }}>
          <Text style={{ color: C.dim, fontSize: 12, fontWeight: "700", letterSpacing: 0.8 }}>EARLIER IN THIS SESSION</Text>
          {turns.slice(1).map((t, i) => (
            <View key={i}>
              {i ? <Divider /> : null}
              <Text style={{ color: C.dim, fontSize: 13, paddingTop: 6 }}>“{t.heard}”</Text>
              <Text style={{ color: C.text, fontSize: 14, paddingBottom: 6 }}>{t.r.error ?? t.r.answer}</Text>
            </View>
          ))}
          <Text onPress={() => { turnOff(); setTurns([]); setThread(null); }} style={{ color: C.accent, fontWeight: "600", paddingTop: 6 }}>End session</Text>
        </View>
      ) : null}
    </ScrollView>
  );
}

function StageCard({ sh, open }: { sh: any; open: () => void }) {
  return (
    <Pressable onPress={open} style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: 14, padding: 14, gap: 8 }}>
      <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
        <Text style={{ color: C.text, fontWeight: "700" }}>{sh.label}</Text>
        <Text style={{ color: C.accent, fontWeight: "600" }}>Open ›</Text>
      </View>
      {sh.screen === "coin" ? <CoinStage coin={sh.coin} /> : null}
      {sh.screen === "trade" ? <TradeStage id={sh.id} /> : null}
      {sh.screen === "portfolio" ? <PortfolioStage /> : null}
      {sh.screen === "markets" ? <MarketsStage /> : null}
    </Pressable>
  );
}

function CoinStage({ coin }: { coin: string }) {
  const { data: ch } = useData(`/v3/chart/${coin}?tf=1h`, 0);
  const { data: w } = useData(`/v3/coin/${coin}/watch`, 0);
  if (!ch) return <ActivityIndicator color={C.dim} />;
  const refs: any[] = (ch.levels ?? []).map((l: any) => ({ value: l.price, color: l.kind === "support" ? "#5B7083" : "#8A6D3B", label: l.kind === "support" ? "Support" : "Resist." }));
  (ch.open_trades ?? []).forEach((t: any) => { if (t.stop) refs.push({ value: t.stop, color: C.bad, label: "Stop" }); });
  const best = w?.setups ? [...w.setups].sort((a: any, b: any) => b.met / b.of - a.met / a.of)[0] : null;
  return (
    <View style={{ gap: 6 }}>
      <Text style={{ color: C.text, fontSize: 20, fontWeight: "700" }}>{price(ch.price)}</Text>
      <CandleChart candles={ch.candles.slice(-60)} height={150} refs={refs} marks={ch.marks} />
      {best ? <T small>Closest setup: {best.name} {best.met}/{best.of}{best.missing?.[0] ? ` · missing: ${best.missing[0]}` : ""}</T> : null}
    </View>
  );
}

function TradeStage({ id }: { id: string }) {
  const { data: d } = useData(`/v3/trade/${id}`, 0);
  if (!d) return <ActivityIndicator color={C.dim} />;
  return (
    <View style={{ gap: 4 }}>
      <Text style={{ color: pnlColor(d.pnl_usd), fontSize: 20, fontWeight: "700" }}>{usdSigned(d.pnl_usd)} <Text style={{ color: C.dim, fontSize: 13 }}>on $100</Text></Text>
      <T small>{d.setup_name} · bought {price(d.entry)} · now {price(d.price)}{d.stop ? ` · stop ${price(d.stop)}` : ""}</T>
    </View>
  );
}

function PortfolioStage() {
  const { data: d } = useData("/v3/holdings", 0);
  if (!d) return <ActivityIndicator color={C.dim} />;
  return (
    <View style={{ gap: 4 }}>
      <Text style={{ color: C.text, fontSize: 20, fontWeight: "700" }}>{usd(d.value)} <Text style={{ color: pnlColor(d.return_pct), fontSize: 14 }}>{pct(d.return_pct)}</Text></Text>
      {d.holdings.slice(0, 5).map((h: any) => <T key={h.coin} small>{h.coin} {usd(h.value)} · {pct(h.pnl_pct)}</T>)}
    </View>
  );
}

function MarketsStage() {
  const { data: d } = useData("/v3/markets", 0);
  if (!d) return <ActivityIndicator color={C.dim} />;
  return (
    <View style={{ gap: 3 }}>
      <T small>{d.summary}</T>
      {d.coins.map((c: any) => <T key={c.coin} small>{c.coin} {price(c.price)} · {pct(c.day_pct)} · 1h {c.trend_1h ?? "–"}</T>)}
    </View>
  );
}

const SwitchRow = ({ label, sub, value, onChange }: { label: string; sub: string; value: boolean; onChange: (v: boolean) => void }) => (
  <View style={{ flexDirection: "row", alignItems: "center", gap: 12, paddingVertical: 10 }}>
    <View style={{ flex: 1 }}>
      <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>{label}</Text>
      <Text style={{ color: C.dim, fontSize: 12 }}>{sub}</Text>
    </View>
    <Switch value={value} onValueChange={onChange} trackColor={{ true: C.accent, false: C.line }} />
  </View>
);

const Toggle = ({ label, on, set }: { label: string; on: boolean; set: (v: boolean) => void }) => (
  <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
    <Switch value={on} onValueChange={set} trackColor={{ true: C.accent, false: C.line }} style={{ transform: [{ scale: 0.8 }] }} />
    <Text style={{ color: C.dim, fontSize: 13 }}>{label}</Text>
  </View>
);

function Level({ db }: { db: number }) {
  const f = Math.max(0, Math.min(1, (db + 60) / 60));
  return (
    <View style={{ width: 160, height: 6, backgroundColor: C.card2, borderRadius: 3 }}>
      <View style={{ width: `${f * 100}%`, height: 6, backgroundColor: C.bad, borderRadius: 3 }} />
    </View>
  );
}

function MicGlyph() {
  return (
    <View style={{ alignItems: "center" }}>
      <View style={{ width: 26, height: 40, borderRadius: 13, borderWidth: 3, borderColor: "#FFF" }} />
      <View style={{ width: 40, height: 16, borderBottomLeftRadius: 20, borderBottomRightRadius: 20, borderWidth: 3, borderTopWidth: 0, borderColor: "#FFF", marginTop: -10 }} />
      <View style={{ width: 3, height: 8, backgroundColor: "#FFF" }} />
    </View>
  );
}
