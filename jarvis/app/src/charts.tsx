// Small, dependency-light charts on react-native-svg.
import React, { useState } from "react";
import { LayoutChangeEvent, Text, View } from "react-native";
import Svg, { Circle, Defs, Line, LinearGradient, Path, Rect, Stop, Text as SvgText } from "react-native-svg";
import { C } from "./theme";

export type Series = { data: (number | null)[]; color: string; width?: number; dashed?: boolean; label?: string; fill?: boolean };
export type RefLine = { value: number; color: string; label: string; dashed?: boolean };

function useWidth(): [number, (e: LayoutChangeEvent) => void] {
  const [w, setW] = useState(0);
  return [w, (e) => setW(e.nativeEvent.layout.width)];
}

const fmtAxis = (x: number) => (Math.abs(x) >= 1000 ? x.toLocaleString(undefined, { maximumFractionDigits: 0 }) : Math.abs(x) >= 10 ? x.toFixed(2) : x.toPrecision(4));

export function LineChart({ series, height = 180, showAxis = true, refs = [], markers = [], xLabels }: {
  series: Series[]; height?: number; showAxis?: boolean; refs?: RefLine[]; markers?: { index: number; label: string; color?: string }[];
  xLabels?: [string, string];
}) {
  const [w, onLayout] = useWidth();
  const vals = series.flatMap((s) => s.data.filter((v): v is number => v != null && isFinite(v))).concat(refs.map((r) => r.value));
  const n = Math.max(0, ...series.map((s) => s.data.length));
  if (!vals.length || n < 2) return <View style={{ height: 60, justifyContent: "center" }} onLayout={onLayout}><Text style={{ color: C.dim }}>Not enough data yet.</Text></View>;
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (hi - lo < 1e-9) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08;
  lo -= pad; hi += pad;
  const right = refs.length ? 64 : 0;
  const pw = Math.max(1, w - right);
  const x = (i: number) => (i / (n - 1)) * pw;
  const y = (v: number) => height - ((v - lo) / (hi - lo)) * height;
  const path = (d: (number | null)[]) => {
    let p = "", pen = false;
    d.forEach((v, i) => {
      if (v == null || !isFinite(v)) { pen = false; return; }
      p += `${pen ? "L" : "M"}${x(i).toFixed(1)},${y(v).toFixed(1)} `;
      pen = true;
    });
    return p;
  };
  const area = (d: (number | null)[]) => {
    const idx = d.map((v, i) => (v != null && isFinite(v) ? i : -1)).filter((i) => i >= 0);
    if (idx.length < 2) return "";
    return `${path(d)} L${x(idx[idx.length - 1]).toFixed(1)},${height} L${x(idx[0]).toFixed(1)},${height} Z`;
  };
  return (
    <View onLayout={onLayout}>
      {w > 0 ? (
        <Svg width={w} height={height}>
          <Defs>
            {series.map((s, i) => (
              <LinearGradient key={i} id={`g${i}`} x1="0" y1="0" x2="0" y2="1">
                <Stop offset="0" stopColor={s.color} stopOpacity="0.16" />
                <Stop offset="1" stopColor={s.color} stopOpacity="0" />
              </LinearGradient>
            ))}
          </Defs>
          {series.map((s, i) => (s.fill ? <Path key={`a${i}`} d={area(s.data)} fill={`url(#g${i})`} /> : null))}
          {markers.map((m, i) => (
            <Line key={`m${i}`} x1={x(m.index)} x2={x(m.index)} y1={0} y2={height} stroke={m.color ?? C.faint} strokeDasharray="2,3" />
          ))}
          {refs.map((r, i) => (
            <React.Fragment key={`r${i}`}>
              <Line x1={0} x2={pw} y1={y(r.value)} y2={y(r.value)} stroke={r.color} strokeWidth={1.2} strokeDasharray={r.dashed === false ? undefined : "5,4"} />
              <Rect x={pw + 4} y={y(r.value) - 9} width={right - 6} height={18} rx={4} fill={r.color} />
              <SvgText x={pw + 4 + (right - 6) / 2} y={y(r.value) + 4} fontSize={10} fontWeight="700" fill="#FFFFFF" textAnchor="middle">{r.label}</SvgText>
            </React.Fragment>
          ))}
          {series.map((s, i) => (
            <Path key={i} d={path(s.data)} stroke={s.color} strokeWidth={s.width ?? 2} fill="none" strokeDasharray={s.dashed ? "4,4" : undefined} strokeLinejoin="round" />
          ))}
          {markers.map((m, i) => (
            <SvgText key={`mt${i}`} x={Math.min(Math.max(x(m.index), 14), pw - 14)} y={11} fontSize={10} fill={m.color ?? C.dim} textAnchor="middle">{m.label}</SvgText>
          ))}
        </Svg>
      ) : <View style={{ height }} />}
      {showAxis ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 6 }}>
          <Text style={{ color: C.faint, fontSize: 11 }}>{xLabels ? xLabels[0] : `low ${fmtAxis(lo + pad)}`}</Text>
          <View style={{ flexDirection: "row", gap: 10 }}>
            {series.filter((s) => s.label).map((s, i) => (
              <Text key={i} style={{ color: C.dim, fontSize: 11 }}><Text style={{ color: s.color }}>━</Text> {s.label}</Text>
            ))}
          </View>
          <Text style={{ color: C.faint, fontSize: 11 }}>{xLabels ? xLabels[1] : `high ${fmtAxis(hi - pad)}`}</Text>
        </View>
      ) : null}
    </View>
  );
}

export function Spark({ data, color, width = 64, height = 24 }: { data: number[]; color: string; width?: number; height?: number }) {
  if (data.length < 2) return <View style={{ width, height }} />;
  const lo = Math.min(...data), hi = Math.max(...data), r = hi - lo || 1;
  const d = data.map((v, i) => `${i ? "L" : "M"}${((i / (data.length - 1)) * width).toFixed(1)},${(height - ((v - lo) / r) * height).toFixed(1)}`).join(" ");
  return <Svg width={width} height={height}><Path d={d} stroke={color} strokeWidth={1.5} fill="none" /></Svg>;
}

// A thin progress bar (e.g. 3 of 4 conditions, 2 of 30 trades).
export function Progress({ value, of, color = C.accent }: { value: number; of: number; color?: string }) {
  const f = Math.max(0, Math.min(1, of ? value / of : 0));
  return (
    <View style={{ height: 6, backgroundColor: C.card2, borderRadius: 3, overflow: "hidden" }}>
      <View style={{ width: `${f * 100}%`, height: 6, backgroundColor: color, borderRadius: 3 }} />
    </View>
  );
}

// A ring split into parts (a pie with a hole), with a number in the middle: caught / seen / missed, the repair board.
export function Donut({ parts, size = 92, stroke = 13, center, sub }: {
  parts: { label: string; value: number; color: string }[]; size?: number; stroke?: number; center?: string; sub?: string;
}) {
  const r = (size - stroke) / 2, cx = size / 2, cy = size / 2;
  const live = parts.filter((p) => p.value > 0);
  const total = live.reduce((a, p) => a + p.value, 0);
  const pt = (a: number) => [cx + r * Math.sin(a), cy - r * Math.cos(a)];
  let a0 = 0;
  return (
    <View style={{ width: size, height: size, alignItems: "center", justifyContent: "center" }}>
      <Svg width={size} height={size} style={{ position: "absolute" }}>
        <Circle cx={cx} cy={cy} r={r} stroke={C.card2} strokeWidth={stroke} fill="none" />
        {live.length === 1 ? <Circle cx={cx} cy={cy} r={r} stroke={live[0].color} strokeWidth={stroke} fill="none" /> :
          live.map((p, i) => {
            const a1 = a0 + (p.value / total) * 2 * Math.PI;
            const gap = Math.min(0.04, (a1 - a0) / 4);
            const [x0, y0] = pt(a0 + gap), [x1, y1] = pt(a1 - gap);
            const d = `M${x0.toFixed(2)},${y0.toFixed(2)} A${r},${r} 0 ${a1 - a0 > Math.PI ? 1 : 0} 1 ${x1.toFixed(2)},${y1.toFixed(2)}`;
            a0 = a1;
            return <Path key={i} d={d} stroke={p.color} strokeWidth={stroke} fill="none" />;
          })}
      </Svg>
      {center != null ? <Text style={{ color: C.text, fontWeight: "800", fontSize: size > 80 ? 20 : 15 }}>{center}</Text> : null}
      {sub ? <Text style={{ color: C.faint, fontSize: 10 }}>{sub}</Text> : null}
    </View>
  );
}

// Bars that can go below zero, around a centre line, with one reference value marked (e.g. random entries).
export function SignedBars({ items, mark, fmt }: {
  items: { label: string; value: number | null; sub?: string; strong?: boolean }[]; mark?: { value: number; label: string } | null; fmt: (v: number) => string;
}) {
  const vals = items.map((i) => Math.abs(i.value ?? 0)).concat(mark ? [Math.abs(mark.value)] : []);
  const max = Math.max(1e-9, ...vals);
  const pos = (v: number) => 50 + (v / max) * 48;
  return (
    <View style={{ gap: 12 }}>
      {items.map((it, k) => {
        const v = it.value;
        const col = v == null ? C.faint : v >= 0 ? C.good : C.bad;
        return (
          <View key={k} style={{ gap: 4 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between", gap: 8 }}>
              <Text style={{ color: C.text, fontSize: 13, fontWeight: it.strong ? "700" : "400", flex: 1 }}>{it.label}</Text>
              <Text style={{ color: col, fontSize: 13, fontWeight: "700" }}>{v == null ? "–" : fmt(v)}</Text>
            </View>
            <View style={{ height: 8, backgroundColor: C.card2, borderRadius: 4 }}>
              {v != null ? (
                <View style={{ position: "absolute", top: 0, height: 8, borderRadius: 4, backgroundColor: col,
                  left: `${Math.min(50, pos(v))}%`, width: `${Math.max(1, Math.abs(pos(v) - 50))}%` }} />
              ) : null}
              <View style={{ position: "absolute", left: "50%", top: -2, width: 1, height: 12, backgroundColor: C.faint }} />
              {mark ? <View style={{ position: "absolute", left: `${pos(mark.value)}%`, top: -3, width: 2, height: 14, backgroundColor: C.text }} /> : null}
            </View>
            {it.sub ? <Text style={{ color: C.dim, fontSize: 11 }}>{it.sub}</Text> : null}
          </View>
        );
      })}
      {mark ? <Text style={{ color: C.dim, fontSize: 11 }}>▮ black mark = {mark.label} ({fmt(mark.value)}) · centre line = $0</Text> : null}
    </View>
  );
}

// One bar split into parts (holdings weights).
export function StackBar({ parts, height = 10 }: { parts: { label: string; value: number; color: string }[]; height?: number }) {
  const [w, onLayout] = useWidth();
  const total = parts.reduce((a, p) => a + Math.max(0, p.value), 0) || 1;
  let x = 0;
  return (
    <View onLayout={onLayout}>
      {w > 0 ? (
        <Svg width={w} height={height}>
          {parts.map((p, i) => {
            const pw = (Math.max(0, p.value) / total) * w;
            const r = <Rect key={i} x={x} y={0} width={Math.max(0, pw - 1.5)} height={height} fill={p.color} rx={2} />;
            x += pw;
            return r;
          })}
        </Svg>
      ) : <View style={{ height }} />}
    </View>
  );
}

// Horizontal bars, kept for small comparisons.
export function HBars({ items, fmt }: { items: { label: string; value: number; sub?: string; color?: string }[]; fmt: (v: number) => string }) {
  const max = Math.max(1e-9, ...items.map((i) => Math.abs(i.value)));
  return (
    <View style={{ gap: 10 }}>
      {items.map((it, k) => (
        <View key={k} style={{ gap: 4 }}>
          <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
            <Text style={{ color: C.text, fontSize: 13 }}>{it.label}</Text>
            <Text style={{ color: it.color ?? (it.value >= 0 ? C.good : C.bad), fontSize: 13, fontWeight: "600" }}>{fmt(it.value)}</Text>
          </View>
          <View style={{ height: 6, backgroundColor: C.card2, borderRadius: 3 }}>
            <View style={{ width: `${Math.max(2, (Math.abs(it.value) / max) * 100)}%`, height: 6, backgroundColor: it.color ?? (it.value >= 0 ? C.good : C.bad), borderRadius: 3 }} />
          </View>
          {it.sub ? <Text style={{ color: C.dim, fontSize: 11 }}>{it.sub}</Text> : null}
        </View>
      ))}
    </View>
  );
}

// Candles with 20/50 averages, horizontal levels (support / resistance / stop / target) and buy/sell marks.
export type Candle = { t: number; o: number; h: number; l: number; c: number; ema20?: number; ema50?: number };
export function CandleChart({ candles, height = 260, refs = [], marks = [], showAvg = true }: {
  candles: Candle[]; height?: number; refs?: RefLine[]; marks?: { t: number; kind: "buy" | "sell"; price?: number | null }[]; showAvg?: boolean;
}) {
  const [w, onLayout] = useWidth();
  if (candles.length < 2) return <View style={{ height: 60, justifyContent: "center" }} onLayout={onLayout}><Text style={{ color: C.dim }}>Not enough data yet.</Text></View>;
  const vals = candles.flatMap((k) => [k.h, k.l]).concat(refs.map((r) => r.value));
  let lo = Math.min(...vals), hi = Math.max(...vals);
  const pad = (hi - lo) * 0.06 || 1;
  lo -= pad; hi += pad;
  const right = 64;
  const pw = Math.max(1, w - right);
  const n = candles.length;
  const step = pw / n;
  const cw = Math.max(1, step * 0.62);
  const x = (i: number) => i * step + step / 2;
  const y = (v: number) => height - ((v - lo) / (hi - lo)) * height;
  const line = (key: "ema20" | "ema50") => candles.map((k, i) => (k[key] == null ? "" : `${i ? "L" : "M"}${x(i).toFixed(1)},${y(k[key] as number).toFixed(1)}`)).join(" ");
  const idxOf = (t: number) => { let best = 0; candles.forEach((k, i) => { if (k.t <= t) best = i; }); return best; };
  return (
    <View onLayout={onLayout}>
      {w > 0 ? (
        <Svg width={w} height={height + 14}>
          {[0.25, 0.5, 0.75].map((f) => <Line key={f} x1={0} x2={pw} y1={height * f} y2={height * f} stroke={C.line} strokeWidth={0.6} />)}
          {candles.map((k, i) => {
            const up = k.c >= k.o;
            const col = up ? C.good : C.bad;
            const top = y(Math.max(k.o, k.c)), bot = y(Math.min(k.o, k.c));
            return (
              <React.Fragment key={i}>
                <Line x1={x(i)} x2={x(i)} y1={y(k.h)} y2={y(k.l)} stroke={col} strokeWidth={1} />
                <Rect x={x(i) - cw / 2} y={top} width={cw} height={Math.max(1, bot - top)} fill={up ? C.card : col} stroke={col} strokeWidth={1} />
              </React.Fragment>
            );
          })}
          {showAvg ? <Path d={line("ema20")} stroke={C.accent} strokeWidth={1.4} fill="none" /> : null}
          {showAvg ? <Path d={line("ema50")} stroke={C.faint} strokeWidth={1.4} fill="none" strokeDasharray="4,3" /> : null}
          {refs.map((r, i) => (
            <React.Fragment key={`r${i}`}>
              <Line x1={0} x2={pw} y1={y(r.value)} y2={y(r.value)} stroke={r.color} strokeWidth={1.1} strokeDasharray={r.dashed === false ? undefined : "5,4"} />
              <Rect x={pw + 4} y={y(r.value) - 9} width={right - 6} height={18} rx={4} fill={r.color} />
              <SvgText x={pw + 4 + (right - 6) / 2} y={y(r.value) + 4} fontSize={10} fontWeight="700" fill="#FFFFFF" textAnchor="middle">{r.label}</SvgText>
            </React.Fragment>
          ))}
          {marks.map((m, i) => {
            const k = idxOf(m.t);
            const yy = m.kind === "buy" ? y(candles[k].l) + 12 : y(candles[k].h) - 6;
            return (
              <SvgText key={`m${i}`} x={x(k)} y={Math.min(height + 12, Math.max(10, yy))} fontSize={12} fontWeight="800" fill={m.kind === "buy" ? C.accent : C.text} textAnchor="middle">
                {m.kind === "buy" ? "▲" : "▼"}
              </SvgText>
            );
          })}
        </Svg>
      ) : <View style={{ height: height + 14 }} />}
    </View>
  );
}
