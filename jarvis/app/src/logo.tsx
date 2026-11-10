// Ananta's mark. 10 Nov 2026 (Madhav, the redesign: "yes for all your recommendations", Icon A): forged bronze. The A comes first, chiselled
// into six facets lit from the top left; the ring second, steel outside and a thin bronze line inside; Shiva's trishul last, as a faint
// engraving behind the A (full mark only: at button size it vanishes, so the small mark leaves it out). Two cuts:
//   AnantaMark            the small mark: the Ask button, the header, the phone icon (Icon A: the small mark on black)
//   AnantaMark full       the full mark: the opening screen and sign-in
// The mark carries its own colours, so it is the same emblem everywhere. scripts/make_icons.py reads MARK2 below to draw the app icon, the
// splash and the website's icons, so the app and the icons can never drift: change the shapes only here. (Before 10 Nov: a flat yellow A
// with steel prongs; its shapes stay below for the classic screens' old imports.)
import { useId } from "react";
import Svg, { Circle, ClipPath, Defs, G, LinearGradient, Path, RadialGradient, Stop } from "react-native-svg";

// MARK2-START (read by scripts/make_icons.py; valid JSON)
export const MARK2 = {
  "facets": {
    "lo": "M50 12 L16 86 L23.2 86 L50 27.2 Z",
    "li": "M50 27.2 L23.2 86 L30.5 86 L37.2 70.5 L43.1 57.5 L50 42.5 Z",
    "ri": "M50 27.2 L50 42.5 L56.9 57.5 L62.8 70.5 L69.5 86 L76.8 86 Z",
    "ro": "M50 12 L50 27.2 L76.8 86 L84 86 Z",
    "bt": "M43.1 57.5 L56.9 57.5 L59.85 64 L40.15 64 Z",
    "bb": "M40.15 64 L59.85 64 L62.8 70.5 L37.2 70.5 Z"
  },
  "small": {"lo": "#EBC896", "li": "#8A5F36", "ri": "#C2925F", "ro": "#7A5330", "bt": "#D9B07C", "bb": "#5A3A1D", "edge": "#FFE9C4"},
  "full": {"lo": "#CDA271", "li": "#6F4A29", "ri": "#A67A4A", "ro": "#5E3E21", "bt": "#B88B59", "bb": "#452C15", "edge": "#F0D2A4"},
  "disc": ["#1A1C20", "#08090B"],
  "steel": ["#C3C8D1", "#6F747D", "#3A3D44"],
  "bronze": ["#E2BC8A", "#A67A4A", "#55371D"],
  "engraving": {"fill": "#1E2125", "stroke": "#4A4E57"},
  "blades": [
    "M50 3 C52.4 10.5 56.6 16.4 58 22.6 C55.4 24.4 53.6 26.6 52.8 30 L47.2 30 C46.4 26.6 44.6 24.4 42 22.6 C43.4 16.4 47.6 10.5 50 3 Z",
    "M45 67.5 C31 67.5 18 61 18 46.5 C18 40.6 19.4 35.6 21 31 L14.6 31.6 C19.4 27 21.4 20.6 22.4 10.5 C27.6 17.6 30.2 26.4 26.8 34.6 C24.6 39.6 23.4 43 23.4 46.8 C23.4 50.8 25.6 53.8 30 56.4 C34.6 59.4 40 61.6 45 61.6 Z",
    "M55 67.5 C69 67.5 82 61 82 46.5 C82 40.6 80.6 35.6 79 31 L85.4 31.6 C80.6 27 78.6 20.6 77.6 10.5 C72.4 17.6 69.8 26.4 73.2 34.6 C75.4 39.6 76.6 43 76.6 46.8 C76.6 50.8 74.4 53.8 70 56.4 C65.4 59.4 60 61.6 55 61.6 Z"
  ],
  "hull": "M0 0 H100 V100 H0 Z M50 22.4 L77.8 82.2 L22.2 82.2 Z",
  "a_transform": "translate(50 52.6) scale(0.8) translate(-50 -49)",
  "engraving_transform": "translate(50 48.5) scale(0.84) translate(-50 -50)",
  "icon_bg": "#08090B",
  "icon_scale": 0.86
};
// MARK2-END

export function AnantaMark({ size = 24, full = false }: { size?: number; full?: boolean; color?: string }) {
  const id = "am" + useId().replace(/[^a-zA-Z0-9]/g, "");          // one set of gradients per mark on the page
  const c = full ? MARK2.full : MARK2.small;
  const order = ["lo", "li", "ri", "ro", "bt", "bb"] as const;
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <Defs>
        <RadialGradient id={id + "d"} cx={50} cy={42} r={52} gradientUnits="userSpaceOnUse">
          <Stop offset={0} stopColor={MARK2.disc[0]} /><Stop offset={1} stopColor={MARK2.disc[1]} />
        </RadialGradient>
        <LinearGradient id={id + "s"} gradientUnits="userSpaceOnUse" x1={20} y1={4} x2={80} y2={96}>
          <Stop offset={0} stopColor={MARK2.steel[0]} /><Stop offset={0.45} stopColor={MARK2.steel[1]} /><Stop offset={1} stopColor={MARK2.steel[2]} />
        </LinearGradient>
        <LinearGradient id={id + "b"} gradientUnits="userSpaceOnUse" x1={20} y1={8} x2={80} y2={92}>
          <Stop offset={0} stopColor={MARK2.bronze[0]} /><Stop offset={0.5} stopColor={MARK2.bronze[1]} /><Stop offset={1} stopColor={MARK2.bronze[2]} />
        </LinearGradient>
        {full ? <ClipPath id={id + "h"}><Path d={MARK2.hull} clipRule="evenodd" /></ClipPath> : null}
      </Defs>
      <Circle cx={50} cy={50} r={48} fill={`url(#${id}d)`} />
      <Circle cx={50} cy={50} r={46.4} stroke={`url(#${id}s)`} strokeWidth={full ? 3 : 3.6} />
      <Circle cx={50} cy={50} r={43.2} stroke={`url(#${id}b)`} strokeWidth={full ? 1.1 : 1.6} />
      {full ? (
        <G clipPath={`url(#${id}h)`}>
          <G transform={MARK2.engraving_transform} fill={MARK2.engraving.fill} stroke={MARK2.engraving.stroke} strokeWidth={0.45} strokeLinejoin="round">
            {MARK2.blades.map((d, i) => <Path key={i} d={d} />)}
          </G>
        </G>
      ) : null}
      <G transform={MARK2.a_transform}>
        {order.map((k) => <Path key={k} d={MARK2.facets[k]} fill={c[k]} />)}
        <Path d="M50 12 L16 86" stroke={c.edge} strokeWidth={0.875} strokeLinecap="round" opacity={0.85} />
        <Path d="M50 27.2 L76.8 86" stroke={c.edge} strokeWidth={0.5} opacity={0.35} />
      </G>
    </Svg>
  );
}

// ---- before 10 Nov: the flat mark's shapes, kept for old imports (MARK_COLORS.disc is the orb's disc)
// MARK-SHAPES-START
export const TRISHUL = MARK2.blades;
export const LETTER_A = "M50 20 L79 82 L66 82 L60 68 L40 68 L34 82 L21 82 Z M50 41 L56 57 L44 57 Z";
export const MARK_COLORS = { "disc": "#08090B", "ring": "#2C2F35", "steelTop": "#A9AEB8", "steelMid": "#666A73", "steelBottom": "#4C5058", "gold": "#C2925F" };
// MARK-SHAPES-END
