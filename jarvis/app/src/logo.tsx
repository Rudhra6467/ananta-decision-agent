// Ananta's mark (Madhav's own design, Oct 15): the letter A inside a double ring, its lattice of lines and nodes, and the faint
// trident behind it. Drawn here in the tab bar's line style (thin strokes, one colour) so it sits beside the tab icons; the full
// textured picture (jarvis/app/public/logo-hero-800.png and the Home Screen icons in public/icons) is the same design recoloured
// from copper to the Bat palette's yellow, used on the website's front page.
import Svg, { Circle, G, Line, Path } from "react-native-svg";

type P = { color: string; size?: number };

// lattice nodes in a 100 x 100 box: down each leg, along the bar, and the spine
const NODES: [number, number][] = [[44, 27], [38, 41], [32, 55], [26, 70], [20, 84], [56, 27], [62, 41], [68, 55], [74, 70], [80, 84],
  [34, 60], [42, 60], [50, 60], [58, 60], [66, 60], [50, 14], [50, 36], [50, 48]];
const EDGES: [number, number][] = [[0, 5], [1, 6], [1, 16], [6, 16], [16, 17], [2, 17], [7, 17], [2, 11], [7, 13], [17, 12], [3, 10], [8, 14], [3, 11], [8, 13], [0, 16], [5, 16]];

export function AnantaMark({ color, size = 24 }: P) {
  return (
    <Svg width={size} height={size} viewBox="0 0 100 100" fill="none">
      <Circle cx={50} cy={50} r={46} stroke={color} strokeWidth={4} opacity={0.9} />
      <Circle cx={50} cy={50} r={40.5} stroke={color} strokeWidth={1.4} opacity={0.5} />
      <G opacity={0.3} stroke={color} strokeWidth={1.6} strokeLinecap="round" strokeLinejoin="round">
        <Path d="M50 90 L50 66" />
        <Path d="M33 30 C25 40 27 54 38 62" />
        <Path d="M67 30 C75 40 73 54 62 62" />
        <Path d="M40 68 C44 75 56 75 60 68" />
      </G>
      <G opacity={0.55} stroke={color} strokeWidth={1.1} strokeLinecap="round">
        {EDGES.map(([a, b], i) => <Line key={i} x1={NODES[a][0]} y1={NODES[a][1]} x2={NODES[b][0]} y2={NODES[b][1]} />)}
      </G>
      <Path d="M50 14 L20 84 M50 14 L80 84 M34 60 L66 60" stroke={color} strokeWidth={4.5} strokeLinecap="round" strokeLinejoin="round" />
      {NODES.map(([x, y], i) => <Circle key={i} cx={x} cy={y} r={2.1} fill={color} />)}
    </Svg>
  );
}
