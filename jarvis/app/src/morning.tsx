// Today on India's Home (Madhav, 23 Oct: "a clean market view for the day and our chances"; 29 Oct, the plan's Phase 4.5: a Today section that
// expands to show what Ananta found, what it would do and what it is waiting for; charts with support and resistance zones on request; a white
// overlay Ananta closes when the view is ready). Read › opens the whole note (the view, Ananta's plan, the chances with their baselines, what to
// watch, the reviewer's second opinion, yesterday's scorecard, the opening update, and after the close the shadow trader's sealed plan).
// Ask › hands it to the voice. Paper only, never advice.
import { useEffect, useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useData } from "./useData";
import { Act, Btn, Card, T, s as st } from "./ui";
import { C } from "./theme";
import { askAbout } from "./context";
import { useSheetRequest } from "./spotlight";
import { LineChart } from "./charts";

function Section({ title, lines }: { title: string; lines?: string[] | string | null }) {
  const arr = !lines ? [] : Array.isArray(lines) ? lines : String(lines).split("\n").filter((x) => x.trim());
  if (!arr.length) return null;
  return (
    <View style={{ gap: 4, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 10 }}>
      <Text style={st.h}>{title}</Text>
      {arr.map((x, i) => <T key={i} small>{x}</T>)}
    </View>
  );
}

// The model's note carries its own headings on their own lines; show each as a section.
function noteSections(words?: string | null): { title: string; lines: string[] }[] {
  if (!words) return [];
  const heads = ["The view", "What Ananta is doing today", "Our chances, honestly", "Watch today", "If you trade today", "Lessons from yesterday"];
  const out: { title: string; lines: string[] }[] = [];
  let cur: { title: string; lines: string[] } | null = null;
  for (const raw of words.split("\n")) {
    const line = raw.trim();
    if (!line) continue;
    const h = heads.find((x) => line.toLowerCase().replace(/[:*#]/g, "").trim() === x.toLowerCase());
    if (h) { cur = { title: h, lines: [] }; out.push(cur); continue; }
    if (!cur) { cur = { title: "Ananta's note", lines: [] }; out.push(cur); }
    cur.lines.push(line.replace(/^[-•*]\s*/, ""));
  }
  return out;
}

// One expander of the Today card: a title line, the first line always visible, the rest on tap.
function Part({ title, lines, openByDefault = false }: { title: string; lines: string[]; openByDefault?: boolean }) {
  const [open, setOpen] = useState(openByDefault);
  if (!lines.length) return null;
  return (
    <Pressable onPress={() => setOpen(!open)} accessibilityRole="button" accessibilityState={{ expanded: open }} style={{ gap: 3, borderTopWidth: 1, borderTopColor: C.line, paddingTop: 8 }}>
      <View style={st.row}>
        <Text style={[st.h, { fontSize: 14 }]}>{title}</Text>
        <Text style={st.act}>{open ? "Less" : lines.length > 1 ? `More (${lines.length})` : ""}</Text>
      </View>
      {(open ? lines : lines.slice(0, 1)).map((x, i) => <T key={i} small numberOfLines={open ? undefined : 2}>{x}</T>)}
    </Pressable>
  );
}

// The chart on request: the last 120 closes with the 50- and 200-day averages and the support and resistance zones (daily closes; a description).
function ChartSheet({ name, onClose }: { name: string; onClose: () => void }) {
  const [which, setWhich] = useState(name);
  const { data: d, loading } = useData(`/v3/chart/${encodeURIComponent(which)}`, 300000);
  const ch = d?.chart ?? {};
  const closes: number[] = ch.closes ?? [];
  const refs = [
    ...((ch.support ?? []) as number[]).slice(0, 2).map((v) => ({ value: v, label: `S ${Math.round(v).toLocaleString()}`, color: C.good })),
    ...((ch.resistance ?? []) as number[]).slice(0, 2).map((v) => ({ value: v, label: `R ${Math.round(v).toLocaleString()}`, color: C.bad })),
  ];
  return (
    <Modal visible transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 12 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center" }}>
          <View style={st.row}>
            <Text style={st.h}>{d?.name ?? which} · {d?.as_of ?? ""}</Text>
            <Act tight label="✕" onPress={onClose} />
          </View>
          <View style={{ flexDirection: "row", gap: 8 }}>
            {["NIFTY", "BANKNIFTY"].map((k) => <Act key={k} tight label={k === which ? `● ${k}` : k} onPress={() => setWhich(k)} />)}
          </View>
          {loading && !d ? <T small>Drawing…</T> : closes.length ? (
            <LineChart height={200} refs={refs} xLabels={[ch.dates?.[0] ?? "", ch.dates?.[ch.dates.length - 1] ?? ""]}
              series={[
                { data: closes, color: C.accent, label: "close", fill: true },
                { data: (ch.sma50 ?? []) as (number | null)[], color: C.warn, label: "50-day", dashed: true, width: 1 },
                { data: (ch.sma200 ?? []) as (number | null)[], color: C.dim, label: "200-day", dashed: true, width: 1 },
              ]} />
          ) : <T small>No chart for {which} yet.</T>}
          {d?.words ? <T small>{d.words}</T> : null}
          <T faint small>{d?.note ?? "Daily closes; zones are swing levels plus or minus half a round step; a description, never a rule."}</T>
          <Btn label="Ask Ananta about this chart" onPress={() => { onClose(); askAbout({ screen: "home", label: `the ${which} chart` }, `Walk me through the ${which} chart: where are support and resistance, and what does it say for today?`); }} />
        </Pressable>
      </Pressable>
    </Modal>
  );
}

// The white overlay before the view is ready in the Indian pre-market (07:00-09:15 IST): Ananta closes it when the view lands; a tap closes it too.
function PreMarketOverlay({ ready, session }: { ready: boolean; session?: string | null }) {
  const [dismissed, setDismissed] = useState(false);
  const ist = new Date(Date.now() + 5.5 * 3600 * 1000);
  const hhmm = ist.getUTCHours() * 60 + ist.getUTCMinutes();
  const istToday = ist.toISOString().slice(0, 10);
  const preMarket = hhmm >= 7 * 60 && hhmm < 9 * 60 + 15;
  useEffect(() => { if (ready && session === istToday) setDismissed(true); }, [ready, session, istToday]);
  if (dismissed || !preMarket || (ready && session === istToday)) return null;
  return (
    <Modal visible transparent animationType="fade" onRequestClose={() => setDismissed(true)}>
      <Pressable onPress={() => setDismissed(true)} style={{ flex: 1, backgroundColor: "#FFFFFF", alignItems: "center", justifyContent: "center", padding: 24, gap: 10 }}>
        <Text style={{ fontSize: 20, fontWeight: "700", color: "#111" }}>Ananta is reading the market</Text>
        <Text style={{ fontSize: 15, color: "#444", textAlign: "center" }}>The view for today lands by 08:30 Indian time and this screen closes by itself. Tap to look around meanwhile.</Text>
      </Pressable>
    </Modal>
  );
}

export function MorningCard() {
  const { data: m } = useData("/v3/morning", 120000);
  const [open, setOpen] = useState(false);
  const [chart, setChart] = useState<string | null>(null);
  useSheetRequest(["morning", "today"], () => setOpen(true));                  // "show the morning view" / "show me today" by voice
  useSheetRequest(["chart"], () => setChart("NIFTY"));                          // "show me the chart"
  const istToday = new Date(Date.now() + 5.5 * 3600 * 1000).toISOString().slice(0, 10);
  if (!m?.ready) return <PreMarketOverlay ready={false} session={null} />;
  const note = noteSections(m.words);
  // the session's own day decides the words (24 Oct: "This morning · 23 Oct" showed on a Saturday)
  const when = !m.session || m.session === istToday ? "Today" : m.session > istToday ? "Next session" : "Last session";
  const found: string[] = [...(m.view ?? []), ...(m.watch ?? []).slice(0, 3)];
  const would: string[] = [...(m.plan ?? [])];
  const waiting: string[] = [m.waiting?.words ?? ""].filter(Boolean);
  const after = m.shadow?.plan;
  return (
    <Card>
      <PreMarketOverlay ready={!!m.ready} session={m.session} />
      <View style={st.row}>
        <Text style={st.h}>{when} · {m.session_words}</Text>
        <View style={{ flexDirection: "row", gap: 8 }}>
          <Act tight label="Chart ›" onPress={() => setChart("NIFTY")} />
          <Act tight label="Read ›" onPress={() => setOpen(true)} />
        </View>
      </View>
      <Part title="What Ananta found" lines={found} openByDefault />
      <Part title="What it would do" lines={would} />
      <Part title="What it is waiting for" lines={waiting} />
      <Part title="The clocks (trials running)" lines={(m.clocks ?? []) as string[]} />
      {m.sealed ? <T faint small>{m.sealed.before_open ? "Written and sealed before the open." : "Written after the open."}</T> : null}
      <View style={{ flexDirection: "row", gap: 10 }}>
        <Act tight label="Ask ›" onPress={() => askAbout({ screen: "home", label: "the morning view" }, "Good morning. What is the view for today, and what are our chances?")} />
      </View>
      {chart ? <ChartSheet name={chart} onClose={() => setChart(null)} /> : null}
      {open ? (
        <Modal visible transparent animationType="fade" onRequestClose={() => setOpen(false)}>
          <Pressable onPress={() => setOpen(false)} style={{ flex: 1, backgroundColor: "rgba(0,0,0,0.55)", justifyContent: "center", padding: 12 }}>
            <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 16, borderWidth: 1, borderColor: C.line, padding: 16, gap: 10, maxWidth: 560, width: "100%", alignSelf: "center", maxHeight: "92%" }}>
              <View style={st.row}>
                <Text style={st.h}>Morning view · {m.session_words}</Text>
                <Act tight label="✕" onPress={() => setOpen(false)} />
              </View>
              <ScrollView contentContainerStyle={{ gap: 10 }}>
                {note.length ? note.map((s) => <Section key={s.title} title={s.title} lines={s.lines} />) : <>
                  <Section title="The view" lines={m.view} />
                  <Section title="What Ananta is doing today" lines={m.plan} />
                  <Section title="Our chances, honestly" lines={m.chances} />
                  <Section title="Watch today" lines={m.watch} />
                  <Section title="Yesterday's scorecard" lines={m.yesterday} />
                </>}
                {m.opening?.words ? <Section title="The opening (after the first hour)" lines={m.opening.words} /> : null}
                <Section title="Second opinion (an independent reviewer)" lines={m.review} />
                {after ? <Section title="The shadow trader (a second model, blind to Ananta's plan; read after the close)"
                  lines={[`Stance: ${String(after.stance ?? "").replace(/_/g, " ")}${after.silent ? " (chose to stay silent)" : ""}. ${after.stance_why ?? ""}`,
                          after.blind_spot ? `What Ananta's rules may have missed: ${after.blind_spot}` : "",
                          ...((after.watch ?? []) as any[]).map((w: any) => `Watch ${w.symbol} (${w.direction}): ${w.why ?? ""}`)].filter(Boolean)} /> : null}
                {m.shadow?.words ? <T faint small>{m.shadow.words}</T> : null}
                {note.length ? <Section title="Yesterday's scorecard" lines={m.yesterday} /> : null}
                <T small>{m.read}</T>
                <Btn label="Talk it over with Ananta" onPress={() => { setOpen(false); askAbout({ screen: "home", label: "the morning view" }, "Walk me through this morning's view: the market, your plan, our chances and what to watch."); }} />
              </ScrollView>
            </Pressable>
          </Pressable>
        </Modal>
      ) : null}
    </Card>
  );
}
