// The Ananta button (Madhav, Oct 15): the mark at the top right of Home, with a number when something waits for him. It opens
// Ananta's space: what needs you, Ananta's note, the lab, findings, as notification rows; each opens to the full item. These four
// used to sit on Home itself; the Home page now shows the account and its trades, and this button carries the rest.
import { useState } from "react";
import { Modal, Pressable, ScrollView, Text, View } from "react-native";
import { router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { ActionCard } from "./actions";
import { api } from "./api";
import { ExplainSheet, showToast } from "./blocks";
import { askAbout, goTab } from "./context";
import { Findings } from "./home";
import { AnantaMark } from "./logo";
import { C } from "./theme";
import { Btn, Card, Divider, ListState, T, dayOf, s as st } from "./ui";
import { useData } from "./useData";

// what the button counts: the decisions waiting (rules that passed, the mandate's actions, trend changes) and new findings
export function useAnantaCount(pending: number, findings: any[]) {
  const { data: nd } = useData("/v3/needs", 300000);
  const { data: inbox } = useData("/v3/inbox");
  const needs = (nd?.items?.length ?? 0) + (inbox?.actions?.length ?? 0) + (pending ? 1 : 0);
  return { needs, findings: findings.length, total: needs + findings.length };
}

export function AnantaButton({ count, onPress }: { count: number; onPress: () => void }) {
  return (
    <Pressable onPress={onPress} accessibilityRole="button" accessibilityLabel={count ? `Ananta, ${count} to check` : "Ananta"} hitSlop={6}
      style={({ pressed }) => ({ width: 60, height: 60, borderRadius: 30, alignItems: "center", justifyContent: "center", opacity: pressed ? 0.7 : 1 })}>
      <AnantaMark color={C.accent} size={56} grey={C.faint} ink={C.bg} />
      {count ? (
        <View style={{ position: "absolute", top: -4, right: -4, minWidth: 20, height: 20, borderRadius: 10, backgroundColor: C.bad, alignItems: "center", justifyContent: "center", paddingHorizontal: 5, borderWidth: 2, borderColor: C.bg }}>
          <Text style={{ color: C.onInk, fontSize: 11, fontWeight: "800" }}>{count}</Text>
        </View>
      ) : null}
    </Pressable>
  );
}

// a notification row: a tag, a title, one line, a chevron
function Row({ tag, tone, title, line, onPress, right }: { tag: string; tone?: "warn" | "accent" | "good" | "dim"; title: string; line?: string; onPress?: () => void; right?: React.ReactNode }) {
  const fg = tone === "warn" ? C.warnDeep : tone === "good" ? C.goodDeep : tone === "accent" ? C.accent : C.dim;
  const bg = tone === "warn" ? C.warnSoft : tone === "good" ? C.goodSoft : tone === "accent" ? C.accentSoft : C.card2;
  return (
    <Pressable onPress={onPress} disabled={!onPress} accessibilityRole={onPress ? "button" : undefined}
      style={({ pressed }) => ({ flexDirection: "row", gap: 10, paddingVertical: 11, alignItems: "center", opacity: pressed ? 0.6 : 1 })}>
      <View style={{ backgroundColor: bg, borderRadius: 6, paddingHorizontal: 6, paddingVertical: 3, alignSelf: "flex-start", marginTop: 2 }}>
        <Text style={{ color: fg, fontSize: 10, fontWeight: "800" }}>{tag}</Text>
      </View>
      <View style={{ flex: 1, gap: 2 }}>
        <Text style={st.rowTitle} numberOfLines={2}>{title}</Text>
        {line ? <T small numberOfLines={2}>{line}</T> : null}
      </View>
      {right ?? (onPress ? <Text style={{ color: C.faint, fontSize: 18 }}>›</Text> : null)}
    </Pressable>
  );
}

export function AnantaSheet({ open, onClose, home, onChanged }: { open: boolean; onClose: () => void; home: any; onChanged: () => void }) {
  const top = useSafeAreaInsets().top;
  const { data: nd, reload: reloadNeeds } = useData(open ? "/v3/needs" : null, 300000);
  const { data: inbox, reload: reloadInbox } = useData(open ? "/v3/inbox" : null);
  const [need, setNeed] = useState<any>(null);
  const [noteOpen, setNoteOpen] = useState(false);
  const [planOpen, setPlanOpen] = useState(false);
  const [setupsOpen, setSetupsOpen] = useState(false);
  const { data: sb } = useData(open ? "/v3/setups?n=12" : null, 300000);
  const board = sb?.board;
  const s = home?.summary ?? {};
  const m = home?.mission ?? {};
  const note = m.account?.note;
  const plan = m.account?.plan;                        // discipline (24 Oct 2026): one plan line, the four checks, the conflicts
  const checkName = (id: string) => ({ idle_cash: "Idle cash", core_exit: "Core exit", book_bleed: "Book bleed", explorer_costs: "Explorer costs" } as any)[id] ?? id;
  const lab: any[] = m.account?.lab ?? [];
  const findings: any[] = (m.findings ?? []).slice(0, 5);
  const pending = s.portfolio?.pending ?? 0;
  const items: any[] = nd?.items ?? [];
  const actions: any[] = inbox?.actions ?? [];
  const needs = items.length + actions.length + (pending ? 1 : 0);
  const refresh = () => { reloadNeeds(); reloadInbox(); onChanged(); };
  const word = (step: string) => String(step).toLowerCase().replace(/_/g, " ");
  const decide = async (it: any, decision: "approve" | "later") => {
    try {
      await api("/v3/needs/decide", { id: it.id, decision });
      showToast(decision === "approve" ? (it.kind === "rx" ? "Yes recorded · sent to the repair board ✓" : `${it.rule} steps up to ${word(it.to)} ✓`) : "Hidden for a week ✓");
    } catch (e: any) { showToast(e?.message ?? "Not changed"); }
    setNeed(null);
    refresh();
  };
  const go = (f: () => void) => { onClose(); setTimeout(f, 80); };
  const measuring = lab.filter((x) => x.status === "EVIDENCE").length;
  const counted = lab.filter((x) => x.status === "ACTIVE" || x.status === "UNDER_REVIEW").length;
  return (
    <Modal visible={open} animationType="slide" onRequestClose={onClose}>
      <View style={{ flex: 1, backgroundColor: C.bg, paddingTop: top }}>
        <View style={{ height: 48, flexDirection: "row", alignItems: "center", paddingHorizontal: 16, gap: 10 }}>
          <AnantaMark color={C.accent} size={34} grey={C.faint} ink={C.bg} />
          <Text style={{ color: C.text, fontWeight: "800", fontSize: 18, flex: 1 }}>Ananta</Text>
          <Pressable onPress={onClose} hitSlop={12} accessibilityLabel="Close"><Text style={{ color: C.dim, fontSize: 20 }}>✕</Text></Pressable>
        </View>
        <ScrollView contentContainerStyle={{ padding: 16, gap: 12, paddingBottom: 40 }}>
          <T small>{needs ? `${needs} thing${needs === 1 ? "" : "s"} need${needs === 1 ? "s" : ""} you · nothing happens until you confirm` : "Nothing needs you right now. The next review comes at the daily close."}</T>

          <Card title={`Needs you${needs ? ` · ${needs}` : ""}`}>
            {!nd && !inbox ? <ListState state="loading" lines={1} /> : null}
            {nd && inbox && needs === 0 ? <ListState state="empty" text="Nothing right now." /> : null}
            {items.map((it: any, i: number) => (
              <View key={it.id}>
                {i ? <Divider /> : null}
                <Row tag="DECISION" tone="warn" title={it.title} line={it.line} onPress={() => setNeed(it)} />
              </View>
            ))}
            {actions.map((a: any) => <ActionCard key={a.id} a={a} onDone={refresh} />)}
            {pending ? (
              <View>
                {items.length ? <Divider /> : null}
                <Row tag="TREND" tone="accent" title={`${pending} trend-portfolio change${pending === 1 ? "" : "s"} wait${pending === 1 ? "s" : ""} for your approval`}
                  line="Review the suggested changes, then approve or reject them."
                  onPress={() => go(() => goTab({ pathname: "/(tabs)/watchlists", params: { tab: "ananta", sub: "portfolio", t: String(Date.now()) } } as any))} />
              </View>
            ) : null}
          </Card>

          {plan ? (
            <Card title={`The plan · ${dayOf(plan.day) || plan.day}`}>
              <Text style={[st.t, { fontSize: 16, lineHeight: 23 }]} numberOfLines={planOpen ? undefined : 3}>{plan.line}</Text>
              {(plan.checks ?? []).length ? (
                <View style={{ gap: 4, marginTop: 6 }}>
                  {(plan.checks ?? []).map((c: any) => (
                    <T key={c.id} small>{c.state === "FAIL" ? "✗" : c.state === "OK" ? "✓" : "?"} {checkName(c.id)}: {c.words}</T>
                  ))}
                </View>
              ) : null}
              {(plan.conflicts ?? []).map((c: any, i: number) => <T key={i} small>⚠ {c.words}</T>)}
              <View style={[st.row, { marginTop: -2 }]}>
                <T faint>One plan, the stance wins conflicts · rules of 24 Oct</T>
                <Text onPress={() => setPlanOpen(!planOpen)} style={st.act}>{planOpen ? "Show less" : "Read it all"}</Text>
              </View>
              <Btn label="Ask about the plan" kind="secondary" onPress={() => go(() => askAbout({ screen: "home", label: "The plan" }, "What is the plan tonight, and what did the reconstruction find?"))} />
            </Card>
          ) : null}

          <Card title={board ? `Setups · ${dayOf(board.day) || board.day}` : "Setups"}>
            {board ? (
              <>
                <T>{board.words}</T>
                {(board.rows ?? []).slice(0, setupsOpen ? 12 : 4).map((r: any, i: number) => (
                  <View key={`${r.coin}-${r.family}`}>
                    {i ? <Divider /> : null}
                    <Row tag={r.state === "FIRED" ? "FIRED" : "NEAR"} tone={r.state === "FIRED" ? "accent" : "dim"}
                      title={`${r.coin} · ${r.name}`}
                      line={`${r.why}${r.stop_pct != null ? ` · stop ${(100 * r.stop_pct).toFixed(1)}% under` : ""}${r.state === "CLOSE" ? ` · waits for ${r.trigger}` : ""}${(r.flags ?? []).length ? ` · ${r.flags.join("; ")}` : ""}`}
                      onPress={() => go(() => askAbout({ screen: "home", label: `Setup ${r.coin}` }, `Tell me about the ${r.name} setup on ${r.coin}: is it worth taking, and what would make it wrong?`))} />
                  </View>
                ))}
                {(board.woke ?? []).length ? <T small>Sent to the brain tonight: {board.woke.join(", ")}</T> : null}
                <View style={[st.row, { marginTop: -2 }]}>
                  <T faint>{board.scanned} coins scanned · only the short dip on tier A has a measured edge</T>
                  <Text onPress={() => setSetupsOpen(!setupsOpen)} style={st.act}>{setupsOpen ? "Show less" : "Show more"}</Text>
                </View>
              </>
            ) : <ListState state="empty" text="The first scan runs after the next daily close (8 pm Toronto)." />}
          </Card>

          <Card title={note ? `Ananta's note · ${dayOf(note.day) || note.day}` : "Ananta's note"}>
            {note ? (
              <>
                <Text style={[st.t, { fontSize: 16, lineHeight: 23 }]} numberOfLines={noteOpen ? undefined : 3}>{note.note}</Text>
                <View style={[st.row, { marginTop: -2 }]}>
                  <T faint>From the database, not from memory</T>
                  <Text onPress={() => setNoteOpen(!noteOpen)} style={st.act}>{noteOpen ? "Show less" : "Read it all"}</Text>
                </View>
                <Btn label="Ask Ananta about today" kind="secondary" onPress={() => go(() => askAbout({ screen: "home", label: "The officer's note" }, "Tell me more about today's note on the account."))} />
              </>
            ) : <ListState state="empty" text="No note yet today. Ananta writes one after the daily close." />}
          </Card>

          <Card title="The lab · measuring in the background">
            <Row tag="LAB" tone="dim" title={`${lab.length} strategies · ${measuring} measuring · ${counted} counted`}
              line={`Explorer ${s.explorer?.opened_today ?? 0} bought, ${s.explorer?.closed_today ?? 0} sold today · every other book keeps measuring`}
              onPress={() => go(() => goTab({ pathname: "/(tabs)/watchlists", params: { tab: "ananta", sub: "lab", t: String(Date.now()) } } as any))} />
          </Card>

          <Findings items={findings} />

          <Btn label="Ananta's own book" kind="secondary" onPress={() => go(() => router.push("/jarvis"))} />
        </ScrollView>

        <ExplainSheet open={!!need} onClose={() => setNeed(null)} title={need?.title ?? ""}>
          {need && need.kind === "rx" ? (
            <>
              <T>{need.line}</T>
              <T dim>{need.meaning}</T>
              <T small>{need.why} {need.note}</T>
              <Btn label="Yes, do it" onPress={() => decide(need, "approve")} />
              <Btn label="Not now · ask me again in a week" kind="secondary" onPress={() => decide(need, "later")} />
            </>
          ) : need ? (
            <>
              <T>{need.why}.</T>
              <T dim>{need.to === "PROMOTED" ? "Promoted" : "Live candidate"} means: {need.meaning}.</T>
              <T small>{need.note}</T>
              <Btn label={`Step up to ${word(need.to)}`} onPress={() => decide(need, "approve")} />
              <Btn label="Keep measuring · ask me again in a week" kind="secondary" onPress={() => decide(need, "later")} />
            </>
          ) : null}
        </ExplainSheet>
      </View>
    </Modal>
  );
}
