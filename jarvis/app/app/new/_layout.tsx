// The redesign's five places (Madhav, 10 Nov 2026: "yes for all your recommendations"): Home · Markets · Ask (the orb) · Activity · More,
// on one floating bar (block 12 of the design canvas). The old new look's Today, Money, Proof and People moved down a level: Money is the
// account page opened from Home, Proof and People sit under More; nothing was removed (jarvis/service/places.py and jarvis/india/places.py
// write every place). Swiping left and right between the places stays (9 Nov, TestFlight).
import SwipeTabs from "expo-router/js-top-tabs";
import { useEffect, useRef, useState } from "react";
import { Animated, PanResponder, Pressable, Text, View } from "react-native";
import { soft, tap } from "../../src/haptics";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { C, useThemeVersion } from "../../src/theme";
import { Orb } from "../../src/newui";
import { Icon } from "../../src/place";
import { ScreenError } from "../../src/safe";
import { barAwake, endVoice, pressOrb, useBarSmall, useLiveVoice, useTyping, useVoiceStage } from "../../src/once";

export const ErrorBoundary = ScreenError;

const TABS: { name: string; label: string }[] = [
  { name: "home", label: "Home" }, { name: "markets", label: "Markets" }, { name: "ask", label: "" }, { name: "activity", label: "Activity" }, { name: "more", label: "More" },
];

// 14 Nov 2026 (Madhav, two Instagram screenshots: "how smoothly I was able to transit between the tabs ... I can select or swipe through to
// select, and the movement is so smooth; only when I stop on something the tab is selected ... and the size of it, a bit less than ours").
// A soft glass pill sits behind the current tab. Drag a finger along the bar and the pill follows it, the icon under it lights up, and a
// light tick marks each tab it passes; the tab is chosen only when the finger lifts. A page swipe moves the pill with the page. The orb
// in the middle is never chosen by a drag (Ask opens only from a tap on it, 14 Nov). The bar is 58 points tall (it was 64).
const BAR_H = 58;
const BAR_SMALL_H = 46;                                                  // 19 Nov 2026: the bar at rest (Instagram)
const PILL_INSET = 5;
const ROUTE_ORDER = ["home", "markets", "activity", "more", "ask"];          // the pager's order (app/new/_layout.tsx below)
const slotOf = (name: string) => TABS.findIndex((t) => t.name === name);
const ORB_SLOT = slotOf("ask");

function Bar({ state, navigation, position }: any) {
  useThemeVersion();
  const ins = useSafeAreaInsets();
  const active = state.routes[state.index]?.name;
  const typing = useTyping();
  const stage = useVoiceStage();
  const [w, setW] = useState(0);                                  // one slot's width
  const left = useRef(0);                                         // the bar's left edge on the screen
  const barRef = useRef<View>(null);
  const hx = useRef(new Animated.Value(0)).current;               // the pill's left edge in the bar
  const hop = useRef(new Animated.Value(active === "ask" ? 0 : 1)).current;
  const lift = useRef(new Animated.Value(1)).current;
  const dragging = useRef(false);
  const [hover, setHover] = useState<number | null>(null);
  const live = useLiveVoice();
  const smallNow = useBarSmall() && active !== "ask";              // 19 Nov: on Ask the bar stays full (the orb is the microphone there)
  const sz = useRef(new Animated.Value(0)).current;
  useEffect(() => { Animated.spring(sz, { toValue: smallNow ? 1 : 0, stiffness: 260, damping: 26, mass: 1, useNativeDriver: false }).start(); }, [smallNow]);
  useEffect(() => { barAwake(); }, [active]);                       // a new tab: full size, then small after a few quiet seconds
  const keep = useRef({ w, active, state, navigation, small: smallNow });
  keep.current = { w, active, state, navigation, small: smallNow };

  // the pill follows the pager: route index -> slot (Ask fades the pill out; the orb shows the microphone there)
  useEffect(() => {
    if (!position || !w) return;
    const slots = ROUTE_ORDER.map((n) => (n === "ask" ? slotOf("more") : slotOf(n)));
    const id = position.addListener(({ value }: { value: number }) => {
      if (dragging.current) return;
      const i = Math.max(0, Math.min(ROUTE_ORDER.length - 1, value));
      const a = Math.floor(i), b = Math.min(a + 1, ROUTE_ORDER.length - 1), f = i - a;
      hx.setValue((slots[a] + (slots[b] - slots[a]) * f) * w);
      hop.setValue(Math.max(0, Math.min(1, ROUTE_ORDER.length - 1 - i)));
    });
    return () => position.removeListener(id);
  }, [position, w]);
  useEffect(() => {                                               // a tap or a jump without a pager tick still lands the pill
    if (!w || dragging.current) return;
    if (active === "ask") { Animated.timing(hop, { toValue: 0, duration: 160, useNativeDriver: false }).start(); return; }
    Animated.parallel([Animated.spring(hx, { toValue: slotOf(active) * w, stiffness: 320, damping: 30, mass: 1, useNativeDriver: false }),
                       Animated.timing(hop, { toValue: 1, duration: 160, useNativeDriver: false })]).start();
  }, [active, w]);

  const go = (name: string) => {
    if (keep.current.small) { barAwake(); return; }                 // 19 Nov (Instagram): a tap on the small bar brings it back to full size first
    const { state: st, navigation: nav } = keep.current;
    const route = st.routes.find((r: any) => r.name === name);
    const ev = nav.emit({ type: "tabPress", target: route?.key, canPreventDefault: true });
    if (keep.current.active !== name && !ev.defaultPrevented) nav.navigate(name);
  };
  const slotAt = (x: number) => Math.max(0, Math.min(TABS.length - 1, Math.floor(x / Math.max(1, keep.current.w))));
  const pan = useRef(PanResponder.create({
    onMoveShouldSetPanResponderCapture: (_e, g) => Math.abs(g.dx) > 8 && Math.abs(g.dx) > Math.abs(g.dy) * 1.5,
    onPanResponderGrant: (_e, g) => {
      barAwake();
      dragging.current = true;
      hx.stopAnimation();
      Animated.parallel([Animated.spring(lift, { toValue: 1.08, stiffness: 400, damping: 22, useNativeDriver: false }),
                         Animated.timing(hop, { toValue: 1, duration: 120, useNativeDriver: false })]).start();
      setHover(slotAt(g.x0 - left.current));
    },
    onPanResponderMove: (_e, g) => {
      const W = keep.current.w;
      const fx = g.moveX - left.current;
      hx.setValue(Math.max(0, Math.min((TABS.length - 1) * W, fx - W / 2)));
      const s = slotAt(fx);
      setHover((h) => { if (h !== s && s !== ORB_SLOT) soft(); return s; });
    },
    onPanResponderRelease: (_e, g) => {
      const W = keep.current.w;
      const fx = g.moveX - left.current;
      let s = slotAt(fx);
      if (s === ORB_SLOT) s = fx - s * W < W / 2 ? s - 1 : s + 1;   // the orb is never chosen by a drag: the nearer side wins
      dragging.current = false;
      setHover(null);
      Animated.parallel([Animated.spring(hx, { toValue: s * W, stiffness: 320, damping: 28, mass: 1, useNativeDriver: false }),
                         Animated.spring(lift, { toValue: 1, stiffness: 400, damping: 24, useNativeDriver: false })]).start();
      tap();
      go(TABS[s].name);
    },
    onPanResponderTerminate: () => {
      dragging.current = false;
      setHover(null);
      Animated.spring(lift, { toValue: 1, useNativeDriver: false }).start();
      const { active: a, w: W } = keep.current;
      if (a !== "ask") Animated.spring(hx, { toValue: slotOf(a) * W, useNativeDriver: false }).start();
    },
    onPanResponderTerminationRequest: () => false,
  })).current;

  if ((typing || stage) && active === "ask") return null;  // 3 Nov: while he types in Ask the bar steps aside; 12 Nov: and on the big voice screen
  const lit = (i: number) => (hover !== null ? hover === i : active === TABS[i].name);
  const barH = sz.interpolate({ inputRange: [0, 1], outputRange: [BAR_H, BAR_SMALL_H] });
  const labelO = sz.interpolate({ inputRange: [0, 0.5], outputRange: [1, 0], extrapolate: "clamp" });
  const labelH = sz.interpolate({ inputRange: [0, 1], outputRange: [13, 0] });
  const orbS = sz.interpolate({ inputRange: [0, 1], outputRange: [1, 0.78] });
  const orbY = sz.interpolate({ inputRange: [0, 1], outputRange: [0, 8] });
  return (
    <View pointerEvents="box-none" style={{ position: "absolute", left: 0, right: 0, bottom: Math.max(ins.bottom, 12), alignItems: "center" }}>
      {live !== "off" && active !== "ask" ? (
        // 19 Nov 2026 (Madhav, YouTube's mini player): the voice is still on, so Ananta waits small at the bottom right; a tap goes back to Ask
        <View pointerEvents="box-none" style={{ position: "absolute", right: 16, bottom: BAR_H + 18, alignItems: "center", gap: 4 }}>
          <Orb size={56} mic label="Back to Ananta" onPress={() => { tap(); navigation.navigate("ask"); }} />
          <Pressable onPress={() => { tap(); endVoice(); }} accessibilityRole="button" accessibilityLabel="End voice" hitSlop={8}
            style={{ position: "absolute", top: -6, left: -6, width: 24, height: 24, borderRadius: 12, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, alignItems: "center", justifyContent: "center" }}>
            <Icon name="close" size={14} color={C.text} />
          </Pressable>
          <Text style={{ color: C.dim, fontSize: 11, fontWeight: "700" }}>{live === "speaking" ? "Speaking" : live === "thinking" ? "Thinking" : "Listening"}</Text>
        </View>
      ) : null}
      <Animated.View accessibilityRole="tablist" onTouchStart={() => barAwake()}
        style={{ width: sz.interpolate({ inputRange: [0, 1], outputRange: ["100%", "74%"] }) as any, maxWidth: 520, paddingHorizontal: 16 }}>
        <Animated.View ref={barRef as any} {...pan.panHandlers}
          onLayout={(e) => { setW(e.nativeEvent.layout.width / TABS.length); barRef.current?.measureInWindow((x) => { left.current = x; }); }}
          style={{ height: barH, borderRadius: BAR_H / 2, backgroundColor: C.card, borderWidth: 1, borderColor: C.line, flexDirection: "row", alignItems: "center",
            shadowColor: "#000", shadowOpacity: 0.25, shadowRadius: 16, shadowOffset: { width: 0, height: 6 }, elevation: 8 }}>
          {w ? (
            <Animated.View pointerEvents="none" style={{ position: "absolute", top: PILL_INSET - 1, height: BAR_H - 2 * PILL_INSET, width: w - 2 * PILL_INSET + 6, left: PILL_INSET - 3,
              borderRadius: (BAR_H - 2 * PILL_INSET) / 2, opacity: hop, transform: [{ translateX: hx }, { scale: lift }] }}>
              <View style={{ flex: 1, borderRadius: (BAR_H - 2 * PILL_INSET) / 2, backgroundColor: C.text, opacity: 0.1 }} />
              <View style={{ position: "absolute", left: 0, right: 0, top: 0, bottom: 0, borderRadius: (BAR_H - 2 * PILL_INSET) / 2, borderWidth: 1, borderColor: C.text, opacity: 0.08 }} />
            </Animated.View>
          ) : null}
          {TABS.map((t, i) => {
            if (!t.label) {
              return (
                <Animated.View key={t.name} style={{ flex: 1, alignItems: "center", marginTop: -24, transform: [{ translateY: orbY }, { scale: orbS }] }}>
                  {/* 7 Nov (Madhav): first press opens Ask; on Ask already, the same press starts the voice */}
                  <Orb size={54} mic={active === "ask"} label={active === "ask" ? "Talk to Ananta" : "Ask Ananta"}
                    onPress={() => { if (keep.current.small) { barAwake(); return; } if (active === "ask") pressOrb(); else navigation.navigate("ask"); }} />
                </Animated.View>
              );
            }
            const on = lit(i);
            const col = on ? C.text : C.dim;
            return (
              <Pressable key={t.name} accessibilityRole="tab" accessibilityLabel={t.label} accessibilityState={{ selected: active === t.name }}
                onPress={() => go(t.name)} style={{ flex: 1, alignItems: "center", justifyContent: "center", gap: 1, minHeight: 46 }}>
                <Icon name={t.name} size={22} color={col} />
                <Animated.Text style={{ color: col, fontSize: 10.5, lineHeight: 13, fontWeight: "700", opacity: labelO, height: labelH }}>{t.label}</Animated.Text>
              </Pressable>
            );
          })}
        </Animated.View>
      </Animated.View>
    </View>
  );
}

// 14 Nov 2026 (Madhav: "while moving between tabs with side swipes it should not show the Ananta voice tab; swiping right from Markets goes
// directly to Activity and back; the Ananta tab only opens from its symbol"). The pages a finger moves through are Home · Markets · Activity ·
// More, in the bar's order; Ask sits after More, out of the swipe path, and is opened only by the orb (or a link or the voice). It stays a tab,
// so once opened it stays alive behind the others (the voice loop, the conversation, the answer that moves the app while it speaks).
// A pager only stops at its ends, so on More (the page before Ask) and on Ask the pager's own swipe is off: on More a swipe right still goes
// back to Activity (src/moreswipe.tsx), a swipe left goes nowhere; Ask is left from the bar.
const NO_PAGER_SWIPE = ["more", "ask"];

export default function NewLayout() {
  useThemeVersion();
  return (
    <SwipeTabs tabBarPosition="bottom" initialRouteName="home" tabBar={(p: any) => <Bar {...p} />}
      screenOptions={({ route }: any) => ({ lazy: true, swipeEnabled: !NO_PAGER_SWIPE.includes(route.name), animationEnabled: true, sceneStyle: { backgroundColor: C.bg } }) as any}>
      <SwipeTabs.Screen name="home" />
      <SwipeTabs.Screen name="markets" />
      <SwipeTabs.Screen name="activity" />
      <SwipeTabs.Screen name="more" />
      <SwipeTabs.Screen name="ask" />
    </SwipeTabs>
  );
}
