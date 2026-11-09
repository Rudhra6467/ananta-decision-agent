// Ananta's mark. A bold, flat letter A in Ananta's yellow with Shiva's trishul standing behind it, on a near-black disc inside a dark ring.
// 9 Nov 2026 (Madhav: "only A and trisul on the logo ... a bit more fierceful trisul (shiva trisul) ... the logo should feel dark and
// powerful"): the lattice of nodes at the sides is gone (at the size of a button it read as two flags); the trishul is forged steel, light
// at the tips and dark at the foot: a long spearhead that reaches into the ring, two flame blades with an outward barb on crescent arms,
// and the damru tied on the shaft between the A's legs. (7 Nov: the trishul replaced the Oct 15 trident.)
// The mark carries its own colours, so it is the same emblem everywhere: the new look's top-right button (More), the orb in the bottom
// bar, classic Home's Ananta button, the drawer, the website's header and, rendered to PNG, the app icon and the Home Screen icons.
// scripts/make_icons.py reads the shapes and colours below from this file, so the app and the icons can never drift: change them only here.
import { useId } from "react";
import Svg, { Circle, Defs, G, LinearGradient, Path, Stop } from "react-native-svg";

type P = { size?: number; color?: string };      // the A is Ananta's yellow in every theme (a blue or brown A on the dark disc is not the mark)

// MARK-SHAPES-START (read by scripts/make_icons.py)
export const TRISHUL = [
  "M50 3 C52.4 10.5 56.6 16.4 58 22.6 C55.4 24.4 53.6 26.6 52.8 30 L47.2 30 C46.4 26.6 44.6 24.4 42 22.6 C43.4 16.4 47.6 10.5 50 3 Z",
  "M45 67.5 C31 67.5 18 61 18 46.5 C18 40.6 19.4 35.6 21 31 L14.6 31.6 C19.4 27 21.4 20.6 22.4 10.5 C27.6 17.6 30.2 26.4 26.8 34.6 C24.6 39.6 23.4 43 23.4 46.8 C23.4 50.8 25.6 53.8 30 56.4 C34.6 59.4 40 61.6 45 61.6 Z",
  "M55 67.5 C69 67.5 82 61 82 46.5 C82 40.6 80.6 35.6 79 31 L85.4 31.6 C80.6 27 78.6 20.6 77.6 10.5 C72.4 17.6 69.8 26.4 73.2 34.6 C75.4 39.6 76.6 43 76.6 46.8 C76.6 50.8 74.4 53.8 70 56.4 C65.4 59.4 60 61.6 55 61.6 Z",
  "M47.7 57 L52.3 57 L52.3 87.5 L50 93.5 L47.7 87.5 Z",
  "M43.5 62.5 L56.5 62.5 L55 68 L45 68 Z",
  "M43.6 72.6 L56.4 72.6 L51 78.6 L49 78.6 Z",
  "M49 78.6 L51 78.6 L56.4 84.6 L43.6 84.6 Z"
];
export const LETTER_A = "M50 20 L79 82 L66 82 L60 68 L40 68 L34 82 L21 82 Z M50 41 L56 57 L44 57 Z";
export const MARK_COLORS = { "disc": "#08090B", "ring": "#2C2F35", "steelTop": "#A9AEB8", "steelMid": "#666A73", "steelBottom": "#4C5058", "gold": "#F2CF66" };
// MARK-SHAPES-END

export function AnantaMark({ color = MARK_COLORS.gold, size = 24 }: P) {
  const id = "am" + useId().replace(/[^a-zA-Z0-9]/g, "");          // one gradient per mark on the page (several marks can be on screen)
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <Defs>
        <LinearGradient id={id} gradientUnits="userSpaceOnUse" x1={0} y1={4} x2={0} y2={94}>
          <Stop offset={0} stopColor={MARK_COLORS.steelTop} />
          <Stop offset={0.5} stopColor={MARK_COLORS.steelMid} />
          <Stop offset={1} stopColor={MARK_COLORS.steelBottom} />
        </LinearGradient>
      </Defs>
      <Circle cx={50} cy={50} r={48} fill={MARK_COLORS.disc} />
      <Circle cx={50} cy={50} r={46.6} stroke={MARK_COLORS.ring} strokeWidth={4.4} />
      <Circle cx={50} cy={50} r={42.6} stroke={color} strokeWidth={1.1} opacity={0.6} />
      <G fill={`url(#${id})`}>
        {TRISHUL.map((d, i) => <Path key={i} d={d} />)}
      </G>
      <Path fillRule="evenodd" d={LETTER_A} fill={color} stroke={MARK_COLORS.disc} strokeWidth={2.4} strokeLinejoin="round" />
    </Svg>
  );
}
