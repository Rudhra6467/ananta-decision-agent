// An invited person's hello (canvas 'An invited person', 1 Nov 2026): three steps before their first conversation - hello by name,
// what they can do here and what stays with Madhav, then the conversation that sets up their practice book and walks them round
// the screens in Ananta's voice (src/firstchat.tsx, unchanged). Seen once on this device (src/onboard.ts).
import { useEffect, useState } from "react";
import { View } from "react-native";
import { router } from "expo-router";
import { setHelloSeen } from "../src/onboard";
import { BigOrbArt, OnbFrame } from "../src/onboardframe";
import { Body, CheckIcon2, LockIcon, NCard } from "../src/newui";
import { C } from "../src/theme";
import { useMe } from "../src/visitor";
import { ScreenError } from "../src/safe";

export const ErrorBoundary = ScreenError;

const Can = ({ ok, children }: { ok: boolean; children: React.ReactNode }) => (
  <NCard pad={12}><View style={{ flexDirection: "row", alignItems: "center", gap: 10 }}>{ok ? <CheckIcon2 color={C.good} /> : <LockIcon color={C.dim} />}<Body style={{ flex: 1 }}>{children}</Body></View></NCard>
);

export default function Hello() {
  const me: any = useMe();
  const [step, setStep] = useState(0);
  useEffect(() => { if (me && !me.guest) router.replace("/" as any); }, [me]);   // the owner has his own first run (app/onboard.tsx)
  const name = String(me?.name || "").split(" ")[0];
  const common = { step, total: 3, topRight: "Invited by Madhav", onBack: step > 0 ? () => setStep(step - 1) : undefined };
  const start = async () => { await setHelloSeen(); router.replace("/(tabs)/ask" as any); };

  if (step === 0) return <OnbFrame {...common} title={name ? `Hello, ${name}.` : "Hello."}
    lines={["Madhav asked me to show you around. I'm Ananta, the trading assistant he built. Everything here is paper: nothing is ever placed, by anyone."]}
    extra={<BigOrbArt />} cta="Nice to meet you" onCta={() => setStep(1)} />;

  if (step === 1) return <OnbFrame {...common} title="What you can do here."
    lines={["Ask me anything about the market, the coins I watch, or what I've tested. I'll answer you by name.",
      "You get your own practice book, in paper money. Madhav's account stays his: if you ask for something only he decides, I'll say so kindly."]}
    extra={<View style={{ gap: 8 }}>
      <Can ok>Ask anything, by voice or text</Can>
      <Can ok>Practise with your own paper book</Can>
      <Can ok={false}>Only Madhav decides for his account: approvals, changes, his books</Can>
    </View>}
    cta="Got it" onCta={() => setStep(2)} />;

  return <OnbFrame {...common} title="A short tour, in my voice."
    lines={["Next I'll ask you a few short questions to set up your practice book, then walk you round the screens while you listen.", "Tap the orb any time to ask instead. You can stop halfway; it picks up where you left."]}
    cta="Let's start" onCta={start} />;
}
