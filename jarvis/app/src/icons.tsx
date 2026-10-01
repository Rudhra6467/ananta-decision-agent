// Tab icons drawn with react-native-svg (no icon font needed).
import Svg, { Circle, Path, Rect } from "react-native-svg";

type P = { color: string; size?: number };
const S = ({ size = 24, children }: { size?: number; children: React.ReactNode }) => (
  <Svg width={size} height={size} viewBox="0 0 24 24" fill="none">{children}</Svg>
);
export const HomeIcon = ({ color, size }: P) => (
  <S size={size}><Path d="M3 10.5 12 3l9 7.5V20a1 1 0 0 1-1 1h-5v-6H9v6H4a1 1 0 0 1-1-1v-9.5Z" stroke={color} strokeWidth={1.8} strokeLinejoin="round" /></S>
);
export const PieIcon = ({ color, size }: P) => (
  <S size={size}><Path d="M12 3v9h9A9 9 0 1 1 12 3Z" stroke={color} strokeWidth={1.8} strokeLinejoin="round" /><Path d="M15 3.5A9 9 0 0 1 20.5 9H15V3.5Z" stroke={color} strokeWidth={1.8} strokeLinejoin="round" /></S>
);
export const ChatIcon = ({ color, size }: P) => (
  <S size={size}><Path d="M4 5h16v11H9l-5 4V5Z" stroke={color} strokeWidth={1.8} strokeLinejoin="round" /><Circle cx={9} cy={10.5} r={1} fill={color} /><Circle cx={12} cy={10.5} r={1} fill={color} /><Circle cx={15} cy={10.5} r={1} fill={color} /></S>
);
export const FlaskIcon = ({ color, size }: P) => (
  <S size={size}><Path d="M9 3h6M10 3v6l-5.5 9.5A1.7 1.7 0 0 0 6 21h12a1.7 1.7 0 0 0 1.5-2.5L14 9V3" stroke={color} strokeWidth={1.8} strokeLinejoin="round" /><Path d="M7.5 15h9" stroke={color} strokeWidth={1.8} /></S>
);
export const GaugeIcon = ({ color, size }: P) => (
  <S size={size}><Path d="M4 17a8 8 0 1 1 16 0" stroke={color} strokeWidth={1.8} strokeLinecap="round" /><Path d="m12 17 4-5" stroke={color} strokeWidth={1.8} strokeLinecap="round" /><Rect x={3} y={19} width={18} height={1.8} rx={0.9} fill={color} /></S>
);
export const ChartIcon = ({ color, size }: P) => (
  <S size={size}><Path d="M4 19h16" stroke={color} strokeWidth={1.8} strokeLinecap="round" /><Path d="M7 15V9M7 7V5M12 16v-5M12 9V6M17 14V8M17 6V4" stroke={color} strokeWidth={1.8} strokeLinecap="round" /><Rect x={5.5} y={9} width={3} height={6} rx={0.6} stroke={color} strokeWidth={1.4} /><Rect x={10.5} y={9} width={3} height={2} rx={0.6} fill={color} /><Rect x={15.5} y={8} width={3} height={6} rx={0.6} stroke={color} strokeWidth={1.4} /></S>
);
