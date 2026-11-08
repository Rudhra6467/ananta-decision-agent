// Ananta's mark. A bold, flat letter A in Ananta's yellow with a trishul standing behind it (7 Nov 2026, Madhav: "I want trisul
// (Indian)", replacing the Oct 15 trident): three leaf blades, the side arms sweeping out from a collar on the shaft, and a damru tied
// on the shaft between the A's legs. A faint lattice of nodes sits low at the sides, everything inside the double ring. The ring and the
// trishul are grey so the A carries the colour.
// Used by: the new look's top-right button (More), the orb in the new look's bottom bar (the "solo" form: no ring, no lattice, dark on
// gold), the Ananta button on classic Home, the drawer, the website's header and, rendered to PNG, the Home Screen icons in public/icons.
// scripts/make_icons.py reads the shapes below from this file, so the app and the icons can never drift apart: change them only here.
import Svg, { Circle, G, Line, Path } from "react-native-svg";
import { C } from "./theme";

type P = { color: string; size?: number; grey?: string; ink?: string; solo?: boolean };

// MARK-SHAPES-START (read by scripts/make_icons.py)
export const TRISHUL_ARMS = [
  "M47 64.6 C22 64.6 23.5 57 24.0 46 C24.4 39 26.4 35 28.0 31",
  "M53 64.6 C78 64.6 76.5 57 76 46 C75.6 39 73.6 35 72 31",
];
export const TRISHUL = [
  "M 50.0 9.5 C 53.1 13.2 55.4 16.4 54.8 19.6 C 54.3 21.8 52.5 23.2 51.3 25.0 L 48.7 25.0 C 47.5 23.2 45.7 21.8 45.2 19.6 C 44.6 16.4 46.9 13.2 50.0 9.5 Z",
  "M48.4 24 L51.6 24 L51.6 41 L48.4 41 Z",
  "M48.4 57 L51.6 57 L51.6 89 L48.4 89 Z",
  "M 25.8 16.5 C 28.7 19.8 30.9 22.7 30.8 26.0 C 30.7 28.2 29.6 29.8 29.0 31.7 L 27.0 31.9 C 25.9 30.3 24.4 29.1 23.7 27.0 C 22.8 23.9 24.0 20.4 25.8 16.5 Z",
  "M 74.2 16.5 C 76.0 20.4 77.2 23.9 76.3 27.0 C 75.6 29.1 74.1 30.3 73.0 31.9 L 71.0 31.7 C 70.4 29.8 69.3 28.2 69.2 26.0 C 69.1 22.7 71.3 19.8 74.2 16.5 Z",
  "M45.4 63.6 L54.6 63.6 L53.8 67.4 L46.2 67.4 Z",
  "M44.2 73 L55.8 73 L50.9 79 L49.1 79 Z",
  "M49.1 79 L50.9 79 L55.8 85 L44.2 85 Z",
];
export const LETTER_A = "M50 20 L79 82 L66 82 L60 68 L40 68 L34 82 L21 82 Z M50 41 L56 57 L44 57 Z";
export const NODES: [number, number][] = [[13, 62], [18, 57], [17.5, 68], [23, 64], [21, 74], [87, 62], [82, 57], [82.5, 68], [77, 64], [79, 74]];
export const EDGES: [number, number][] = [[0, 1], [0, 2], [1, 3], [2, 3], [2, 4], [5, 6], [5, 7], [6, 8], [7, 8], [7, 9]];
// MARK-SHAPES-END

export function AnantaMark({ color, size = 24, grey = C.faint, ink = C.bg, solo = false }: P) {   // every caller passes its theme's colours
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      {solo ? null : <Circle cx={50} cy={50} r={47} stroke={grey} strokeWidth={4} />}
      {solo ? null : <Circle cx={50} cy={50} r={42.5} stroke={color} strokeWidth={1.2} opacity={0.55} />}
      <G stroke={grey} strokeWidth={3.2} strokeLinecap="round" fill="none">
        {TRISHUL_ARMS.map((d, i) => <Path key={i} d={d} />)}
      </G>
      <G fill={grey}>
        {TRISHUL.map((d, i) => <Path key={i} d={d} />)}
      </G>
      {solo ? null : (
        <G stroke={color} strokeWidth={0.9} opacity={0.6} fill={color}>
          {EDGES.map(([a, b], i) => <Line key={i} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} />)}
          {NODES.map(([x, y], i) => <Circle key={i} cx={x} cy={y} r={1.7} />)}
        </G>
      )}
      <Path fillRule="evenodd" d={LETTER_A} fill={color} stroke={ink} strokeWidth={2.2} strokeLinejoin="round" />
    </Svg>
  );
}
