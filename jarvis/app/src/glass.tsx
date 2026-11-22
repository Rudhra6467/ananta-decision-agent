// The glass look (Madhav, 22 Nov 2026: "Good to lock. Let's build it into website and app", after the preview canvas
// "Ananta – Glass look preview"). The colours live in src/theme.ts (GLASS); this file draws the three things a colour cannot:
//   GlassBackdrop  the soft glow behind a page, so the translucent cards have something to catch (fixed; it does not scroll)
//   GlassBarFill   the tab bar's frosted glass: the browser's backdrop blur on the website, Apple's Liquid Glass on an iPhone that has it
//   GlassToggle    the round button beside the sun on More (on: bronze, the one accent)
// and watchReduceTransparency(), which keeps the look off while the phone's or the browser's Reduce Transparency is on.
import { AccessibilityInfo, Platform, Pressable, View } from "react-native";
import Svg, { Defs, Path, RadialGradient, Rect, Stop } from "react-native-svg";
import { C, glassHeldOff, glassOn, glassSwitch, setGlass, setReduceTransparency, themeName } from "./theme";
import * as Haptics from "./haptics";

// the glow: three soft pools of light, as on the canvas (light kept faint after "blue feels a bit strong"; dark brighter after
// "glass effect feels a bit less in dark titanium")
type Pool = { cx: string; cy: string; rx: string; ry: string; rgb: string; a: number };
const POOLS: Record<"light" | "bat", Pool[]> = {
  light: [
    { cx: "92%", cy: "6%", rx: "70%", ry: "36%", rgb: "rgb(59,110,220)", a: 0.11 },
    { cx: "-5%", cy: "46%", rx: "60%", ry: "32%", rgb: "rgb(70,100,190)", a: 0.07 },
    { cx: "85%", cy: "98%", rx: "75%", ry: "34%", rgb: "rgb(96,150,240)", a: 0.10 },
  ],
  bat: [
    { cx: "92%", cy: "4%", rx: "70%", ry: "38%", rgb: "rgb(176,190,212)", a: 0.26 },
    { cx: "-5%", cy: "48%", rx: "60%", ry: "34%", rgb: "rgb(128,142,164)", a: 0.20 },
    { cx: "90%", cy: "100%", rx: "75%", ry: "36%", rgb: "rgb(242,207,102)", a: 0.10 },
  ],
};

export function GlassBackdrop() {
  if (!glassOn()) return null;
  const t = themeName();
  const pools = POOLS[t];
  return (
    <View pointerEvents="none" style={{ position: "absolute", left: 0, top: 0, right: 0, bottom: 0, backgroundColor: C.bg }}>
      <Svg width="100%" height="100%" preserveAspectRatio="none">
        <Defs>
          {pools.map((p, i) => (
            <RadialGradient key={i} id={`glassPool_${t}_${i}`} cx={p.cx} cy={p.cy} rx={p.rx} ry={p.ry} fx={p.cx} fy={p.cy} gradientUnits="objectBoundingBox">
              <Stop offset="0" stopColor={p.rgb} stopOpacity={p.a} />
              <Stop offset="0.7" stopColor={p.rgb} stopOpacity={0} />
            </RadialGradient>
          ))}
        </Defs>
        {pools.map((_p, i) => <Rect key={i} x="0" y="0" width="100%" height="100%" fill={`url(#glassPool_${t}_${i})`} />)}
      </Svg>
    </View>
  );
}

// Apple's Liquid Glass (iOS 26 and later) through expo-glass-effect, already in the iPhone build (expo-router uses it). Loaded lazily
// so the website never touches it; anything older falls back to a near-solid fill (no blur there, so it must not show the page through).
let liquid: { GlassView: any; ok: boolean } | null = null;
function liquidGlass() {
  if (liquid) return liquid;
  liquid = { GlassView: null, ok: false };
  if (Platform.OS !== "ios") return liquid;
  try {
    const m = require("expo-glass-effect");
    liquid = { GlassView: m.GlassView, ok: !!m.isLiquidGlassAvailable?.() };
  } catch { /* not in this build */ }
  return liquid;
}

const FILL = {
  web: { light: "rgba(255,255,255,0.6)", bat: "rgba(34,36,41,0.55)" },        // over the browser's blur
  tint: { light: "rgba(255,255,255,0.35)", bat: "rgba(20,22,26,0.35)" },      // Liquid Glass's tint
  solid: { light: "rgba(255,255,255,0.92)", bat: "rgba(30,32,37,0.92)" },     // no blur available
};

export function GlassBarFill({ radius }: { radius: number }) {
  if (!glassOn()) return null;
  const t = themeName();
  const box = { position: "absolute" as const, left: 0, top: 0, right: 0, bottom: 0, borderRadius: radius, overflow: "hidden" as const };
  if (Platform.OS === "web") {
    return <View pointerEvents="none" style={[box, { backgroundColor: FILL.web[t], backdropFilter: "blur(30px) saturate(175%)" } as any]} />;
  }
  const lg = liquidGlass();
  if (lg.ok && lg.GlassView) {
    const GV = lg.GlassView;
    return <GV pointerEvents="none" style={box} glassEffectStyle="regular" tintColor={FILL.tint[t]} colorScheme={t === "bat" ? "dark" : "light"} />;
  }
  return <View pointerEvents="none" style={[box, { backgroundColor: FILL.solid[t] }]} />;
}

// A frosted panel's own background, for bars that float over the page (the tab bar). Off: the plain card colour as before.
export const barBackground = () => (glassOn() ? "transparent" : C.card);
export const barBorder = () => (glassOn() ? C.edge : C.line);

// the button beside the sun on More: a drop of liquid; bronze when on
export function GlassToggle({ onHeldOff }: { onHeldOff?: () => void }) {
  const on = glassSwitch();
  const press = () => {
    Haptics.tap();
    const next = !on;
    setGlass(next);
    if (next && glassHeldOff()) { onHeldOff?.(); return; }
    // the website starts again in the new surfaces, as the sun does (the phone app redraws in place)
    if (Platform.OS === "web" && typeof window !== "undefined") setTimeout(() => window.location.reload(), 120);
  };
  const col = on ? C.gold : C.text;
  return (
    <Pressable onPress={press} hitSlop={12} accessibilityRole="switch" accessibilityState={{ checked: on }}
      accessibilityLabel={on ? "Glass look on. Turn it off" : "Glass look off. Turn it on"}
      style={{ width: 34, height: 34, borderRadius: 17, alignItems: "center", justifyContent: "center", marginRight: 8,
        backgroundColor: on ? C.goldSoft : C.card2, borderWidth: 1, borderColor: on ? C.gold : C.line }}>
      <Svg width={17} height={17} viewBox="0 0 24 24" fill="none" stroke={col} strokeWidth={1.9} strokeLinecap="round" strokeLinejoin="round">
        <Path d="M12 2.8s6 6.2 6 11.2a6 6 0 0 1-12 0c0-5 6-11.2 6-11.2Z" />
        <Path d="M9.3 14.4a2.7 2.7 0 0 0 2.7 2.7" />
      </Svg>
    </Pressable>
  );
}

// Reduce Transparency (iPhone: Settings › Accessibility › Display & Text Size; browsers: prefers-reduced-transparency) holds the glass
// look off while it is on; the switch keeps its place and the look comes back when the setting is turned off.
let watching = false;
export function watchReduceTransparency() {
  if (watching) return;
  watching = true;
  if (Platform.OS === "web") {
    try {
      const mq = typeof window !== "undefined" && window.matchMedia ? window.matchMedia("(prefers-reduced-transparency: reduce)") : null;
      if (mq) { setReduceTransparency(mq.matches); mq.addEventListener?.("change", (e: any) => setReduceTransparency(!!e.matches)); }
    } catch { /* */ }
    return;
  }
  AccessibilityInfo.isReduceTransparencyEnabled?.().then((v) => setReduceTransparency(!!v)).catch(() => {});
  AccessibilityInfo.addEventListener?.("reduceTransparencyChanged" as any, (v: any) => setReduceTransparency(!!v));
}
