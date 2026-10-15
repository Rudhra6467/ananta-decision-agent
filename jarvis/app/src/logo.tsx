// Ananta's mark (Madhav's own design; the Oct 15 evening version after his review): a bold, flat letter A in Ananta's yellow, the
// trident standing behind it, a faint lattice of nodes at the sides, everything inside the double ring (nothing pokes out of the
// circle). The ring and the trident are grey so the A carries the colour. Used by the Ananta button on Home, the drawer, the
// website's header and, rendered to PNG, the Home Screen icons in public/icons (scripts/make_icons.py).
import Svg, { Circle, G, Line, Path } from "react-native-svg";

type P = { color: string; size?: number; grey?: string; ink?: string };

const NODES: [number, number][] = [[20, 46], [25, 38], [29, 52], [22, 60], [31, 64], [80, 46], [75, 38], [71, 52], [78, 60], [69, 64]];
const EDGES: [number, number][] = [[0, 1], [0, 2], [2, 3], [2, 4], [5, 6], [5, 7], [7, 8], [7, 9]];

export function AnantaMark({ color, size = 24, grey = "#5A5E66", ink = "#141518" }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <Circle cx={50} cy={50} r={47} stroke={grey} strokeWidth={4} />
      <Circle cx={50} cy={50} r={42.5} stroke={color} strokeWidth={1.2} opacity={0.55} />
      <G fill={grey}>
        <Path d="M47 66 L53 66 L52 24 L48 24 Z" />
        <Path d="M50 12 L55 24 L45 24 Z" />
        <Path d="M44 60 C32 52 30 36 37 20 L30 19 C24 36 27 56 41 66 Z" />
        <Path d="M56 60 C68 52 70 36 63 20 L70 19 C76 36 73 56 59 66 Z" />
        <Path d="M40 66 C44 72 56 72 60 66 L58 62 C55 66 45 66 42 62 Z" />
      </G>
      <G stroke={color} strokeWidth={0.9} opacity={0.6} fill={color}>
        {EDGES.map(([a, b], i) => <Line key={i} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} />)}
        {NODES.map(([x, y], i) => <Circle key={i} cx={x} cy={y} r={1.7} />)}
      </G>
      <Path fillRule="evenodd" d="M50 20 L79 82 L66 82 L60 68 L40 68 L34 82 L21 82 Z M50 41 L56 57 L44 57 Z" fill={color} stroke={ink} strokeWidth={2.2} strokeLinejoin="round" />
    </Svg>
  );
}
