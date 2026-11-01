// The owner's first run (canvas 'Your first run', 1 Nov 2026): six steps - who Ananta is, the paper pledge, your voice, Zerodha
// read-only, your people, the first morning. Resumes at the step left (src/onboard.ts); "Skip for now" stops it showing again;
// More › "Replay the first run" starts it over. Read-only: each step shows what is already set up (/v3/onboard/owner) and links
// to the screen that changes it (Teach my voice, People). Zerodha is never connected from here: the morning sign-in does that, and
// Ananta has no order path (the India leakcheck guards it).
import { useCallback, useEffect, useState } from "react";
import { Text, View } from "react-native";
import { router, useFocusEffect } from "expo-router";
import { api } from "../src/api";
import { newHome } from "../src/look";
import { getMarket } from "../src/market";
import { ownerStep, setOwnerStep } from "../src/onboard";
import { BigOrbArt, OnbFrame } from "../src/onboardframe";
import { Body, CheckIcon2, G, LockIcon, Meta, NCard, TY } from "../src/newui";
import { C } from "../src/theme";
import { ScreenError } from "../src/safe";

export const ErrorBoundary = ScreenError;
const TOTAL = 6;

type Owner = { voice?: { enrolled: boolean | null; when?: string | null }; zerodha?: { connected: boolean | null; until?: string | null };
  people?: { name: string; relation: string }[]; morning?: { words: string } };

const Row = ({ ok, children }: { ok: boolean | null | undefined; children: React.ReactNode }) => (
  <View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>
    {ok ? <CheckIcon2 color={C.good} /> : <LockIcon color={C.dim} />}
    <Body style={{ flex: 1 }}>{children}</Body>
  </View>
);
const Pill = ({ label }: { label: string }) => (
  <View style={{ backgroundColor: C.card2, borderRadius: 999, paddingHorizontal: 12, paddingVertical: 6 }}><Text style={[TY.meta, { color: C.text }]}>{label}</Text></View>
);

export default function Onboard() {
  const [step, setStep] = useState<number | null>(null);
  const [o, setO] = useState<Owner>({});
  useEffect(() => { ownerStep().then((s) => setStep(typeof s === "number" ? s : 0)); }, []);
  const load = useCallback(() => { api<Owner>("/v3/onboard/owner", undefined, 20000, true).then(setO).catch(() => {}); }, []);
  useFocusEffect(load);                                   // back from Teach my voice or People: show what changed
  const go = (n: number) => { setStep(n); setOwnerStep(n); };
  const leave = async (how: "done" | "skipped") => { await setOwnerStep(how); router.replace((getMarket() ? newHome : "/market") as any); };
  if (step == null) return <View style={{ flex: 1, backgroundColor: C.bg }} />;
  const common = { step, total: TOTAL, topRight: step < TOTAL - 1 ? "Skip for now" : undefined, onTopRight: () => leave("skipped"),
    onBack: step > 0 ? () => go(step - 1) : undefined };
  const v = o.voice, z = o.zerodha, ppl = o.people || [];

  if (step === 0) return <OnbFrame {...common} title="I'm Ananta."
    lines={["I watch the Indian market and crypto for you, do the homework before you walk in, and speak when you ask.", "This takes about three minutes. Stop any time; it picks up where you left."]}
    extra={<BigOrbArt />} cta="Let's begin" onCta={() => go(1)} />;

  if (step === 1) return <OnbFrame {...common} title="What I do, and what I never do."
    lines={["Every evening I re-rate your holdings, write a cut list and run the replacements on paper. Every morning I tell you the plan. In crypto I run a $500 book at real NDAX prices.",
      "I never place, change or close a real trade. Nothing is placed from chat, by anyone. Every book is paper until you decide otherwise, in person, after the proof."]}
    extra={<NCard pad={14}><View style={{ flexDirection: "row", alignItems: "center", gap: 12 }}><LockIcon color={G.gold()} /><Body style={{ flex: 1 }}>Paper only. Said once, here, and kept.</Body></View></NCard>}
    cta="I understand" onCta={() => go(2)} />;

  if (step === 2) return <OnbFrame {...common} title={v?.enrolled ? "I know your voice." : "Teach me your voice."}
    lines={v?.enrolled
      ? [`You taught me${v.when ? ` on ${fmt(v.when)}` : ""}. When it's you, you can decide; anyone else gets a greeting by name, not your account.`]
      : ["Read six short sentences so I know when it's you, even on a noisy line. Anyone else gets a greeting, not your account.", "It takes about a minute, and the voice print never leaves your Mac."]}
    extra={<NCard pad={14}><Row ok={v?.enrolled}>{v?.enrolled ? "Voice taught" : v?.enrolled === false ? "Not taught yet" : "Checking…"}</Row></NCard>}
    cta={v?.enrolled ? "Continue" : "Teach my voice"} onCta={() => (v?.enrolled ? go(3) : router.push("/voiceid" as any))}
    secondary={v?.enrolled ? "Teach it again" : "Do this later"} onSecondary={() => (v?.enrolled ? router.push("/voiceid" as any) : go(3))} />;

  if (step === 3) return <OnbFrame {...common} title="Zerodha, read-only."
    lines={["I read your holdings and funds once a day to rate them. I cannot place orders: there is no order path anywhere in Ananta, and a check on every change makes sure none is added.",
      z?.connected ? `Connected now${z.until ? `, good until ${z.until}` : ""}. The sign-in renews itself every morning before the open.` : z?.connected === false
        ? "Not connected at this moment. The sign-in renews itself every morning before the open; nothing for you to do here." : "Checking the connection…"]}
    extra={<NCard pad={14}><View style={{ gap: 10 }}>
      <Meta>What I see</Meta><Body>Holdings, average price, funds · once a day</Body>
      <Meta>What I never do</Meta><Body>Place, modify or cancel an order</Body>
    </View></NCard>}
    cta="Continue" onCta={() => go(4)} />;

  if (step === 4) return <OnbFrame {...common} title="Who else may talk to me?"
    lines={["Family and friends can ask me anything and I'll greet them by name; only you decide. To give someone their own sign-in, invite them from People."]}
    extra={<View style={{ flexDirection: "row", flexWrap: "wrap", gap: 8 }}>
      {ppl.slice(0, 10).map((p) => <Pill key={p.name} label={`${p.name} · ${p.relation}`} />)}
      {ppl.length > 10 ? <Pill label={`+${ppl.length - 10} more`} /> : null}
      {!ppl.length ? <Body dim>No one added yet.</Body> : null}
    </View>}
    cta="Continue" onCta={() => go(5)} secondary="Invite someone" onSecondary={() => router.push("/people" as any)} />;

  return <OnbFrame {...common} title="You're set."
    lines={[`Your next morning view arrives ${o.morning?.words || "at 08:30 Indian time on the next trading day"}: the market, the plan, what to watch. Crypto decides at each daily close.`,
      "Until then, ask me anything: tap the orb in the middle of the bar."]}
    extra={<View style={{ gap: 8 }}>
      <NCard pad={14}><View style={{ gap: 10 }}>
        <Meta>Set up</Meta>
        <Row ok={v?.enrolled}>{v?.enrolled ? "Voice taught" : "Voice not taught yet (People › Teach my voice)"}</Row>
        <Row ok={z?.connected}>{z?.connected ? "Zerodha read-only, connected" : "Zerodha read-only, connects each morning"}</Row>
        <Row ok={ppl.length > 0}>{ppl.length} {ppl.length === 1 ? "person knows" : "people know"} Ananta by name</Row>
      </View></NCard>
      <NCard pad={14}><Meta>Waiting for you</Meta><Body style={{ marginTop: 4 }}>Anything that needs your yes shows on Today.</Body></NCard>
    </View>}
    cta="Take me to Today" onCta={() => leave("done")} />;
}

function fmt(d: string) {
  try { return new Date(d + "T12:00:00").toLocaleDateString("en-GB", { weekday: "short", day: "numeric", month: "short" }).replace(",", ""); } catch { return d; }
}
