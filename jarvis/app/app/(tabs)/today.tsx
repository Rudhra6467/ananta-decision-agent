import { Spot, useSpotActive } from "../../src/spotlight";
import { useCallback, useState } from "react";
import { Modal, Pressable, ScrollView, Text, TextInput, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { askAbout, setScreen } from "../../src/context";
import { ActionCard } from "../../src/actions";
import { api } from "../../src/api";
import { confirmWithFaceId } from "../../src/guard";
import { Big, Btn, Busy, Card, Divider, Dot, ErrorBox, Row, Screen, Section, Stat, T, pct, usd } from "../../src/ui";
import { useData } from "../../src/useData";
import { C, pnlColor } from "../../src/theme";

const KIND: Record<string, { color: string; label: string }> = {
  buy: { color: C.accent, label: "BUY" }, sell: { color: C.text, label: "SELL" }, watch: { color: C.faint, label: "ORDER" },
  portfolio: { color: C.accent, label: "PORTFOLIO" }, warn: { color: C.warn, label: "WARNING" }, info: { color: C.faint, label: "YOU" },
  alert: { color: C.warn, label: "ALERT" }, brief: { color: C.accent, label: "BRIEF" }, setup: { color: C.good, label: "YOUR SETUP" },
};

export default function Home() {
  const { data: d, err, loading, reload } = useData("/v3/home");
  const { data: inbox, reload: reloadInbox } = useData("/v3/inbox");
  const { data: br, reload: reloadBrief } = useData("/v3/brief", 300000);
  const { data: me } = useData("/v3/me", 0);
  const [briefing, setBriefing] = useState(false);
  const [q, setQ] = useState("");
  const [all, setAll] = useState(false);
  const [briefOpen, setBriefOpen] = useState(false);
  const [showActivity, setShowActivity] = useState(false);
  const activityLit = useSpotActive("home.activity");              // Ananta pointing at it opens it
  useFocusEffect(useCallback(() => { setScreen({ screen: "home", label: "Home tab: today's summary, inbox, brief and activity" }); }, []));
  if (!d && loading) return <Busy />;
  if (!d) return <Screen loading={loading} onRefresh={reload}><ErrorBox err={err ?? "No data"} /></Screen>;
  const s = d.summary;
  const ask = () => {
    if (!q.trim()) return;
    router.push({ pathname: "/(tabs)/ask", params: { q: q.trim(), t: String(Date.now()) } });
    setQ("");
  };
  const approveAll = async () => {
    if (!(await confirmWithFaceId("Approve portfolio changes", `${s.portfolio.pending} paper change(s) will be made now.`))) return;
    await api("/portfolio/approve", { ids: "all" });
    reload();
  };
  const feed = all ? d.feed : d.feed.slice(0, 8);
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="home.value">
      <View style={{ gap: 4 }}>
        <T dim>{s.date} · paper money</T>
        <Big value={usd(s.paper_value)} changeLabel={s.today_change != null ? `${s.today_change >= 0 ? "+" : "-"}$${Math.abs(s.today_change).toFixed(2)} today` : undefined}
          change={s.today_change} />
        <T dim>{s.sentence}</T>
      </View>
      </Spot>

      {me?.guest ? (
        <Card title="Welcome to Ananta" sub="Madhav's trading assistant, in practice mode">
          <T small>Ananta watches 10 coins all day, explains what it sees and why it would or would not trade, and learns from its own record. Everything you do here goes to your own practice book.</T>
          <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, marginTop: 8 }}>
            {["Show me around", "What are we doing here?", "How do I make a paper trade?"].map((q) => (
              <Pressable key={q} onPress={() => router.push({ pathname: "/(tabs)/ask", params: { q, t: String(Date.now()) } })}
                style={{ backgroundColor: C.accent, borderRadius: 8, paddingHorizontal: 12, paddingVertical: 8 }}>
                <Text style={{ color: "#FFF", fontWeight: "700", fontSize: 13 }}>{q}</Text>
              </Pressable>
            ))}
          </View>
        </Card>
      ) : null}

      <Pressable onPress={() => router.push("/(tabs)/ask")} style={{ flexDirection: "row", alignItems: "center", backgroundColor: C.card, borderRadius: 12, borderWidth: 1, borderColor: C.line, paddingHorizontal: 14 }}>
        <TextInput value={q} onChangeText={setQ} onSubmitEditing={ask} returnKeyType="send" placeholder="Ask Ananta about trades or markets…"
          placeholderTextColor={C.faint} style={{ flex: 1, paddingVertical: 13, fontSize: 15, color: C.text }} />
        <Text onPress={ask} style={{ color: C.accent, fontWeight: "700" }}>Ask</Text>
      </Pressable>

      {(inbox?.actions ?? []).length ? (
        <Spot id="home.inbox">
        <Card title="Waiting for your OK" sub="Things Ananta prepared. Nothing happens until you confirm.">
          {inbox.actions.map((a: any) => <ActionCard key={a.id} a={a} onDone={() => { reloadInbox(); reload(); }} />)}
        </Card>
        </Spot>
      ) : null}

      <Spot id="home.brief">
      <Card title={br?.brief ? `${br.brief.kind === "morning" ? "Morning" : "Evening"} brief` : "Daily brief"}
        sub={br?.brief ? new Date(br.brief.t * 1000).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" }) : "Written at 8:00 and 21:30"}
        right={<Text onPress={async () => { setBriefing(true); try { await api("/v3/brief/now", {}); reloadBrief(); } catch (e) { } setBriefing(false); }}
          style={{ color: C.accent, fontWeight: "600" }}>{briefing ? "Writing…" : "Brief me now"}</Text>}>
        {br?.brief ? (
          <Pressable onPress={() => setBriefOpen(true)} accessibilityHint="Opens the full brief">
            <Text numberOfLines={2} ellipsizeMode="tail" style={{ color: C.text, fontSize: 15, lineHeight: 21 }}>{br.brief.text}</Text>
            <Text style={{ color: C.accent, fontSize: 13, fontWeight: "600", marginTop: 4 }}>Read the full brief ›</Text>
          </Pressable>
        ) : <T dim>No brief yet today.</T>}
      </Card>
      </Spot>
      <BriefPopup open={briefOpen} onClose={() => setBriefOpen(false)} title={br?.brief ? `${br.brief.kind === "morning" ? "Morning" : "Evening"} brief` : "Brief"}
        when={br?.brief ? new Date(br.brief.t * 1000).toLocaleString(undefined, { weekday: "short", hour: "numeric", minute: "2-digit" }) : ""} text={br?.brief?.text ?? ""} />

      {s.portfolio.pending ? (
        <Card title={`${s.portfolio.pending} change(s) waiting for you`} sub="The portfolio is in Suggest mode: nothing moves until you approve.">
          <View style={{ flexDirection: "row", gap: 10 }}>
            <View style={{ flex: 1 }}><Btn label="Review" kind="secondary" onPress={() => router.push("/(tabs)/portfolio")} /></View>
            <View style={{ flex: 1 }}><Btn label="Approve all" onPress={approveAll} /></View>
          </View>
        </Card>
      ) : null}

      <Section title="Our market watches" right={<T small>what's running for us</T>} />
      <Spot id="home.books">
      <Card>
        <Row title="Explorer" sub={`${s.explorer.open} open trade(s) · checks 10 coins every 15 min`} value={usd(s.explorer.value)}
          valueSub={`${s.explorer.opened_today} bought · ${s.explorer.closed_today} sold today`} onPress={() => router.push("/(tabs)/portfolio")} />
        <Divider />
        <Row title="Portfolio" sub={`${s.portfolio.holding} coins held · ${s.portfolio.mode === "AUTO" ? "Autopilot on" : "Suggests, you approve"}`}
          value={usd(s.portfolio.value)} valueSub={pct(s.portfolio.return_pct)} valueSubColor={pnlColor(s.portfolio.return_pct)}
          onPress={() => router.push("/(tabs)/portfolio")} />
        <Divider />
        <Row title="Hourly watch" sub="Hunter and Squeeze strategies" value={`${s.hourly_watch.looks_today}`} valueSub="looks today" />
      </Card>
        </Spot>

      <View style={{ flexDirection: "row", gap: 12, paddingHorizontal: 4 }}>
        <Stat label="Started with" value={usd(s.start_value, 0)} />
        <Stat label="Paper value now" value={usd(s.paper_value)} />
        <Stat label="Change" value={pct(100 * (s.paper_value / s.start_value - 1))} color={pnlColor(s.paper_value - s.start_value)} />
      </View>

      <Spot id="home.activity">
      <Pressable onPress={() => setShowActivity(!showActivity)} style={{ flexDirection: "row", alignItems: "center", backgroundColor: C.card, borderColor: C.line,
        borderWidth: 1, borderRadius: 12, paddingHorizontal: 14, paddingVertical: 12 }}>
        <Text style={{ color: C.text, fontWeight: "700", fontSize: 15, flex: 1 }}>Activity</Text>
        <T small>{d.feed.length} in the last 3 days</T>
        <Text style={{ color: C.accent, fontWeight: "700", marginLeft: 10 }}>{showActivity || activityLit ? "Hide ⌃" : "Show ⌄"}</Text>
      </Pressable>
      {showActivity || activityLit ? (
      <Card>
        {feed.length === 0 ? <T dim>Nothing happened yet.</T> : null}
        {feed.map((it: any, i: number) => (
          <View key={i}>
            {i ? <Divider /> : null}
            <Pressable onPress={() => it.trade_id && router.push(`/trade/${it.trade_id}`)} delayLongPress={350}
              onLongPress={() => askAbout({ screen: "activity", label: `${it.title} (${it.time})`, coin: it.coin, id: it.trade_id, item: it }, `Explain this: ${it.title}`)} style={{ flexDirection: "row", gap: 12, paddingVertical: 11 }}>
              <View style={{ paddingTop: 6 }}><Dot color={KIND[it.kind]?.color ?? C.faint} /></View>
              <View style={{ flex: 1, gap: 2 }}>
                <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
                  <Text style={{ color: it.kind === "sell" && it.good != null ? pnlColor(it.good ? 1 : -1) : C.text, fontWeight: "600", fontSize: 15, flex: 1 }}>{it.title}</Text>
                  <Text style={{ color: C.faint, fontSize: 12 }}>{it.time}</Text>
                </View>
                <Text style={{ color: C.dim, fontSize: 13, lineHeight: 18 }}>{it.body}</Text>
              </View>
              {it.trade_id ? <Text style={{ color: C.faint, fontSize: 18, alignSelf: "center" }}>›</Text> : null}
            </Pressable>
          </View>
        ))}
        {d.feed.length > 8 ? <Text onPress={() => setAll(!all)} style={{ color: C.accent, fontWeight: "600", paddingTop: 6 }}>{all ? "Show less" : `Show all ${d.feed.length}`}</Text> : null}
      </Card>
      ) : null}
      </Spot>
    </Screen>
  );
}

// The full brief in a small window: closes with ✕ or a tap anywhere outside it.
function BriefPopup({ open, onClose, title, when, text }: { open: boolean; onClose: () => void; title: string; when: string; text: string }) {
  return (
    <Modal visible={open} transparent animationType="fade" onRequestClose={onClose}>
      <Pressable onPress={onClose} style={{ flex: 1, backgroundColor: "rgba(15,20,35,0.45)", justifyContent: "center", padding: 20 }}>
        <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 18, maxHeight: "75%", overflow: "hidden" }}>
          <View style={{ flexDirection: "row", alignItems: "center", paddingHorizontal: 16, paddingTop: 14, paddingBottom: 8 }}>
            <View style={{ flex: 1 }}>
              <Text style={{ color: C.text, fontWeight: "700", fontSize: 17 }}>{title}</Text>
              {when ? <Text style={{ color: C.faint, fontSize: 12 }}>{when}</Text> : null}
            </View>
            <Pressable onPress={onClose} hitSlop={14} accessibilityLabel="Close"
              style={{ width: 30, height: 30, borderRadius: 15, backgroundColor: C.card2, alignItems: "center", justifyContent: "center" }}>
              <Text style={{ color: C.text, fontSize: 15, fontWeight: "700" }}>✕</Text>
            </Pressable>
          </View>
          <ScrollView contentContainerStyle={{ paddingHorizontal: 16, paddingBottom: 18 }}>
            <Text style={{ color: C.text, fontSize: 15, lineHeight: 23 }}>{text}</Text>
          </ScrollView>
        </Pressable>
      </Pressable>
    </Modal>
  );
}
