// Where the owner is ("here": the screen actually open now) and what he pointed at ("about": an item he long-pressed).
// Ananta gets both with every question, so it never guesses which screen is showing.
import { useEffect, useState } from "react";
import { router } from "expo-router";
import * as Haptics from "./haptics";

export type ScreenCtx = { screen: string; label: string; coin?: string; id?: string; tab?: string; item?: any } | null;
let here: ScreenCtx = null;
let about: ScreenCtx = null;
let voiceLive = false;
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());

// every screen calls this when it comes into view
export function setScreen(c: ScreenCtx) {
  here = c;
  emit();
}
export const getScreen = () => here;
export const getAbout = () => about;
export function setAbout(c: ScreenCtx) {
  about = c;
  emit();
}
export function setVoiceLive(on: boolean) {
  voiceLive = on;
  emit();
}
export const isVoiceLive = () => voiceLive;

function useStore<T>(read: () => T): T {
  const [v, setV] = useState<T>(read());
  useEffect(() => {
    const f = () => setV(read());
    subs.add(f);
    f();
    return () => { subs.delete(f); };
  }, []);
  return v;
}
export const useHere = () => useStore(() => here);
export const useAbout = (): [ScreenCtx, (c: ScreenCtx) => void] => [useStore(() => about), setAbout];
export const useVoiceLive = () => useStore(() => voiceLive);

// kept for older screens: [about, setAbout]
export const useScreen = useAbout;

// Long-press anything: open Ananta with that item attached and a first question.
export function askAbout(ctx: NonNullable<ScreenCtx>, question?: string) {
  Haptics.tap();
  setAbout(ctx);
  router.push({ pathname: "/(tabs)/ask", params: { q: question ?? `Tell me about this: ${ctx.label}`, t: String(Date.now()) } });
}

// Tour state (shown as a caption bar over every screen while Ananta walks you through the app)
export type TourState = { active: boolean; i: number; n: number; text: string };
let tour: TourState = { active: false, i: 0, n: 0, text: "" };
let tourCmd: "" | "stop" | "next" = "";
export const setTour = (t: TourState) => { tour = t; emit(); };
export const useTour = () => useStore(() => tour);
export const tourCommand = (c: "" | "stop" | "next") => { tourCmd = c; };
export const takeTourCommand = () => { const c = tourCmd; tourCmd = ""; return c; };
