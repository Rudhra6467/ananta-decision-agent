// More (was Cockpit; plan 3.8, D11), regrouped Oct 14 to one grammar: "settings, evidence, and is everything running?"
//  · the title row (in the tabs header): the alerts bell and the sun/moon switch
//  · who is signed in (one row)
//  · Controls: Kill switch, Autopilot, Live (locked), Ask Ananta, Voice assist — one row each, a switch on the right
//  · Voice and model: who answers, the voice and speed, the Claude budget (each row opens Additional features)
//  · Evidence: the reviews, the repair loop, strategy status, lost trades
//  · System: every part running, costs, live money (off), the rest of Additional features
//  · notifications, Sign out
// A visitor's More controls only their own account: Pause Ananta for me, Auto mode, Live (coming soon), their voice.
import { Spot } from "../../src/spotlight";
import { askAbout, setScreen } from "../../src/context";
import { useFocusEffect } from "expo-router";
import React, { useCallback, useEffect, useState } from "react";
import { Alert, Pressable, Switch, Text, View } from "react-native";
import { router } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { api, logout } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { Btn, Busy, Card, Divider, ErrorBox, Line, ListState, Screen, Section, Segmented, T, s as st } from "../../src/ui";
import { useData } from "../../src/useData";
import { getMarket } from "../../src/market";
import { C } from "../../src/theme";
import { ExplainSheet, VERDICT, showToast } from "../../src/blocks";
import { clearMe, loadMe, useMe } from "../../src/visitor";
import * as TTS from "../../src/tts";
import { NotificationsCard } from "../../src/notifications";

export default function CockpitPage() {
  const me = useMe();
  if (!me) return <Busy />;
  return me.guest ? <VisitorCockpit /> : <Cockpit />;
}

// ---- one control: label, one line of help, a switch; 44 tall at least ----
function SwitchRow({ label, help, on, onChange, danger, locked, last }: {
  label: string; help: string; on: boolean; onChange: (v: boolean) => void; danger?: boolean; locked?: boolean; last?: boolean;
}) {
  return (
    <View style={{ flexDirection: "row", alignItems: "center", gap: 12, minHeight: 56, paddingVertical: 8, borderBottomWidth: last ? 0 : 1, borderBottomColor: C.line }}>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={st.rowTitle}>{label}{locked ? "  ·  locked" : ""}</Text>
        <T small>{help}</T>
      </View>
      <Text style={{ color: on ? (danger ? C.bad : C.accent) : C.dim, fontSize: 13, fontWeight: "700" }}>{on ? "ON" : "OFF"}</Text>
      <Switch value={on} onValueChange={onChange} trackColor={{ true: danger ? C.bad : C.accent, false: C.line }} accessibilityLabel={label} />
    </View>
  );
}

// ---- one row that opens something: label left, the current value right, a chevron ----
function GoRow({ label, value, onPress, dot, last }: { label: string; value?: string; onPress: () => void; dot?: string; last?: boolean }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 10, minHeight: 48, paddingVertical: 6,
      borderBottomWidth: last ? 0 : 1, borderBottomColor: C.line, opacity: pressed ? 0.6 : 1 })}>
      <Text style={[st.rowTitle, { flex: 1 }]}>{label}</Text>
      {dot ? <View style={{ width: 8, height: 8, borderRadius: 4, backgroundColor: dot }} /> : null}
      {value ? <T small numberOfLines={1}>{value}</T> : null}
      <Text style={{ color: C.dim, fontSize: 18 }}>›</Text>
    </Pressable>
  );
}

// Live: never switches on from here until live trading is approved; the switch opens this sheet and stays off.
function LiveSheet({ open, onClose }: { open: boolean; onClose: () => void }) {
  const Opt = ({ title, sub }: { title: string; sub: string }) => (
    <View style={{ borderWidth: 1, borderColor: C.line, borderRadius: 12, padding: 14, gap: 4, opacity: 0.85 }}>
      <View style={{ flexDirection: "row", alignItems: "center" }}>
        <Text style={[st.rowTitle, { flex: 1 }]}>{title}</Text>
        <View style={{ backgroundColor: C.card2, borderRadius: 999, paddingHorizontal: 8, paddingVertical: 3 }}>
          <Text style={{ color: C.dim, fontSize: 11, fontWeight: "800" }}>COMING SOON</Text>
        </View>
      </View>
      <T small>{sub}</T>
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
      <T small>Voice</T>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
        {TTS.VOICES.map((x) => (
          <Pressable key={x} onPress={() => { setV(x); TTS.setVoice(x); api("/v3/me/setup", { voice: x }).catch(() => {}); TTS.speakText(`Hello. This is the ${x} voice.`); }}
            style={{ borderRadius: 999, paddingHorizontal: 11, minHeight: 32, justifyContent: "center", borderWidth: 1, borderColor: v === x ? C.accent : C.card2, backgroundColor: v === x ? C.accentSoft : C.card2 }}>
            <Text style={{ color: v === x ? C.accent : C.text, fontSize: 13, fontWeight: "600" }}>{LABEL[x] ?? x}</Text>
          </Pressable>
        ))}
      </View>
      <T small>Speed</T>
      <Segmented value={r} onChange={(k) => { setR(k); TTS.setRate(Number(k)); }} options={TTS.RATES.map((x) => ({ key: String(x), label: `${x}×` }))} />
    </View>
  );
}

// ---- a visitor's More: their own account only ----
function VisitorCockpit() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "cockpit", label: "More: your own controls, voice and account" }); }, []));
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
      <Card>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
          <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: C.accentSoft, alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: C.accent, fontSize: 17, fontWeight: "700" }}>{String(p.name ?? me?.name ?? "?").slice(0, 1).toUpperCase()}</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={st.rowTitle}>{p.name ?? me?.name ?? "Your account"}</Text>
            <T small>Practice account · paper money{p.capital ? ` · started with $${Number(p.capital).toLocaleString()}` : ""}{p.coins?.length ? ` · ${p.coins.length} coins` : ""}</T>
          </View>
        </View>
      </Card>
      <Spot id="cockpit.controls">
        <Section title="Controls" />
        <Card>
          <SwitchRow label="Pause Ananta for me" help="On: no watch acts for you; nothing new is bought." on={!!p.paused} danger onChange={(v) => set("paused", v)} />
          <SwitchRow label="Auto mode" help="On: your watches take their paper trades and tell you. Off: Ananta asks first." on={!!p.auto} onChange={(v) => set("auto", v)} />
          <SwitchRow label="Live" help="Real money: coming soon." on={false} locked onChange={() => setLive(true)} last />
        </Card>
      </Spot>
      <Section title="Voice" />
      <Card><VoicePick /></Card>
      <NotificationsCard />
      <Btn label="Sign out" kind="secondary" onPress={async () => { await logout(); clearMe(); router.replace("/login"); }} />
      <LiveSheet open={live} onClose={() => setLive(false)} />
    </Screen>
  );
}

// ---- Madhav's More ----
function Cockpit() {
  useFocusEffect(useCallback(() => { setScreen({ screen: "cockpit", label: "More: controls, voice and model, evidence, system" }); }, []));
  const { data: d, err, loading, reload } = useData("/v3/cockpit");
  const { data: sp, reload: reloadSpend } = useData("/v3/spend");
  const { data: ev } = useData("/v3/evidence/collected", 600000);
  const { data: ld } = useData("/v3/universe/ladder", 600000);
  const [live, setLive] = useState(false);
  const [autoOn, setAutoOn] = useState(true);
  const [google, setGoogle] = useState(false);
  const [voice, setVoice] = useState({ v: TTS.voice, e: TTS.engine, r: TTS.rate });
  useFocusEffect(useCallback(() => {
    Promise.all([SecureStore.getItemAsync("ask_auto"), SecureStore.getItemAsync("ask_google")]).then(([a, g]) => {
      if (a) setAutoOn(a === "1"); if (g) setGoogle(g === "1");
    }).catch(() => {});
    TTS.init().then(() => setVoice({ v: TTS.voice, e: TTS.engine, r: TTS.rate }));
  }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} onRetry={reload} /></Screen>;
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
  const passed = reviews.filter((r) => r.verdict === "PASS").length;
  const systems: any[] = d.systems ?? [];
  const down = systems.filter((x) => !x.ok);
  const breakers = Object.values(d.circuit_breakers ?? {}) as any[];
  const tripped = breakers.filter((b) => b?.status === "TRIPPED").length;
  const rows: any[] = ld?.rows ?? [];
  const steps = rows.length ? `${rows.filter((r) => r.step === "PROMOTED").length} promoted · ${rows.filter((r) => r.step === "EVIDENCE").length} measuring` : "";
  const who = google ? (autoOn ? "Google · auto" : "Google") : (autoOn ? "Claude · auto" : "Claude · deep");
  const more = () => router.push("/more");

  return (
    <Screen loading={loading} onRefresh={() => { reload(); reloadSpend(); }}>
      <Card onPress={more}>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}>
          <View style={{ width: 40, height: 40, borderRadius: 20, backgroundColor: C.accentSoft, alignItems: "center", justifyContent: "center" }}>
            <Text style={{ color: C.accent, fontSize: 17, fontWeight: "700" }}>M</Text>
          </View>
          <View style={{ flex: 1 }}>
            <Text style={st.rowTitle}>Madhav · owner</Text>
            <T small>Brutal truth on · paper only · additional features ›</T>
          </View>
          <Text style={{ color: C.dim, fontSize: 18 }}>›</Text>
        </View>
      </Card>

      <Spot id="cockpit.controls">
        <Section title="Controls" />
        <Card>
          {getMarket() === "india" ? (d.switches ?? []).map((w: any) => (                                   // India (23 Oct): its own switches, read-only until the gate
            <SwitchRow key={w.key} label={w.label} help={w.help} on={!!w.on} locked onChange={() => {}} />
          )) : (<>
            <SwitchRow label="Kill switch" help="On: close every paper position and block new trades." on={!!sw("kill_switch").on} danger onChange={(v) => flip("kill_switch", v)} />
            <SwitchRow label="Autopilot" help="On: the trend portfolio rebalances by itself." on={!!sw("portfolio_auto").on} onChange={(v) => flip("portfolio_auto", v)} />
            <SwitchRow label="Live" help="Real money: coming soon. Paper only." on={false} locked onChange={() => setLive(true)} />
          </>)}
          <Spot id="cockpit.ai">
            <View>
              <SwitchRow label="Ask Ananta" help="Off: no AI answers at all (nothing can cost money)." on={sp?.settings?.ask_enabled === "1"} onChange={(v) => setting("ask_enabled", v ? "1" : "0")} />
              <SwitchRow label="Voice assist" help="Off: Ananta never speaks or reaches out by itself." on={sp?.settings?.voice_enabled === "1"} onChange={(v) => setting("voice_enabled", v ? "1" : "0")} last />
            </View>
          </Spot>
        </Card>
      </Spot>

      <Section title="Voice and model" />
      <Card>
        <GoRow label="Who answers" value={who} onPress={more} />
        <GoRow label="Voice" value={`${voice.e === "phone" ? "Phone" : voice.v} · ${voice.r}×`} onPress={more} />
        <GoRow label="Teach Ananta my voice" value="so it knows it's you" onPress={() => router.push("/voiceid")} />
        <GoRow label="Claude budget" value={sp ? `$${sp.today_usd.toFixed(2)} of $${sp.budget_usd.toFixed(2)} today` : "…"} onPress={more} last />
      </Card>

      <Spot id="cockpit.evidence">
        <Section title="Evidence" />
        <Card>
          {!ev ? <ListState state="loading" lines={1} /> : null}
          {ev ? <GoRow label="Reviews" value={reviews.length ? `${reviews.length} · ${passed} passed` : "none yet"} onPress={() => router.push("/evidence")} /> : null}
          <GoRow label="The repair loop, live" value="looked · traded · fixed" onPress={() => router.push("/lab")} />
          <GoRow label="Strategy ladder" value={steps || "…"} onPress={() => router.push("/evidence")} />
          <GoRow label="Lost trades" value="by verdict" onPress={() => askAbout({ screen: "cockpit", label: "lost trades" }, "Classify our lost trades: which we won't take again, which we will try again, and where the rules were modified. Use the lost_trades tool.")} last />
        </Card>
        {reviews.length ? (
          <Card>
            <T small>Latest review</T>
            {reviews.slice(0, 1).map((r: any) => {
              const [word, tone] = VERDICT[r.verdict] ?? [r.verdict, "dim"];
              return (
                <Pressable key={r.id} onPress={() => router.push(`/evidence/${r.id}`)} style={({ pressed }) => ({ gap: 3, opacity: pressed ? 0.6 : 1 })}>
                  <Text style={st.rowTitle} numberOfLines={2}>{r.title}</Text>
                  <Text style={{ color: (C as any)[tone], fontSize: 13, fontWeight: "600" }}>{word} <Text style={{ color: C.dim, fontWeight: "400" }}>· {r.date}</Text></Text>
                </Pressable>
              );
            })}
          </Card>
        ) : null}
      </Spot>

      <Section title="System" />
      <Card>
        <GoRow label="Engine" dot={down.length ? C.bad : C.good} value={down.length ? `${down.length} part${down.length === 1 ? "" : "s"} down` : `all ${systems.length} parts running`} onPress={more} />
        <GoRow label="Circuit breakers" value={breakers.length ? (tripped ? `${tripped} tripped` : "none tripped") : "…"} onPress={more} />
        <GoRow label="Costs" value={sp ? `$${sp.today_usd.toFixed(2)} today · $${sp.month_usd.toFixed(2)} this month` : "…"} onPress={more} />
        <GoRow label="Live money" value="off · paper only" onPress={() => setLive(true)} last />
      </Card>

      <NotificationsCard />
      <Btn label="Sign out" kind="secondary" onPress={async () => { await logout(); clearMe(); router.replace("/login"); }} />
      <LiveSheet open={live} onClose={() => setLive(false)} />
    </Screen>
  );
}
