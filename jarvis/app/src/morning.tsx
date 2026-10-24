// The morning view on India's Home (Madhav, 23 Oct, 20:23: "a clean market view for the day and our chances ... already loading in the start of the
// morning"). One card: the session, three lines of the view, Read › opens the whole note (the view, Ananta's plan, the chances with their baselines,
// what to watch, the reviewer's second opinion, yesterday's scorecard, the opening update), Ask › hands it to the voice. Paper only, never advice.
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { useData } from "./useData";
import { Act, Btn, Card, T, s as st } from "./ui";
import { C } from "./theme";
import { askAbout } from "./context";

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

export function MorningCard() {
  const { data: m } = useData("/v3/morning", 120000);
  const [open, setOpen] = useState(false);
  if (!m?.ready) return null;
  const first = (m.view ?? []).slice(0, 2);
  const note = noteSections(m.words);
  return (
    <Card>
      <View style={st.row}>
        <Text style={st.h}>This morning · {m.session_words}</Text>
        <Act tight label="Read ›" onPress={() => setOpen(true)} />
      </View>
      {first.length ? <T numberOfLines={4}>{first[0]}</T> : null}
      {first.length > 1 ? <T faint numberOfLines={2}>{first[1]}</T> : null}
      <View style={{ flexDirection: "row", gap: 10 }}>
        <Act tight label="Ask ›" onPress={() => askAbout({ screen: "home", label: "the morning view" }, "Good morning. What is the view for today, and what are our chances?")} />
      </View>
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
