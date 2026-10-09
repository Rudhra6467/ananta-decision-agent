// Cockpit (plan 3.8, D11). Top to bottom:
//  · the title row (in the tabs header): the alerts bell and the sun/moon switch
//  · the 3 + 2 controls: Kill switch, Autopilot, Live on the left; Ask Ananta, Ananta Voice Assist on the right
//  · Evidence: the repair shop's reviews with human names, each with its own page
//  · Additional features: Systems and circuit breakers, Recent activities, Invites, Mandate
//  · Voice Assist Settings: the voice, the Claude budget and the Test lab
//  · Sign out
// A visitor's Cockpit controls only their own account: Pause Ananta for me, Auto mode, Live (coming soon), their voice.
import { Spot } from "../../src/spotlight";
import { setScreen } from "../../src/context";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import { Alert, Pressable, Switch, Text, View } from "react-native";
import { router } from "expo-router";
import { api, logout } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { Btn, Busy, Card, Divider, ErrorBox, Line, Screen, Section, Segmented, T } from "../../src/ui";
import { Progress } from "../../src/charts";
import { useData } from "../../src/useData";
import { C } from "../../src/theme";
import { ExplainSheet, showToast } from "../../src/blocks";
import { clearMe, loadMe, useMe } from "../../src/visitor";
import * as TTS from "../../src/tts";

export default function CockpitPage() {
  const me = useMe();
  if (!me) return <Busy />;
  return me.guest ? <VisitorCockpit /> : <Cockpit />;
}

// ---- one control tile of the 3 + 2 grid ----
function Tile({ label, help, on, onChange, danger, locked }: {
  label: string; help: string; on: boolean; onChange: (v: boolean) => void; danger?: boolean; locked?: boolean;
}) {
  return (
    <View style={{ backgroundColor: C.card, borderRadius: 14, borderWidth: 1, borderColor: on ? (danger ? C.bad : C.accent) : C.line, padding: 12, gap: 6, minHeight: 104 }}>
      <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 14, flex: 1 }} numberOfLines={2}>{label}{locked ? " 🔒" : ""}</Text>
        <Switch value={on} onValueChange={onChange} trackColor={{ true: danger ? C.bad : C.accent, false: C.line }} />
      </View>
      <Text style={{ color: on ? (danger ? C.bad : C.accent) : C.dim, fontSize: 12, fontWeight: "700" }}>{on ? "ON" : "OFF"}</Text>
      <Text style={{ color: C.dim, fontSize: 12, lineHeight: 16 }}>{help}</Text>
    </View>
  );
}

function Grid({ left, right }: { left: React.ReactNode[]; right: React.ReactNode[] }) {
  return (
    <View style={{ flexDirection: "row", gap: 10 }}>
      <View style={{ flex: 1, gap: 10 }}>{left}</View>
      <View style={{ flex: 1, gap: 10 }}>{right}</View>
    </View>
  );
}

// Live: never switches on from here until live trading is approved; the switch opens this sheet and stays off.
function LiveSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const Opt = ({ title, sub }: { title: string; sub: string }) => (
    <View style={{ borderWidth: 1, borderColor: C.line, borderRadius: 12, padding: 14, gap: 4, opacity: 0.85 }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 15, flex: 1 }}>{title}</Text>
        <View style={{ backgroundColor: C.card2, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3 }}>
          <Text style={{ color: C.dim, fontSize: 11, fontWeight: "800" }}>COMING SOON</Text>
        </View>
      </View>
      <Text style={{ color: C.dim, fontSize: 13 }}>{sub}</Text>
    </View>
  );
  return (
    <ExplainSheet open={open} onClose={onClose} title="Live trading">
      <T>Everything runs on paper money today. Live trading opens only after the paper results prove the setups, and only with your approval.</T>
      <Opt title="Add money" sub="Fund an account to trade with real money." />
      <Opt title="Connect your exchange with an API key" sub="Let Ananta place orders on your own exchange account." />
    </ExplainSheet>
  );
}

// the voice Ananta speaks with (saved on this device and to the account)
function VoicePick() {
  const [v, setV] = useState(TTS.voice);
  const [r, setR] = useState(String(TTS.rate));
  useEffect(() => { TTS.init().then(() => { setV(TTS.voice); setR(String(TTS.rate)); }); }, []);
  const LABEL: Record<string, string> = { Deep: "Deep · male", British: "British · male", Calm: "Calm · female", Friendly: "Friendly · female", Bright: "Bright · female" };
  return (
    <View style={{ gap: 8 }}>
      <T dim small>Voice</T>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {TTS.VOICES.map((x) => (
          <Pressable key={x} onPress={() => { setV(x); TTS.setVoice(x); api("/v3/me/setup", { voice: x }).catch(() => {}); TTS.speakText(`Hello. This is the ${x} voice.`); }}
            style={{ borderRadius: 999, paddingHorizontal: 11, paddingVertical: 6, borderWidth: 1, borderColor: v === x ? C.accent : C.line, backgroundColor: v === x ? C.accentSoft : C.card }}>
            <Text style={{ color: v === x ? C.accent : C.text, fontSize: 13, fontWeight: "600" }}>{LABEL[x] ?? x}</Text>
          </Pressable>
        ))}
      </View>
      <T dim small>Speed</T>
      <Segmented value={r} onChange={(k) => { setR(k); TTS.setRate(Number(k)); }} options={TTS.RATES.map((x) => ({ key: String(x), label: `${x}×` }))} />
    </View>
  );
}

// ---- a visitor's Cockpit: their own account only ----
function VisitorCockpit() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "cockpit", label: "Cockpit: your own controls, voice and account" }); }, []));
  const me = useMe();
  const [live, setLive] = useState(false);
  const p = me?.profile ?? {};
  const set = async (k: "paused" | "auto", v: boolean) => {
    try {
      await api("/v3/me/setup", { [k]: v });
      await loadMe();
      showToast(k === "paused" ? (v ? "Ananta is paused for you" : "Ananta is working for you again") : (v ? "Auto mode on ✓" : "Ananta asks you first ✓"));
    } catch (e: any) { showToast(e?.message ?? "Not changed"); }
  };
  return (
    <Screen loading={false} onRefresh={() => loadMe()}>
      <Spot id="cockpit.controls">
        <Grid
          left={[
            <Tile key="p" label="Pause Ananta for me" help="On = no watch acts for you; nothing new is bought." on={!!p.paused} danger onChange={(v) => set("paused", v)} />,
            <Tile key="l" label="Live" help="Real money: coming soon." on={false} locked onChange={() => setLive(true)} />,
          ]}
          right={[
            <Tile key="a" label="Auto mode" help="On = your watches take their paper trades and tell you. Off = Ananta asks first." on={!!p.auto} onChange={(v) => set("auto", v)} />,
          ]} />
      </Spot>
      <Card title={p.name ?? me?.name ?? "Your account"} sub="Practice account · paper money">
        {p.capital ? <Line label="Starting money" value={`$${Number(p.capital).toLocaleString()}`} /> : null}
        {p.coins?.length ? <Line label="Your coins" value={String(p.coins.length)} sub={p.coins.join(", ")} /> : null}
      </Card>
      <Section title="Voice Assist Settings" />
      <Card><VoicePick /></Card>
      <Btn label="Sign out" kind="secondary" onPress={async () => { await logout(); clearMe(); router.replace("/login"); }} />
      <LiveSheet open={live} onClose={() => setLive(false)} />
    </Screen>
  );
}

// ---- Madhav's Cockpit ----
const VERDICT: Record<string, [string, string]> = { PASS: ["Passed", "good"], FAIL: ["No change", "dim"], INSUFFICIENT: ["Not enough data", "warn"] };

function Cockpit() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "cockpit", label: "Cockpit: controls, evidence, additional features, voice settings" }); }, []));
  const { data: d, err, loading, reload } = useData("/v3/cockpit");
  const { data: sp, reload: reloadSpend } = useData("/v3/spend");
  const { data: ev } = useData("/v3/evidence/collected", 600000);
  const [live, setLive] = useState(false);
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  const sw = (k: string) => (d.switches ?? []).find((w: any) => w.key === k) ?? {};

  const flip = async (key: string, on: boolean) => {
    try {
      if (key === "kill_switch") {
        const ok = await confirmWithFaceId(on ? "Turn ON the kill switch?" : "Turn OFF the kill switch?",
          on ? "Every paper position closes at the next price and no new trades start." : "Trading (paper) may start again.");
        if (!ok) return;
        await api("/safety/kill", { on, confirm: true });
      } else if (key === "portfolio_auto") {
        if (on && !(await confirmWithFaceId("Turn on portfolio autopilot?", "The portfolio will rebalance (paper) by itself without asking you."))) return;
        await api("/portfolio/mode", { mode: on ? "AUTO" : "SUGGEST", confirm: true });
      }
    } catch (e: any) {
      Alert.alert("Not changed", e?.message ?? String(e));
    }
    reload();
  };
  const setting = async (key: string, value: string) => { await api("/v3/settings", { key, value }); reloadSpend(); };
  const reviews: any[] = [...(ev?.forwarded ?? [])].reverse();

  return (
    <Screen loading={loading} onRefresh={() => { reload(); reloadSpend(); }}>
      <Spot id="cockpit.controls">
        <Grid
          left={[
            <Tile key="k" label="Kill switch" help="On = close every paper position and block new trades." on={!!sw("kill_switch").on} danger onChange={(v) => flip("kill_switch", v)} />,
            <Tile key="a" label="Autopilot" help="On = the trend portfolio rebalances by itself." on={!!sw("portfolio_auto").on} onChange={(v) => flip("portfolio_auto", v)} />,
            <Tile key="l" label="Live" help="Real money: coming soon. Paper only." on={false} locked onChange={() => setLive(true)} />,
          ]}
          right={[
            <Spot id="cockpit.ai" key="ai">
              <View style={{ gap: 10 }}>
                <Tile label="Ask Ananta" help="Off = no AI answers at all (nothing can cost money)." on={sp?.settings?.ask_enabled === "1"}
                  onChange={(v) => setting("ask_enabled", v ? "1" : "0")} />
                <Tile label="Ananta Voice Assist" help="Off = Ananta never speaks or reaches out by itself." on={sp?.settings?.voice_enabled === "1"}
                  onChange={(v) => setting("voice_enabled", v ? "1" : "0")} />
              </View>
            </Spot>,
          ]} />
      </Spot>

      <Spot id="cockpit.evidence">
        <Section title="Evidence" right={<Text onPress={() => router.push("/evidence")} style={{ color: C.accent, fontWeight: "600" }}>All {reviews.length} ›</Text>} />
        <Card>
          {reviews.length === 0 ? <T dim>Loading the reviews…</T> : null}
          {reviews.slice(0, 5).map((r: any, i: number) => {
            const [word, tone] = VERDICT[r.verdict] ?? [r.verdict, "dim"];
            return (
              <View key={r.id}>
                {i ? <Divider /> : null}
                <Pressable onPress={() => router.push(`/evidence/${r.id}`)} style={({ pressed }) => ({ paddingVertical: 10, gap: 3, opacity: pressed ? 0.6 : 1 })}>
                  <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
                    <Text style={{ color: C.text, fontWeight: "600", fontSize: 15, flex: 1 }} numberOfLines={2}>{r.title}</Text>
                    <Text style={{ color: C.faint, fontSize: 18 }}>›</Text>
                  </View>
                  <Text style={{ color: (C as any)[tone], fontSize: 12, fontWeight: "700" }}>{word.toUpperCase()} <Text style={{ color: C.faint, fontWeight: "400" }}>· {r.date}</Text></Text>
                </Pressable>
              </View>
            );
          })}
          <Divider />
          <Text onPress={() => router.push("/lab")} style={{ color: C.accent, fontWeight: "600", paddingTop: 8 }}>The repair loop, live ›</Text>
        </Card>
      </Spot>

      <Card onPress={() => router.push("/more")} title="Additional features" sub="Systems and circuit breakers · Recent activities · Invites · Mandate"
        right={<Text style={{ color: C.faint, fontSize: 18 }}>›</Text>} />

      {sp ? (
        <Spot id="cockpit.voice">
          <Section title="Voice Assist Settings" />
          <Card>
            <VoicePick />
            <Divider />
            <View style={{ paddingVertical: 4, gap: 8 }}>
              <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
                <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Claude budget per day</Text>
                <Text style={{ color: C.text, fontWeight: "700" }}>${sp.today_usd.toFixed(2)} of ${sp.budget_usd.toFixed(2)}</Text>
              </View>
              <Progress value={sp.today_usd} of={sp.budget_usd || 1} color={sp.today_usd >= sp.budget_usd ? C.bad : C.accent} />
              <Segmented value={String(sp.budget_usd)} onChange={(v) => setting("daily_budget_usd", v)}
                options={["0", "1", "2", "5", "10"].map((x) => ({ key: x, label: `$${x}` }))} />
              <T small>When today's budget is used up: {sp.settings.over_budget === "stop" ? "Claude stops until tomorrow." : "Gemini (free) answers instead."}
                {"  "}<Text style={{ color: C.accent }} onPress={() => setting("over_budget", sp.settings.over_budget === "stop" ? "gemini" : "stop")}>Change</Text></T>
              <Line label="This month" value={`$${sp.month_usd.toFixed(2)}`} />
              {Object.entries(sp.month).map(([k, v]: any) => <Line key={k} label={`  ${k}`} value={`${v.answers} answers · $${v.usd.toFixed(2)}`} />)}
            </View>
            <Divider />
            <Pressable onPress={() => router.push("/testlab")} style={{ flexDirection: "row", alignItems: "center", paddingTop: 10 }}>
              <View style={{ flex: 1 }}>
                <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Test lab</Text>
                <T small>Recorded test runs of Ananta: answers from both models, voice, stability{sp.tests ? ` · today $${sp.tests.today_usd.toFixed(2)} of $${sp.tests.budget_usd.toFixed(2)}` : ""}</T>
              </View>
              <Text style={{ color: C.faint, fontSize: 18 }}>›</Text>
            </Pressable>
          </Card>
        </Spot>
      ) : null}

      <Btn label="Sign out" kind="secondary" onPress={async () => { await logout(); clearMe(); router.replace("/login"); }} />
      <LiveSheet open={live} onClose={() => setLive(false)} />
    </Screen>
  );
}
