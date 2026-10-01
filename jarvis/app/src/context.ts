// What the owner is looking at, so Ananta can answer "is this one OK?" without being told which one.
import { useEffect, useState } from "react";
import { router } from "expo-router";
import * as Haptics from "./haptics";

export type ScreenCtx = { screen: string; label: string; coin?: string; id?: string; item?: any } | null;
let current: ScreenCtx = null;
const subs = new Set<(c: ScreenCtx) => void>();

export function setScreen(c: ScreenCtx) {
  current = c;
  subs.forEach((f) => f(c));
}
export const getScreen = () => current;
export function useScreen(): [ScreenCtx, (c: ScreenCtx) => void] {
  const [c, setC] = useState<ScreenCtx>(current);
  useEffect(() => {
    subs.add(setC);
    return () => { subs.delete(setC); };
  }, []);
  return [c, setScreen];
}

// Long-press anything: open Ananta with that item attached and a first question.
export function askAbout(ctx: NonNullable<ScreenCtx>, question?: string) {
  Haptics.tap();
  setScreen(ctx);
  router.push({ pathname: "/(tabs)/ask", params: { q: question ?? `Tell me about this: ${ctx.label}`, t: String(Date.now()) } });
}
