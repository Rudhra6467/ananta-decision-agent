// The More page's tile icons (14 Nov 2026, Madhav: "the icons used in the More page are just okay; can we use other designs that make the
// page more beautiful. Just the icons: the sizing and placing look good"). Same box, same place: each tile now has its own colour and a
// duotone drawing (a soft filled shape under a crisp line) on a gently lit square. Names are the server's tile icons (jarvis/*/places.py);
// a name with no drawing here falls back to the plain line icon.
import { useId } from "react";
import Svg, { Circle, Defs, G, LinearGradient, Path, Rect, Stop } from "react-native-svg";

type Art = { color: string; fill?: string[]; line: string[]; dots?: [number, number, number][]; solid?: string[] };

const ART: Record<string, Art> = {
  // Studies: a flask with liquid and bubbles
  flask: { color: "#3CC6B5", fill: ["M7.2 14.2h9.6l2 3.4a1.7 1.7 0 0 1-1.5 2.6H6.7a1.7 1.7 0 0 1-1.5-2.6z"],
           line: ["M9.5 3.5h5", "M10.5 3.5v5.4L5.5 17.3a2 2 0 0 0 1.7 3h9.6a2 2 0 0 0 1.7-3l-5-8.4V3.5"], dots: [[10.8, 16.8, 0.9], [13.8, 15.6, 0.7]] },
  // the exam: a clipboard with a tick
  exam: { color: "#8C96FF", fill: ["M7.5 5h9a1.5 1.5 0 0 1 1.5 1.5v12.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 19V6.5A1.5 1.5 0 0 1 7.5 5z"],
          line: ["M7.5 5h9a1.5 1.5 0 0 1 1.5 1.5v12.5a1.5 1.5 0 0 1-1.5 1.5h-9A1.5 1.5 0 0 1 6 19V6.5A1.5 1.5 0 0 1 7.5 5z", "M9.5 3.5h5v3h-5z", "M9 13.2l2.2 2.2 4.3-4.4"] },
  // the night test: a crescent and two sparkles
  moon: { color: "#E9B85C", fill: ["M18.5 14.8A7.4 7.4 0 0 1 8.7 5a7.6 7.6 0 1 0 9.8 9.8z"], line: ["M18.5 14.8A7.4 7.4 0 0 1 8.7 5a7.6 7.6 0 1 0 9.8 9.8z"],
          solid: ["M17 3l.65 1.55L19.2 5.2l-1.55.65L17 7.4l-.65-1.55L14.8 5.2l1.55-.65z", "M20.2 9.2l.4.9.9.4-.9.4-.4.9-.4-.9-.9-.4.9-.4z"] },
  // the clocks: a stopwatch
  clock: { color: "#5DB2FF", fill: ["M12 6a7.5 7.5 0 1 1 0 15a7.5 7.5 0 1 1 0-15z"],
           line: ["M12 6a7.5 7.5 0 1 1 0 15a7.5 7.5 0 1 1 0-15z", "M12 13.5V9.6", "M12 13.5l2.7 1.7", "M10 3h4", "M12 3v3", "M18.2 6.8l1.4-1.4"] },
  // missed: a target with the arrow that went wide
  eye: { color: "#FF8C74", fill: ["M12 4a8 8 0 1 1 0 16a8 8 0 1 1 0-16z"],
         line: ["M12 4a8 8 0 1 1 0 16a8 8 0 1 1 0-16z", "M12 8.2a3.8 3.8 0 1 1 0 7.6a3.8 3.8 0 1 1 0-7.6z", "M13.6 10.4L20 4", "M17.2 4H20v2.8"], dots: [[12, 12, 1.1]] },
  // teachers: a graduation cap
  bars: { color: "#B58FFF", fill: ["M12 5L2.5 9.6 12 14.2l9.5-4.6z"],
          line: ["M12 5L2.5 9.6 12 14.2l9.5-4.6z", "M6.5 11.6v4.1c0 1.5 2.5 3.1 5.5 3.1s5.5-1.6 5.5-3.1v-4.1", "M21.5 9.6v5.2"], dots: [[21.5, 15.6, 1]] },
  // people: two people, the nearer one bolder
  people: { color: "#F27DB9", fill: ["M9.5 4.8a3.2 3.2 0 1 1 0 6.4a3.2 3.2 0 1 1 0-6.4z", "M16.2 6.2a2.5 2.5 0 1 1 0 5a2.5 2.5 0 1 1 0-5z"],
            line: ["M9.5 4.8a3.2 3.2 0 1 1 0 6.4a3.2 3.2 0 1 1 0-6.4z", "M3.5 19.5c.6-3.3 3-5.3 6-5.3s5.4 2 6 5.3", "M16.2 6.2a2.5 2.5 0 1 1 0 5a2.5 2.5 0 1 1 0-5z", "M16 13.8c2.6 0 4.4 1.8 4.9 4.6"] },
  // the open list: a card of ticked lines
  list: { color: "#5BD38F", fill: ["M7 4h10a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3z"],
          line: ["M7 4h10a3 3 0 0 1 3 3v10a3 3 0 0 1-3 3H7a3 3 0 0 1-3-3V7a3 3 0 0 1 3-3z", "M11 9.5h5.5", "M11 14.5h5.5", "M7.3 9.6l.9.9 1.6-1.8", "M7.3 14.6l.9.9 1.6-1.8"] },
  // the repair board: a wrench
  flag: { color: "#F6A04C", fill: ["M14.8 4.2a4.6 4.6 0 0 0-5.6 5.7l-5.6 5.6a1.9 1.9 0 0 0 2.7 2.7l5.6-5.6a4.6 4.6 0 0 0 5.7-5.6l-2.7 2.7-2.5-.3-.3-2.5z"],
          line: ["M14.8 4.2a4.6 4.6 0 0 0-5.6 5.7l-5.6 5.6a1.9 1.9 0 0 0 2.7 2.7l5.6-5.6a4.6 4.6 0 0 0 5.7-5.6l-2.7 2.7-2.5-.3-.3-2.5z"], dots: [[5.4, 17.5, 0.9]] },
  // phone notes: a phone with a notice dot
  phone: { color: "#6FA9FF", fill: ["M9 3h6a2.5 2.5 0 0 1 2.5 2.5v13A2.5 2.5 0 0 1 15 21H9a2.5 2.5 0 0 1-2.5-2.5v-13A2.5 2.5 0 0 1 9 3z"],
           line: ["M9 3h6a2.5 2.5 0 0 1 2.5 2.5v13A2.5 2.5 0 0 1 15 21H9a2.5 2.5 0 0 1-2.5-2.5v-13A2.5 2.5 0 0 1 9 3z", "M11 18h2"], dots: [[17.6, 5.4, 2.6]] },
  // appearance: half light, half dark
  sun: { color: "#F4C452", line: ["M12 4.5a7.5 7.5 0 1 1 0 15a7.5 7.5 0 1 1 0-15z", "M12 2v1.2", "M12 20.8V22", "M2 12h1.2", "M20.8 12H22"], solid: ["M12 4.5a7.5 7.5 0 0 1 0 15z"] },
  // all settings: a gear
  person: { color: "#AEB6C2", fill: ["M12 5.8a6.2 6.2 0 1 1 0 12.4a6.2 6.2 0 1 1 0-12.4z"],
            line: ["M12 5.8a6.2 6.2 0 1 1 0 12.4a6.2 6.2 0 1 1 0-12.4z", "M12 9.6a2.4 2.4 0 1 1 0 4.8a2.4 2.4 0 1 1 0-4.8z", "M12 2.6v3.2", "M12 18.2v3.2", "M2.6 12h3.2", "M18.2 12h3.2",
                   "M5.4 5.4l2.2 2.2", "M16.4 16.4l2.2 2.2", "M5.4 18.6l2.2-2.2", "M16.4 7.6l2.2-2.2"] },
};

export const hasArt = (name?: string) => !!name && !!ART[name];

export function TileArt({ name, size = 36 }: { name: string; size?: number }) {
  const a = ART[name];
  const id = "ta" + useId().replace(/[^a-zA-Z0-9]/g, "");
  if (!a) return null;
  const r = size * 0.3;
  return (
    <Svg width={size} height={size} viewBox={`0 0 ${size} ${size}`}>
      <Defs>
        <LinearGradient id={id} x1="0" y1="0" x2="1" y2="1">
          <Stop offset="0" stopColor={a.color} stopOpacity={0.30} />
          <Stop offset="1" stopColor={a.color} stopOpacity={0.08} />
        </LinearGradient>
      </Defs>
      <Rect x={0.5} y={0.5} width={size - 1} height={size - 1} rx={r} fill={`url(#${id})`} stroke={a.color} strokeOpacity={0.28} strokeWidth={1} />
      <G transform={`translate(${(size - 24 * 0.92) / 2} ${(size - 24 * 0.92) / 2}) scale(0.92)`}>
        {(a.fill || []).map((d, i) => <Path key={"f" + i} d={d} fill={a.color} fillOpacity={0.38} />)}
        {(a.solid || []).map((d, i) => <Path key={"s" + i} d={d} fill={a.color} />)}
        {(a.line || []).map((d, i) => <Path key={"l" + i} d={d} fill="none" stroke={a.color} strokeWidth={1.75} strokeLinecap="round" strokeLinejoin="round" />)}
        {(a.dots || []).map(([cx, cy, rr], i) => <Circle key={"d" + i} cx={cx} cy={cy} r={rr} fill={a.color} />)}
      </G>
    </Svg>
  );
}
