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

export default function Voice({ ActionCard, openScreen }: { ActionCard: any; openScreen: (sh: any) => void }) {
  const rec = useAudioRecorder(WAV);
  const st = useAudioRecorderState(rec, 150);
  const [status, setStatus] = useState<"idle" | "listening" | "thinking" | "speaking">("idle");
  const [turns, setTurns] = useState<Turn[]>([]);
  const [thread, setThread] = useState<string | null>(null);
  const [mode, setMode] = useState("auto");
  const [handsFree, setHandsFree] = useState(false);
  const [speak, setSpeak] = useState(true);
  const [err, setErr] = useState<string | null>(null);
  const [ctx] = useScreen();
  const loudAt = useRef(0), startedAt = useRef(0), heardVoice = useRef(false), stopping = useRef(false);
  const pulse = useRef(new Animated.Value(1)).current;

  useEffect(() => {
    if (status !== "listening") { pulse.setValue(1); return; }
    const a = Animated.loop(Animated.sequence([Animated.timing(pulse, { toValue: 1.12, duration: 600, useNativeDriver: true }),
      Animated.timing(pulse, { toValue: 1, duration: 600, useNativeDriver: true })]));
    a.start();
    return () => a.stop();
  }, [status]);

  // hands-free: stop by itself after ~1.6 s of quiet once you have spoken
  useEffect(() => {
    if (status !== "listening" || !handsFree) return;
    const m = st.metering ?? -160;
    const now = Date.now();
    if (m > -38) { loudAt.current = now; heardVoice.current = true; }
    if (heardVoice.current && now - loudAt.current > 1600) stop();
    if (!heardVoice.current && now - startedAt.current > 8000) stop();
  }, [st.metering, st.durationMillis]);

  useEffect(() => () => { Speech.stop(); }, []);

  const start = async () => {
    setErr(null);
    Speech.stop();
    const p = await requestRecordingPermissionsAsync();
    if (!p.granted) { setErr("Microphone permission is off. Allow it for Expo Go in iPhone Settings."); return; }
    await setAudioModeAsync({ allowsRecording: true, playsInSilentMode: true });
    await rec.prepareToRecordAsync();
    rec.record();
    startedAt.current = Date.now();
    loudAt.current = Date.now();
    heardVoice.current = false;
    setStatus("listening");
  };

  const stop = async () => {
    if (status !== "listening" || stopping.current) return;
    stopping.current = true;
    setStatus("thinking");
    try {
      await rec.stop();
      await setAudioModeAsync({ allowsRecording: false, playsInSilentMode: true });
      const uri = rec.uri;
      if (!uri) throw new Error("no recording");
      const b64 = await toBase64(uri);
      const r = await api("/v3/voice/turn", { audio_b64: b64, mime: "audio/wav", thread, mode, context: ctx ?? undefined });
      if (r.thread) setThread(r.thread);
      setTurns((t) => [{ heard: r.heard, r }, ...t]);
      const say = r.error ? r.error : r.answer;
      if (speak && say) {
        setStatus("speaking");
        Speech.speak(say, {
          rate: 1.0,
          onDone: () => { setStatus("idle"); if (handsFree && !r.error) setTimeout(start, 350); },
          onStopped: () => setStatus("idle"),
          onError: () => setStatus("idle"),
        });
      } else {
        setStatus("idle");
      }
    } catch (e: any) {
      setErr(e?.message ?? String(e));
      setStatus("idle");
    } finally {
      stopping.current = false;
    }
  };

  const onMic = () => {
    if (status === "listening") stop();
    else if (status === "speaking") { Speech.stop(); setStatus("idle"); }
    else if (status === "idle") start();
  };

  const cur = turns[0]?.r;
  const label = { idle: handsFree ? "Tap to start talking" : "Tap to talk", listening: handsFree ? "Listening… (stops when you pause)" : "Listening… tap to send",
    thinking: "Ananta is looking…", speaking: "Speaking… tap to stop" }[status];
  return (
    <ScrollView contentContainerStyle={{ padding: 16, gap: 14, paddingBottom: 40 }}>
      <Segmented value={mode} onChange={setMode} options={[{ key: "auto", label: "Auto" }, { key: "everyday", label: "Everyday" }, { key: "deep", label: "Deep" }, { key: "max", label: "Max" }]} />
      <View style={{ alignItems: "center", gap: 10, paddingVertical: 8 }}>
        <Pressable onPress={onMic} disabled={status === "thinking"}>
          <Animated.View style={{ transform: [{ scale: pulse }], width: 112, height: 112, borderRadius: 56, alignItems: "center", justifyContent: "center",
            backgroundColor: status === "listening" ? C.bad : status === "speaking" ? C.good : C.accent }}>
            {status === "thinking" ? <ActivityIndicator color="#FFF" size="large" /> : <MicGlyph />}
          </Animated.View>
        </Pressable>
        <Text style={{ color: C.text, fontWeight: "600" }}>{label}</Text>
        {status === "listening" ? <Level db={st.metering ?? -160} /> : null}
        <View style={{ flexDirection: "row", gap: 18, alignItems: "center" }}>
          <Toggle label="Hands-free" on={handsFree} set={setHandsFree} />
          <Toggle label="Speak answers" on={speak} set={(v) => { setSpeak(v); if (!v) Speech.stop(); }} />
        </View>
        {ctx ? <T small>Context: {ctx.label}</T> : null}
        {err ? <Text style={{ color: C.bad, textAlign: "center" }}>{err}</Text> : null}
      </View>

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
          <T dim>Try: "How is the market?" · "What is Hunter doing?" · "Show me where ETH stands" · "How are my trades?"</T>
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
          <Text onPress={() => { setTurns([]); setThread(null); }} style={{ color: C.accent, fontWeight: "600", paddingTop: 6 }}>End session</Text>
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
