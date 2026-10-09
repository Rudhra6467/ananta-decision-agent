// A visitor's own account (Madhav, 2026-10-06): a new person sees only what is theirs. Their name, the coins they picked,
// their practice capital and their own trades. Nothing of Madhav's books or history.
// Setup order: name -> coins -> tour (their own tabs, skippable; last screen lists what they can do) -> capital -> ready -> trading.
import { useCallback, useEffect, useRef, useState } from "react";
import { Animated, Modal, Platform, Pressable, Text, TextInput, View } from "react-native";
import { router } from "expo-router";
import { api } from "./api";
import { askAbout, goTab } from "./context";
import { Spark } from "./charts";
import { Spot } from "./spotlight";
import { Big, Btn, Card, Divider, Line, Row, Screen, Section, Stat, T, pct, price, usd, usdSigned } from "./ui";
import { C, COIN_NAME, pnlColor } from "./theme";

// ---- shared "me" (one fetch, every screen sees the same answer) ----
type Me = { guest: boolean; name: string; stage?: string; profile?: any; coin_choices?: { coin: string; name: string }[]; capitals?: number[]; practice_note?: string } | null;
let me: Me = null;
const subs = new Set<() => void>();
export async function loadMe(): Promise<Me> {
  try { me = await api("/v3/me"); } catch { /* keep the last one */ }
  subs.forEach((f) => f());
  return me;
}
export function useMe(): Me {
  const [v, setV] = useState<Me>(me);
  useEffect(() => {
    const f = () => setV(me);
    subs.add(f);
    if (!me) loadMe();
    return () => { subs.delete(f); };
  }, []);
  return v;
}
export function clearMe() { me = null; subs.forEach((f) => f()); }
export async function setup(body: object) {
  me = await api("/v3/me/setup", body).then((r) => ({ ...(me as any), ...r, name: r?.profile?.name || (me as any)?.name }));
  subs.forEach((f) => f());
  return me;
}

// Where a signed-in person should be: a visitor who has not finished setup goes to the welcome steps.
export async function routeAfterSignIn() {
  const m = await loadMe();
  if (m?.guest && ["name", "coins", "capital"].includes(String(m.stage))) router.replace("/welcome");
  else if (m?.guest && m.stage === "tour") router.replace("/(tabs)/today");
  else router.replace("/(tabs)/today");
}

// ---- the confirmation pop-up (plan 2.6): "Order placed ✓" closes by itself after 2 seconds, or with its ✕ ----
type ToastT = { text: string; id: number } | null;
let toast: ToastT = null;
const tsubs = new Set<() => void>();
const tset = (t: ToastT) => { toast = t; tsubs.forEach((f) => f()); };
export function showToast(text: string, ms = 2000) {
  const id = Date.now();
  tset({ text, id });
  setTimeout(() => { if (toast?.id === id) tset(null); }, ms);
}
export function Toast() {
  const [t, setT] = useState<ToastT>(toast);
  useEffect(() => { const f = () => setT(toast); tsubs.add(f); return () => { tsubs.delete(f); }; }, []);
  if (!t) return null;
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", top: 0, bottom: 0, left: 0, right: 0, alignItems: "center", justifyContent: "center" }}>
      <View accessibilityRole="alert" style={{ backgroundColor: C.ink, borderRadius: 16, paddingLeft: 22, paddingRight: 40, paddingVertical: 16, maxWidth: 320,
        shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 12 }}>
        <Text style={{ color: C.onInk, fontSize: 17, fontWeight: "700", textAlign: "center" }}>{t.text}</Text>
        <Pressable onPress={() => tset(null)} hitSlop={10} accessibilityLabel="Close" style={{ position: "absolute", top: 6, right: 10, padding: 4 }}>
          <Text style={{ color: C.onInk, fontSize: 15, opacity: 0.7 }}>✕</Text>
        </Pressable>
      </View>
    </View>
  );
}

// ---- pick coins ----
export function CoinPicker({ value, onChange, choices }: { value: string[]; onChange: (v: string[]) => void; choices: { coin: string; name: string }[] }) {
  return (
    <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
      {choices.map((c) => {
        const on = value.includes(c.coin);
        return (
          <Pressable key={c.coin} onPress={() => onChange(on ? value.filter((x) => x !== c.coin) : [...value, c.coin])} accessibilityRole="checkbox"
            accessibilityState={{ checked: on }}
            style={{ width: "47%", flexGrow: 1, borderRadius: 12, borderWidth: 2, borderColor: on ? C.accent : C.line, backgroundColor: on ? C.accentSoft : C.card,
              paddingVertical: 12, paddingHorizontal: 12, flexDirection: "row", alignItems: "center", gap: 8 }}>
            <View style={{ width: 20, height: 20, borderRadius: 10, borderWidth: 2, borderColor: on ? C.accent : C.faint, backgroundColor: on ? C.accent : "transparent",
              alignItems: "center", justifyContent: "center" }}>
              {on ? <Text style={{ color: C.onInk, fontSize: 12, fontWeight: "800" }}>✓</Text> : null}
            </View>
            <View>
              <Text style={{ color: C.text, fontWeight: "700", fontSize: 15 }}>{c.name}</Text>
              <Text style={{ color: C.dim, fontSize: 12 }}>{c.coin}</Text>
            </View>
          </Pressable>
        );
      })}
    </View>
  );
}

// ---- the tour over their own tabs: Next / Skip; the last screen lists what they can do ----
const TOUR = [
  { path: "/(tabs)/today", title: "Home", text: "This is your Home. Your coins, your practice money and your trades show up here. It's empty because it's all yours: nothing has happened yet." },
  { path: "/(tabs)/watchlists", title: "Watchlists", text: "Watchlists shows the coins you picked: live price, today's move and the trend. Tap a coin for its chart and what Ananta sees in it." },
  { path: "/(tabs)/portfolio", title: "Books", text: "Books is your practice book. Next you add practice capital, then press Start trading. Until then nothing is bought or watched for you." },
  { path: "/(tabs)/ask", title: "Ask Ananta", text: "Ask Ananta anything. Type, tap the mic to dictate, or tap the wave and just talk. Ananta knows your coins and your book." },
];
export const CAN_DO = [
  "“Find me a trade”: Ananta looks at your coins and suggests one, with a plan",
  "“What's happening with Bitcoin today?”",
  "“Buy $100 of Solana with a stop 5% below”",
  "“Why would you buy, or not buy, Ethereum now?”",
  "“How is my book doing?”",
  "“Show me around”: Ananta walks you through any screen",
  "Tap the wave in Ask Ananta and talk instead of typing",
  "Long-press any coin or trade to ask Ananta about it",
];

export function OnboardTour() {
  const m = useMe();
  const [i, setI] = useState(0);
  const active = !!m?.guest && m.stage === "tour";
  useEffect(() => { if (active && i < TOUR.length) goTab(TOUR[i].path as any); }, [active, i]);
  if (!active) return null;
  const finish = async () => {
    await setup({ tour_done: true }).catch(() => {});
    router.replace("/welcome");                          // next: practice capital
  };
  if (i >= TOUR.length) {
    return (
      <Modal transparent animationType="fade" visible>
        <View style={{ flex: 1, backgroundColor: "rgba(15,20,35,0.5)", justifyContent: "center", padding: 18 }}>
          <View style={{ backgroundColor: C.card, borderRadius: 18, padding: 18, gap: 10, maxWidth: 520, width: "100%", alignSelf: "center" }}>
            <Text style={{ color: C.accent, fontSize: 11, fontWeight: "700", letterSpacing: 0.6 }}>LAST STEP OF THE TOUR</Text>
            <Text style={{ color: C.text, fontSize: 20, fontWeight: "700" }}>Things you can try</Text>
            {CAN_DO.map((x, k) => (
              <View key={k} style={{ flexDirection: "row", gap: 8 }}>
                <Text style={{ color: C.accent, fontWeight: "700" }}>•</Text>
                <Text style={{ color: C.text, fontSize: 14, lineHeight: 20, flex: 1 }}>{x}</Text>
              </View>
            ))}
            <View style={{ flexDirection: "row", gap: 10, marginTop: 6 }}>
              <View style={{ flex: 1 }}><Btn label="Back" kind="secondary" onPress={() => setI(TOUR.length - 1)} /></View>
              <View style={{ flex: 2 }}><Btn label="Got it · add my capital" onPress={finish} /></View>
            </View>
          </View>
        </View>
      </Modal>
    );
  }
  const st = TOUR[i];
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", left: 12, right: 12, bottom: 96 }}>
      <View style={{ backgroundColor: C.ink, borderRadius: 16, padding: 14, gap: 10, shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 10,
        maxWidth: 560, width: "100%", alignSelf: "center" }}>
        <Text style={{ color: C.inkDim, fontSize: 11, fontWeight: "700", letterSpacing: 0.6 }}>TOUR · {i + 1} OF {TOUR.length + 1} · {st.title.toUpperCase()}</Text>
        <Text style={{ color: C.onInk, fontSize: 15, lineHeight: 21 }}>{st.text}</Text>
        <View style={{ flexDirection: "row", gap: 10 }}>
          <Pressable onPress={() => setI(TOUR.length)} style={{ flex: 1, backgroundColor: C.inkBtn, borderRadius: 10, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.onInk, fontWeight: "700" }}>Skip tour</Text>
          </Pressable>
          <Pressable onPress={() => setI(i + 1)} style={{ flex: 1, backgroundColor: C.accent, borderRadius: 10, padding: 9, alignItems: "center" }}>
            <Text style={{ color: C.onInk, fontWeight: "700" }}>Next ›</Text>
          </Pressable>
        </View>
      </View>
    </View>
  );
}

// ---- Home ----
function hello(name?: string) {
  const h = new Date().getHours();
  return `${h < 12 ? "Morning" : h < 17 ? "Afternoon" : "Evening"}${name ? `, ${name}` : ""}`;
}

export function VisitorHome({ d, loading, reload }: { d: any; loading: boolean; reload: () => void }) {
  const b = d.book;
  const gain = b ? b.equity - b.start : 0;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <View style={{ gap: 2 }}>
        <T dim small>Your practice account · paper money</T>
        <Text style={{ color: C.text, fontSize: 24, fontWeight: "700", letterSpacing: -0.3 }}>{hello(d.name)}</Text>
      </View>
      {d.next && d.stage !== "tour" ? (
        <Card title="Next step" sub={d.stage === "ready" ? "Your capital is in. Choose how you want to trade." : "Finish setting up your account."}>
          <Btn label={d.next} onPress={() => (d.stage === "ready" ? goTab("/(tabs)/portfolio") : router.replace("/welcome"))} />
        </Card>
      ) : null}
      <Card>
        <T dim small>Your practice money</T>
        {b ? (
          <>
            <Text style={{ color: C.text, fontSize: 32, fontWeight: "700", letterSpacing: -0.6 }}>{usd(b.equity)}</Text>
            <Text style={{ color: pnlColor(gain), fontWeight: "600" }}>{usdSigned(gain)} ({pct(b.return_pct)}) since you started with {usd(b.start, 0)}</Text>
            <T small>Cash {usd(b.cash)} · {b.positions.length} open position{b.positions.length === 1 ? "" : "s"} · {b.fills.length} order{b.fills.length === 1 ? "" : "s"}</T>
          </>
        ) : <T>No capital added yet.</T>}
      </Card>
      <Section title="Your coins" right={<Text onPress={() => goTab("/(tabs)/watchlists")} style={{ color: C.accent, fontWeight: "600" }}>Watchlists ›</Text>} />
      <Card>
        {(d.coins ?? []).length === 0 ? <T dim>No coins picked yet.</T> : null}
        {(d.coins ?? []).map((c: any, i: number) => (
          <View key={c.coin}>
            {i ? <Divider /> : null}
            <CoinRow c={c} />
          </View>
        ))}
      </Card>
      <Section title="Your trades" />
      <Card>
        {!b || b.fills.length === 0 ? (
          <T dim>{d.started ? "No trades yet. Ask Ananta to find one, or place one yourself in Books." : "Nothing yet. Trading starts when you press Start trading in Books."}</T>
        ) : b.fills.slice(0, 6).map((f: any, i: number) => (
          <View key={f.id}>
            {i ? <Divider /> : null}
            <Line label={`${f.side === "BUY" ? "Bought" : "Sold"} ${COIN_NAME[f.coin] ?? f.coin}`} value={`${usd(f.usd)} @ ${price(f.px)}`}
              sub={new Date(f.t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })} />
          </View>
        ))}
      </Card>
      {d.started ? (
        <Btn label="Ask Ananta to find me a trade" onPress={() => openJarvisTrade()} />
      ) : null}
    </Screen>
  );
}

function CoinRow({ c }: { c: any }) {
  return (
    <Pressable onPress={() => router.push(`/coin/${c.coin}`)} delayLongPress={350}
      onLongPress={() => askAbout({ screen: "coin", coin: c.coin, label: `${c.coin} in my coins` }, `What is happening with ${COIN_NAME[c.coin] ?? c.coin}?`)}
      style={({ pressed }) => ({ flexDirection: "row", alignItems: "center", gap: 10, paddingVertical: 11, opacity: pressed ? 0.6 : 1 })}>
      <View style={{ flex: 1 }}>
        <Text style={{ color: C.text, fontSize: 16, fontWeight: "700" }}>{c.name ?? COIN_NAME[c.coin] ?? c.coin}</Text>
        <Text style={{ color: C.dim, fontSize: 12 }}>{c.coin}{c.trend_1h ? ` · 1h ${c.trend_1h}` : ""}{c.daily ? ` · ${c.daily}` : ""}</Text>
      </View>
      {c.spark?.length ? <Spark data={c.spark} color={pnlColor(c.day_pct)} /> : null}
      <View style={{ alignItems: "flex-end", minWidth: 86 }}>
        <Text style={{ color: C.text, fontSize: 15, fontWeight: "600" }}>{price(c.price)}</Text>
        <Text style={{ color: pnlColor(c.day_pct), fontSize: 12, fontWeight: "600" }}>{pct(c.day_pct)} today</Text>
      </View>
    </Pressable>
  );
}

// ---- Markets ----
export function VisitorMarkets({ d, loading, reload }: { d: any; loading: boolean; reload: () => void }) {
  const m = useMe();
  const [edit, setEdit] = useState(false);
  const [pick, setPick] = useState<string[]>([]);
  useEffect(() => { setPick(m?.profile?.coins ?? []); }, [m?.profile?.coins?.join(",")]);
  const save = async () => { await setup({ coins: pick }); setEdit(false); reload(); };
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Card>
        <T>{d.summary}</T>
        <Text onPress={() => setEdit(!edit)} style={{ color: C.accent, fontWeight: "600" }}>{edit ? "Close" : "Add or remove coins"}</Text>
        {edit ? (
          <View style={{ gap: 10, marginTop: 6 }}>
            <CoinPicker value={pick} onChange={setPick} choices={m?.coin_choices ?? []} />
            <Btn label={`Save · ${pick.length} coin${pick.length === 1 ? "" : "s"}`} onPress={save} />
          </View>
        ) : null}
      </Card>
      <Section title="Your coins" right={<T small>tap for chart · long-press to ask</T>} />
      <Card>
        {(d.coins ?? []).map((c: any, i: number) => (
          <View key={c.coin}>{i ? <Divider /> : null}<Spot id={`markets.coin:${c.coin}`}><CoinRow c={c} /></Spot></View>
        ))}
      </Card>
    </Screen>
  );
}

// ---- Books ----
export function openJarvisTrade() {
  goTab({ pathname: "/(tabs)/ask", params: { intro: "find_trade", t: String(Date.now()) } } as any);
}

export function VisitorBooks({ d, loading, reload }: { d: any; loading: boolean; reload: () => void }) {
  const [choose, setChoose] = useState(false);
  const [form, setForm] = useState(false);
  const start = async (method: "jarvis" | "myself") => {
    setChoose(false);
    await setup({ start_trading: true, method });
    reload();
    if (method === "jarvis") openJarvisTrade(); else setForm(true);
  };
  const b = d.book;
  if (!d.capital) {
    return (
      <Screen loading={loading} onRefresh={reload}>
        <Card title="Your practice book" sub="Add practice capital to begin. It's paper money: nothing real is spent.">
          {d.stage === "tour" ? <T dim>You'll add it right after the tour.</T> : <Btn label="Add practice capital" onPress={() => router.replace("/welcome")} />}
        </Card>
      </Screen>
    );
  }
  const gain = b.equity - b.start;
  return (
    <Screen loading={loading} onRefresh={reload}>
      <Spot id="mine.value"><Big label="Your practice book" value={usd(b.equity)} change={gain} changeLabel={`${usdSigned(gain)} (${pct(b.return_pct)}) since you started with ${usd(b.start, 0)}`} /></Spot>
      {!d.started ? (
        <Card title="Ready when you are" sub="Nothing is bought or watched for you until you start.">
          <Pressable onPress={() => setChoose(true)} style={({ pressed }) => ({ backgroundColor: C.good, borderRadius: 12, paddingVertical: 16, alignItems: "center", opacity: pressed ? 0.8 : 1 })}>
            <Text style={{ color: C.onInk, fontSize: 18, fontWeight: "800" }}>Start trading</Text>
          </Pressable>
        </Card>
      ) : (
        <>
          <View style={{ flexDirection: "row", gap: 12 }}>
            <Stat label="Cash" value={usd(b.cash)} />
            <Stat label="Closed P&L" value={usdSigned(b.realized)} color={pnlColor(b.realized)} />
            <Stat label="Costs" value={usd(b.costs)} />
          </View>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <View style={{ flex: 1 }}><Btn label="Ananta, find a trade" onPress={openJarvisTrade} /></View>
            <View style={{ flex: 1 }}><Btn label="Trade myself" kind="secondary" onPress={() => setForm(!form)} /></View>
          </View>
          {form ? <TradeForm coins={d.coins} positions={b.positions} onDone={() => { setForm(false); reload(); }} /> : null}
          <Section title="Positions" />
          <Card>
            {b.positions.length === 0 ? <T dim>No open positions yet.</T> : null}
            {b.positions.map((p: any, i: number) => (
              <View key={p.coin}>
                {i ? <Divider /> : null}
                <Spot id={`mine.position:${p.coin}`}><Row title={COIN_NAME[p.coin] ?? p.coin} sub={[p.stop ? `stop ${price(p.stop)}` : null, p.target ? `target ${price(p.target)}` : null].filter(Boolean).join(" · ") || "no stop set"}
                  value={usd(p.value)} valueSub={usdSigned(p.pnl)} valueSubColor={pnlColor(p.pnl)} onPress={() => router.push(`/coin/${p.coin}`)}
                  onLongPress={() => askAbout({ screen: "manual_position", coin: p.coin, label: `my ${p.coin} position` }, `How is my ${COIN_NAME[p.coin] ?? p.coin} position doing?`)} /></Spot>
              </View>
            ))}
          </Card>
          <Section title="Your orders" />
          <Card>
            {b.fills.length === 0 ? <T dim>No orders yet.</T> : null}
            {b.fills.map((f: any, i: number) => (
              <View key={f.id}>
                {i ? <Divider /> : null}
                <Line label={`${f.side === "BUY" ? "Bought" : "Sold"} ${COIN_NAME[f.coin] ?? f.coin} · ${new Date(f.t * 1000).toLocaleString(undefined, { month: "short", day: "numeric", hour: "numeric", minute: "2-digit" })}`}
                  value={`${usd(f.usd)} @ ${price(f.px)}`} sub={f.reason ? `“${f.reason}”` : f.trigger === "direct" ? "placed by you" : f.trigger !== "owner" ? `automatic: ${f.trigger}` : "via Ananta"} />
              </View>
            ))}
          </Card>
        </>
      )}
      <Modal transparent animationType="fade" visible={choose} onRequestClose={() => setChoose(false)}>
        <Pressable onPress={() => setChoose(false)} style={{ flex: 1, backgroundColor: "rgba(15,20,35,0.5)", justifyContent: "center", padding: 18 }}>
          <Pressable onPress={() => {}} style={{ backgroundColor: C.card, borderRadius: 18, padding: 18, gap: 12, maxWidth: 480, width: "100%", alignSelf: "center" }}>
            <Text style={{ color: C.text, fontSize: 20, fontWeight: "700" }}>How do you want to trade?</Text>
            <Pressable onPress={() => start("jarvis")} style={({ pressed }) => ({ borderWidth: 2, borderColor: C.accent, backgroundColor: C.accentSoft, borderRadius: 14, padding: 14, gap: 4, opacity: pressed ? 0.8 : 1 })}>
              <Text style={{ color: C.accent, fontWeight: "800", fontSize: 16 }}>Use Ananta  ·  recommended</Text>
              <Text style={{ color: C.text, fontSize: 13 }}>Ananta looks at your coins, suggests a trade with a plan, and places it when you confirm.</Text>
            </Pressable>
            <Pressable onPress={() => start("myself")} style={({ pressed }) => ({ borderWidth: 1, borderColor: C.line, borderRadius: 14, padding: 14, gap: 4, opacity: pressed ? 0.8 : 1 })}>
              <Text style={{ color: C.text, fontWeight: "800", fontSize: 16 }}>Trade myself</Text>
              <Text style={{ color: C.dim, fontSize: 13 }}>Pick a coin and an amount and place the order yourself.</Text>
            </Pressable>
            <Text onPress={() => setChoose(false)} style={{ color: C.dim, textAlign: "center", marginTop: 4 }}>Not now</Text>
          </Pressable>
        </Pressable>
      </Modal>
    </Screen>
  );
}

const AMOUNTS = [50, 100, 250, 500];
export function TradeForm({ coins, positions, onDone }: { coins: string[]; positions: any[]; onDone: () => void }) {
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [coin, setCoin] = useState(coins[0] ?? "BTC");
  const [amt, setAmt] = useState("100");
  const [stop, setStop] = useState("");
  const [pv, setPv] = useState<any>(null);
  const [msg, setMsg] = useState("");
  const held = positions.map((p) => p.coin);
  const list = side === "sell" ? held : coins;
  const body = () => {
    const stopPct = parseFloat(stop);
    return { side, coin, usd: side === "sell" && amt === "all" ? null : parseFloat(amt), stop: undefined as number | undefined, stopPct: isFinite(stopPct) ? stopPct : null };
  };
  const preview = async () => {
    setMsg("");
    try {
      const b = body();
      let st: number | undefined;
      if (side === "buy" && b.stopPct) {
        const p0 = await api("/v3/manual/order", { side, coin, usd: b.usd });
        st = Number((p0.price * (1 - b.stopPct / 100)).toPrecision(6));
      }
      setPv(await api("/v3/manual/order", { side, coin, usd: b.usd, stop: st }));
    } catch (e: any) { setPv(null); setMsg(e?.message ?? String(e)); }
  };
  const place = async () => {
    try {
      await api("/v3/manual/order", { ...pv.order, usd: pv.order.usd, confirm: true });
      showToast("Order placed ✓");
      setPv(null);
      onDone();
    } catch (e: any) { setMsg(e?.message ?? String(e)); }
  };
  return (
    <Card title={side === "buy" ? "Buy (paper)" : "Sell (paper)"}>
      <View style={{ flexDirection: "row", gap: 8 }}>
        {(["buy", "sell"] as const).map((s) => (
          <Pressable key={s} onPress={() => { setSide(s); setPv(null); if (s === "sell") { setCoin(held[0] ?? ""); setAmt("all"); } else { setCoin(coins[0] ?? "BTC"); setAmt("100"); } }}
            style={{ flex: 1, borderRadius: 8, paddingVertical: 8, alignItems: "center", backgroundColor: side === s ? C.text : C.card2 }}>
            <Text style={{ color: side === s ? C.onInk : C.text, fontWeight: "700" }}>{s === "buy" ? "Buy" : "Sell"}</Text>
          </Pressable>
        ))}
      </View>
      {list.length === 0 ? <T dim>Nothing to sell yet.</T> : (
        <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
          {list.map((c) => (
            <Pressable key={c} onPress={() => { setCoin(c); setPv(null); }} style={{ borderRadius: 999, paddingHorizontal: 12, paddingVertical: 7, borderWidth: 1,
              borderColor: coin === c ? C.accent : C.line, backgroundColor: coin === c ? C.accentSoft : C.card }}>
              <Text style={{ color: coin === c ? C.accent : C.text, fontWeight: "600" }}>{COIN_NAME[c] ?? c}</Text>
            </Pressable>
          ))}
        </View>
      )}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8, alignItems: "center" }}>
        {(side === "sell" ? ["all"] : AMOUNTS.map(String)).map((a) => (
          <Pressable key={a} onPress={() => { setAmt(a); setPv(null); }} style={{ borderRadius: 8, paddingHorizontal: 12, paddingVertical: 7, backgroundColor: amt === a ? C.text : C.card2 }}>
            <Text style={{ color: amt === a ? C.onInk : C.text, fontWeight: "600" }}>{a === "all" ? "All of it" : `$${a}`}</Text>
          </Pressable>
        ))}
        {side === "buy" ? (
          <TextInput value={AMOUNTS.map(String).includes(amt) ? "" : amt} onChangeText={(t) => { setAmt(t.replace(/[^0-9.]/g, "")); setPv(null); }} placeholder="Other $"
            keyboardType="decimal-pad" placeholderTextColor={C.faint}
            style={{ minWidth: 80, borderWidth: 1, borderColor: C.line, borderRadius: 8, paddingHorizontal: 10, paddingVertical: 6, color: C.text }} />
        ) : null}
      </View>
      {side === "buy" ? (
        <View style={{ flexDirection: "row", gap: 8, alignItems: "center" }}>
          <T small>Stop (optional): sell automatically if it falls</T>
          <TextInput value={stop} onChangeText={(t) => { setStop(t.replace(/[^0-9.]/g, "")); setPv(null); }} placeholder="5" keyboardType="decimal-pad" placeholderTextColor={C.faint}
            style={{ width: 54, borderWidth: 1, borderColor: C.line, borderRadius: 8, paddingHorizontal: 8, paddingVertical: 5, color: C.text }} />
          <T small>% below</T>
        </View>
      ) : null}
      {pv ? (
        <View style={{ backgroundColor: C.accentSoft, borderRadius: 10, padding: 10, gap: 8 }}>
          <Text style={{ color: C.text, fontSize: 14 }}>{pv.summary}</Text>
          <View style={{ flexDirection: "row", gap: 10 }}>
            <View style={{ flex: 1 }}><Btn label="Change" kind="secondary" onPress={() => setPv(null)} /></View>
            <View style={{ flex: 1 }}><Btn label="Place order" onPress={place} /></View>
          </View>
        </View>
      ) : <Btn label="Preview order" onPress={preview} />}
      {msg ? <Text style={{ color: C.bad }}>{msg}</Text> : null}
    </Card>
  );
}
