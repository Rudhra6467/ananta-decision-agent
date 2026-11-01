// Onboarding state (1 Nov 2026, Madhav: "when i invite someone, they should be onboarded and they should feel easy using and
// understanding it"; canvas "Your first run" and "An invited person"). Kept on this device: the owner's first run resumes at the
// step he left, "Skip for now" stops it showing again, and More › "Replay the first run" starts it over. An invited person sees
// the three hello steps once, before their first conversation (src/firstchat.tsx), which is unchanged.
import * as SecureStore from "expo-secure-store";

const OWNER = "ananta_onboard_owner";   // "0".."5" = the step to resume at; "done"; "skipped"
const HELLO = "ananta_hello_seen";      // "1" once an invited person has seen the hello steps

export async function ownerStep(): Promise<number | "done" | "skipped"> {
  try {
    const v = await SecureStore.getItemAsync(OWNER);
    if (v === "done" || v === "skipped") return v;
    const n = Number(v);
    return Number.isFinite(n) && v !== null ? Math.max(0, Math.min(5, n)) : 0;
  } catch { return 0; }
}
export async function setOwnerStep(v: number | "done" | "skipped") {
  try { await SecureStore.setItemAsync(OWNER, String(v)); } catch { /* the step still holds for this visit */ }
}
export async function ownerNeedsFirstRun(): Promise<boolean> {
  const s = await ownerStep();
  return s !== "done" && s !== "skipped";
}
export async function helloSeen(): Promise<boolean> {
  try { return (await SecureStore.getItemAsync(HELLO)) === "1"; } catch { return true; }
}
export async function setHelloSeen() {
  try { await SecureStore.setItemAsync(HELLO, "1"); } catch { /* */ }
}
