// My flags (Madhav, 23 Oct): every problem flagged from the app, in both markets, with where its fix stands: waiting for your
// choice, queued, being built, live, or back with you for a yes. Tap one that waits for you to choose again.
import { useCallback, useEffect, useState } from "react";
import { useFocusEffect } from "expo-router";
import { setScreen } from "../src/context";
import { Pressable, RefreshControl, ScrollView, Text, View } from "react-native";
import { router } from "expo-router";
import { api } from "../src/api";
import { C, RADIUS, SPACE, TYPE } from "../src/theme";

type Flow = { state: string; state_words: string; lane: string; market: string; screen: string; log: [number, string][]; commit_sha?: string;
  options: { diagnosis: string; options: { title: string; what: string; lane: string; does: string }[]; title?: string; note?: string }; choice?: number | null };
type Row = { num: number; no?: number | null; label?: string; text: string; status: string; status_words: string; note: string; updated_t: number; flow: Flow | null };

const stateColor = (s: string) => s === "deployed" ? C.good : s === "failed" ? C.bad : s === "needs_decision" || s === "triaged" ? C.warn : C.accent;
const when = (t: number) => new Date(t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" });

export default function Flags() {
  const [rows, setRows] = useState<Row[]>([]);
  const [busy, setBusy] = useState(false);
  const [msg, setMsg] = useState("");
  const [open, setOpen] = useState<number | null>(null);
  const load = useCallback(async () => {
    setBusy(true);
    try { setRows((await api<{ flags: Row[] }>("/v3/flags")).flags); setMsg(""); }
    catch (e: any) { setMsg(e?.message ?? "Could not load"); }
    setBusy(false);
  }, []);
  useEffect(() => { load(); const t = setInterval(load, 30000); return () => clearInterval(t); }, [load]);
  useFocusEffect(useCallback(() => { setScreen({ screen: "flags", label: "My flags: every flag with where its fix stands" }); }, []));
  const choose = async (num: number, i: number) => {
    try { const r = await api<{ say: string }>(`/v3/flags/${num}/choose`, { option: i }); setMsg(r.say); load(); }
    catch (e: any) { setMsg(e?.message ?? "Could not send"); }
  };
  const open_ = rows.filter((r) => r.status === "OPEN" || r.status === "PLANNED").length;
  return (
    <ScrollView style={{ flex: 1, backgroundColor: C.bg }} contentContainerStyle={{ padding: SPACE.card, paddingTop: 56, paddingBottom: 120 }}
      refreshControl={<RefreshControl refreshing={busy} onRefresh={load} />}>
      <Pressable onPress={() => router.back()} accessibilityRole="button"><Text style={{ color: C.accent, fontWeight: "700" }}>‹ Back</Text></Pressable>
      <Text style={{ color: C.text, fontSize: TYPE.title, fontWeight: "800", marginTop: 8 }}>My flags</Text>
      <Text style={{ color: C.dim, fontSize: TYPE.meta, marginTop: 4 }}>Your flags: {open_} open · {rows.length} in all · both markets. To flag an app problem, tell Ananta by voice or chat "flag this: …" and pick a fix. To save a research idea, say "note this for research: …": it is written up in full here, with no fixes to pick.</Text>
      {msg ? <Text style={{ color: C.text, marginTop: 10 }}>{msg}</Text> : null}
      {rows.map((r) => {
        const f = r.flow;
        const st = f?.state ?? r.status.toLowerCase();
        return (
          <Pressable key={r.num} onPress={() => setOpen(open === r.num ? null : r.num)} accessibilityRole="button"
            style={{ backgroundColor: C.card, borderColor: C.line, borderWidth: 1, borderRadius: RADIUS.card, padding: 12, marginTop: 10 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
              <Text style={{ color: C.text, fontWeight: "700", flex: 1 }} numberOfLines={open === r.num ? undefined : 2}>{r.no ? `Flag ${r.no}` : `#${r.num}`} · {r.text.replace(/^\[[^\]]*\]\s*/, "")}</Text>
              <Text style={{ color: f ? stateColor(f.state) : r.status === "DONE" ? C.good : C.dim, fontWeight: "700", fontSize: TYPE.meta }}>
                {f ? f.state_words : r.status_words}
              </Text>
            </View>
            {open === r.num ? (
              <View style={{ marginTop: 8, gap: 6 }}>
                {/* 26 Oct: a research note shows in full, to read in the back end; a flag shows its status note */}
                {f?.state === "noted" && f.options?.note ? <Text selectable style={{ color: C.text, fontSize: TYPE.meta, lineHeight: 20 }}>{f.options.note}</Text>
                  : r.note ? <Text style={{ color: C.dim, fontSize: TYPE.meta, lineHeight: 19 }}>{r.note}</Text> : null}
                {f && (st === "triaged" || st === "needs_decision" || st === "failed") ? f.options.options.map((o, i) => (
                  <Pressable key={i} onPress={() => choose(r.num, i)} accessibilityRole="button"
                    style={{ borderColor: o.lane === "SAFE" ? C.line : C.warn, borderWidth: 1, borderRadius: RADIUS.card, padding: 10 }}>
                    <Text style={{ color: C.text, fontWeight: "700" }}>{o.title}</Text>
                    <Text style={{ color: o.lane === "SAFE" ? C.good : C.warn, fontSize: TYPE.meta }}>{o.does}</Text>
                  </Pressable>
                )) : null}
                {f?.log?.slice(-6).map(([t, line], i) => (
                  <Text key={i} style={{ color: C.faint, fontSize: TYPE.meta }}>{when(t)} · {line}</Text>
                ))}
              </View>
            ) : null}
          </Pressable>
        );
      })}
    </ScrollView>
  );
}
