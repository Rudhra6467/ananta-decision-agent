// Voice and model settings, in one place (Cockpit › Additional features; Madhav, Oct 13): which model answers (Auto, Claude or
// Google), the voice Ananta speaks with and its speed, the Claude budget, and the test lab. The Ask tab and the voice panel only
// show what is set; they no longer carry the controls.
import React, { useEffect, useState } from "react";
import { Pressable, Switch, Text, View } from "react-native";
import { router } from "expo-router";
import * as SecureStore from "expo-secure-store";
import { api } from "./api";
import { Progress } from "./charts";
import { C } from "./theme";
import * as TTS from "./tts";
import { Divider, Line, Segmented, T } from "./ui";
import { useData } from "./useData";

export function VoiceSettings() {
  const { data: sp, reload } = useData("/v3/spend");
  const [autoOn, setAutoOn] = useState(true);
  const [google, setGoogle] = useState(false);
  const [v, setV] = useState(TTS.voice);
  const [r, setR] = useState(String(TTS.rate));
  useEffect(() => {
    TTS.init().then(() => { setV(TTS.voice); setR(String(TTS.rate)); });
    Promise.all([SecureStore.getItemAsync("ask_auto"), SecureStore.getItemAsync("ask_google")]).then(([a, g]) => {
      if (a) setAutoOn(a === "1"); if (g) setGoogle(g === "1");
    }).catch(() => {});
  }, []);
  const flip = (k: "ask_auto" | "ask_google", val: boolean) => {
    (k === "ask_auto" ? setAutoOn : setGoogle)(val);
    SecureStore.setItemAsync(k, val ? "1" : "0").catch(() => {});
  };
  const setting = async (key: string, value: string) => { await api("/v3/settings", { key, value }); reload(); };
  const LABEL: Record<string, string> = { Deep: "Deep · male", British: "British · male", Calm: "Calm · female", Friendly: "Friendly · female", Bright: "Bright · female" };
  return (
    <View style={{ gap: 10 }}>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View style={{ flex: 1 }}>
          <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Who answers</Text>
          <T small dim>{google ? "Google Gemini (free, slower)" : "Claude (Sonnet: faster and better here)"}</T>
        </View>
        <View style={{ flexDirection: "row", alignItems: "center", gap: 6 }}>
          <Text style={{ color: google ? C.faint : C.text, fontSize: 13, fontWeight: "700" }}>Claude</Text>
          <Switch value={google} onValueChange={(x) => flip("ask_google", x)} trackColor={{ true: C.accent, false: C.line }} />
          <Text style={{ color: google ? C.text : C.faint, fontSize: 13, fontWeight: "700" }}>Google</Text>
        </View>
      </View>
      <View style={{ flexDirection: "row", alignItems: "center", justifyContent: "space-between" }}>
        <View style={{ flex: 1 }}>
          <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Auto</Text>
          <T small dim>On: Ananta picks the model per question. Off: always the deeper one.</T>
        </View>
        <Switch value={autoOn} onValueChange={(x) => flip("ask_auto", x)} trackColor={{ true: C.accent, false: C.line }} />
      </View>
      <Divider />
      <T dim small>Voice</T>
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 6 }}>
        {[...TTS.VOICES, "Phone"].map((x) => (
          <Pressable key={x} onPress={() => { setV(x); if (x === "Phone") TTS.setEngine("phone"); else { TTS.setEngine("natural"); TTS.setVoice(x); api("/v3/me/setup", { voice: x }).catch(() => {}); TTS.speakText(`Hello. This is the ${x} voice.`); } }}
            style={{ borderRadius: 999, paddingHorizontal: 11, paddingVertical: 6, borderWidth: 1, borderColor: v === x ? C.accent : C.line, backgroundColor: v === x ? C.accentSoft : C.card }}>
            <Text style={{ color: v === x ? C.accent : C.text, fontSize: 13, fontWeight: "600" }}>{LABEL[x] ?? x}</Text>
          </Pressable>
        ))}
      </View>
      <T dim small>Speed</T>
      <Segmented value={r} onChange={(k) => { setR(k); TTS.setRate(Number(k)); }} options={TTS.RATES.map((x) => ({ key: String(x), label: `${x}×` }))} />
      {sp ? (
        <>
          <Divider />
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Claude budget per day</Text>
            <Text style={{ color: C.text, fontWeight: "700" }}>${sp.today_usd.toFixed(2)} of ${sp.budget_usd.toFixed(2)}</Text>
          </View>
          <Progress value={sp.today_usd} of={sp.budget_usd || 1} color={sp.today_usd >= sp.budget_usd ? C.bad : C.accent} />
          <Segmented value={String(sp.budget_usd)} onChange={(x) => setting("daily_budget_usd", x)} options={["0", "1", "2", "5", "10"].map((x) => ({ key: x, label: `$${x}` }))} />
          <T small>When today's budget is used up: {sp.settings?.over_budget === "stop" ? "Claude stops until tomorrow." : "Gemini (free) answers instead."}
            {"  "}<Text style={{ color: C.accent }} onPress={() => setting("over_budget", sp.settings?.over_budget === "stop" ? "gemini" : "stop")}>Change</Text></T>
          <Line label="This month" value={`$${sp.month_usd.toFixed(2)}`} />
          <Divider />
          <Pressable onPress={() => router.push("/testlab")} style={{ flexDirection: "row", alignItems: "center", paddingTop: 6 }}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>Test lab</Text>
              <T small>Recorded test runs: answers, voice, stability{sp.tests ? ` · today $${sp.tests.today_usd.toFixed(2)} of $${sp.tests.budget_usd.toFixed(2)}` : ""}</T>
            </View>
            <Text style={{ color: C.faint, fontSize: 18 }}>›</Text>
          </Pressable>
        </>
      ) : null}
    </View>
  );
}
