// Spotlight: Ananta points at things while it talks.
// <Spot id="home.value"> marks an element. focusSpot(id) scrolls the open screen to it and makes it glow.
// The open screen's scroll view registers itself (Screen in ui.tsx), so scroll("down") etc. move what the owner sees.
import React, { useEffect, useRef, useState } from "react";
import { Animated, ScrollView, View } from "react-native";
import { C } from "./theme";

type SpotRef = { view: View | null };
const spots = new Map<string, Set<SpotRef>>();
let active: string | null = null;
const subs = new Set<() => void>();
const emit = () => subs.forEach((f) => f());
let clearTimer: any = null;

type Scroller = { ref: React.RefObject<ScrollView | null>; offset: { y: number }; height: { h: number }; content: { h: number } };
let scroller: Scroller | null = null;
export const setScroller = (s: Scroller | null) => { scroller = s; };

export function activeSpot() { return active; }

// A spot Ananta is looking for right now (focusSpot is waiting for it): a folded section can open itself to show it.
let wanted: string | null = null;
export function useSpotWanted(ids: string[]): boolean {
  const [on, setOn] = useState(!!wanted && ids.includes(wanted));
  useEffect(() => {
    const f = () => setOn(!!wanted && ids.includes(wanted));
    subs.add(f);
    return () => { subs.delete(f); };
  }, [ids.join("|")]);
  return on;
}

export function useSpotActive(id?: string): boolean {
  const [on, setOn] = useState(!!id && active === id);
  useEffect(() => {
    if (!id) return;
    const f = () => setOn(active === id);
    subs.add(f);
    return () => { subs.delete(f); };
  }, [id]);
  return on;
}

export function Spot({ id, children, style }: { id: string; children: React.ReactNode; style?: any }) {
  const ref = useRef<View>(null);
  const [on, setOn] = useState(active === id);
  const glow = useRef(new Animated.Value(0)).current;
  useEffect(() => {
    const me: SpotRef = { view: null };
    me.view = ref.current;
    if (!spots.has(id)) spots.set(id, new Set());
    spots.get(id)!.add(me);
    const f = () => setOn(active === id);
    subs.add(f);
    return () => { spots.get(id)?.delete(me); subs.delete(f); };
  }, [id]);
  useEffect(() => {
    if (on) {
      Animated.loop(Animated.sequence([Animated.timing(glow, { toValue: 1, duration: 500, useNativeDriver: false }),
        Animated.timing(glow, { toValue: 0.55, duration: 500, useNativeDriver: false })])).start();
    } else {
      glow.stopAnimation();
      glow.setValue(0);
    }
  }, [on]);
  return (
    <Animated.View ref={ref as any} collapsable={false} style={[{ borderRadius: 16, borderWidth: 2,
      borderColor: glow.interpolate({ inputRange: [0, 1], outputRange: ["rgba(41,82,204,0)", C.accent] }),
      backgroundColor: glow.interpolate({ inputRange: [0, 1], outputRange: ["rgba(41,82,204,0)", "rgba(41,82,204,0.06)"] }),
      margin: -2 }, style]}>
      {children}
    </Animated.View>
  );
}

const sleep = (ms: number) => new Promise((r) => setTimeout(r, ms));

function measure(v: View | null): Promise<{ y: number; h: number } | null> {
  return new Promise((res) => {
    if (!v) return res(null);
    try { (v as any).measureInWindow((x: number, y: number, w: number, h: number) => res(w || h ? { y, h } : null)); } catch { res(null); }
  });
}

// Scroll the open screen so the spot is in view, then make it glow. Returns false if the spot is not on screen.
export async function focusSpot(id: string, holdMs = 0): Promise<boolean> {
  let target: SpotRef | null = null;
  wanted = id;
  emit();
  for (let i = 0; i < 30 && !target; i++) {                   // the screen (and its data) may still be loading: up to 3 s
    for (const s of spots.get(id) ?? []) {
      const m = await measure(s.view);
      if (m) { target = s; break; }
    }
    if (!target) await sleep(100);
  }
  wanted = null;
  if (!target) { emit(); return false; }
  const m = await measure(target.view);
  if (m && scroller?.ref.current) {
    const sv = await measure(scroller.ref.current as any);
    const top = sv?.y ?? 100, h = scroller.height.h || 600;
    if (m.y < top + 40 || m.y + Math.min(m.h, h * 0.6) > top + h - 40) {
      const y = Math.max(0, scroller.offset.y + (m.y - top) - 90);
      scroller.ref.current.scrollTo({ y, animated: true });
      await sleep(350);
    }
  }
  if (clearTimer) clearTimeout(clearTimer);
  active = id;
  emit();
  if (holdMs) clearTimer = setTimeout(() => { if (active === id) { active = null; emit(); } }, holdMs);
  return true;
}

export function clearSpot() {
  if (clearTimer) clearTimeout(clearTimer);
  active = null;
  emit();
}

export function scroll(dir: "up" | "down" | "top" | "bottom"): boolean {
  if (!scroller?.ref.current) return false;
  const h = scroller.height.h || 600, y = scroller.offset.y, max = Math.max(0, scroller.content.h - h);
  const to = dir === "top" ? 0 : dir === "bottom" ? max : dir === "down" ? Math.min(max, y + h * 0.75) : Math.max(0, y - h * 0.75);
  scroller.ref.current.scrollTo({ y: to, animated: true });
  return true;
}
