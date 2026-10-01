// Small, dependency-light charts on react-native-svg.
import React, { useState } from "react";
import { LayoutChangeEvent, Text, View } from "react-native";
import Svg, { Defs, Line, LinearGradient, Path, Rect, Stop, Text as SvgText } from "react-native-svg";
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
