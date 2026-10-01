// Small, dependency-light charts on react-native-svg.
import React, { useState } from "react";
import { LayoutChangeEvent, Text, View } from "react-native";
import Svg, { Line, Path, Rect } from "react-native-svg";
import { C } from "./theme";

export type Series = { data: (number | null)[]; color: string; width?: number; dashed?: boolean; label?: string };

function useWidth(): [number, (e: LayoutChangeEvent) => void] {
  const [w, setW] = useState(0);
  return [w, (e) => setW(e.nativeEvent.layout.width)];
}

const fmtAxis = (x: number) => (Math.abs(x) >= 1000 ? x.toLocaleString(undefined, { maximumFractionDigits: 0 }) : x.toPrecision(4));

export function LineChart({ series, height = 160, showAxis = true }: { series: Series[]; height?: number; showAxis?: boolean }) {
  const [w, onLayout] = useWidth();
  const vals = series.flatMap((s) => s.data.filter((v): v is number => v != null && isFinite(v)));
  const n = Math.max(0, ...series.map((s) => s.data.length));
  if (!vals.length || n < 2) return <View style={{ height }} onLayout={onLayout}><Text style={{ color: C.dim }}>Not enough data yet.</Text></View>;
  let lo = Math.min(...vals), hi = Math.max(...vals);
  if (hi - lo < 1e-9) { hi += 1; lo -= 1; }
  const pad = (hi - lo) * 0.08;
  lo -= pad; hi += pad;
  const x = (i: number) => (i / (n - 1)) * w;
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
  return (
    <View onLayout={onLayout}>
      {w > 0 ? (
        <Svg width={w} height={height}>
          <Line x1={0} x2={w} y1={height - 0.5} y2={height - 0.5} stroke={C.line} />
          {series.map((s, i) => (
            <Path key={i} d={path(s.data)} stroke={s.color} strokeWidth={s.width ?? 2} fill="none" strokeDasharray={s.dashed ? "4,4" : undefined} />
          ))}
        </Svg>
      ) : <View style={{ height }} />}
      {showAxis ? (
        <View style={{ flexDirection: "row", justifyContent: "space-between", marginTop: 4 }}>
          <Text style={{ color: C.dim, fontSize: 11 }}>low {fmtAxis(lo + pad)}</Text>
          <View style={{ flexDirection: "row", gap: 10 }}>
            {series.filter((s) => s.label).map((s, i) => (
              <Text key={i} style={{ color: s.color, fontSize: 11 }}>● {s.label}</Text>
            ))}
          </View>
          <Text style={{ color: C.dim, fontSize: 11 }}>high {fmtAxis(hi - pad)}</Text>
        </View>
      ) : null}
    </View>
  );
}

export function Spark({ data, color, width = 90, height = 28 }: { data: number[]; color: string; width?: number; height?: number }) {
  if (data.length < 2) return <View style={{ width, height }} />;
  const lo = Math.min(...data), hi = Math.max(...data), r = hi - lo || 1;
  const d = data.map((v, i) => `${i ? "L" : "M"}${((i / (data.length - 1)) * width).toFixed(1)},${(height - ((v - lo) / r) * height).toFixed(1)}`).join(" ");
  return <Svg width={width} height={height}><Path d={d} stroke={color} strokeWidth={1.6} fill="none" /></Svg>;
}

// Horizontal bars; positive green, negative red unless a colour is given. Zero line in the middle when values mix.
export function HBars({ items, fmt }: { items: { label: string; value: number; sub?: string; color?: string }[]; fmt: (v: number) => string }) {
  const max = Math.max(1e-9, ...items.map((i) => Math.abs(i.value)));
  const mixed = items.some((i) => i.value < 0) && items.some((i) => i.value > 0);
  return (
    <View style={{ gap: 8 }}>
      {items.map((it, k) => {
        const frac = Math.abs(it.value) / max;
        const col = it.color ?? (it.value >= 0 ? C.good : C.bad);
        return (
          <View key={k} style={{ gap: 3 }}>
            <View style={{ flexDirection: "row", justifyContent: "space-between" }}>
              <Text style={{ color: C.text, fontSize: 13 }}>{it.label}</Text>
              <Text style={{ color: col, fontSize: 13, fontWeight: "600" }}>{fmt(it.value)}</Text>
            </View>
            <View style={{ height: 8, backgroundColor: C.line, borderRadius: 4, flexDirection: "row", justifyContent: mixed ? "center" : "flex-start" }}>
              {mixed && it.value < 0 ? <View style={{ width: `${frac * 50}%`, backgroundColor: col, borderRadius: 4, position: "absolute", right: "50%", height: 8 }} /> : null}
              {mixed && it.value >= 0 ? <View style={{ width: `${frac * 50}%`, backgroundColor: col, borderRadius: 4, position: "absolute", left: "50%", height: 8 }} /> : null}
              {!mixed ? <View style={{ width: `${Math.max(2, frac * 100)}%`, backgroundColor: col, borderRadius: 4 }} /> : null}
            </View>
            {it.sub ? <Text style={{ color: C.dim, fontSize: 11 }}>{it.sub}</Text> : null}
          </View>
        );
      })}
    </View>
  );
}

// One bar split into parts (e.g. holdings vs cash).
export function StackBar({ parts, height = 14 }: { parts: { label: string; value: number; color: string }[]; height?: number }) {
  const [w, onLayout] = useWidth();
  const total = parts.reduce((a, p) => a + Math.max(0, p.value), 0) || 1;
  let x = 0;
  return (
    <View onLayout={onLayout} style={{ gap: 6 }}>
      {w > 0 ? (
        <Svg width={w} height={height}>
          {parts.map((p, i) => {
            const pw = (Math.max(0, p.value) / total) * w;
            const r = <Rect key={i} x={x} y={0} width={Math.max(0, pw - 1)} height={height} fill={p.color} rx={3} />;
            x += pw;
            return r;
          })}
        </Svg>
      ) : <View style={{ height }} />}
      <View style={{ flexDirection: "row", flexWrap: "wrap", gap: 10 }}>
        {parts.filter((p) => p.value > 0).map((p, i) => (
          <Text key={i} style={{ color: C.dim, fontSize: 11 }}><Text style={{ color: p.color }}>■</Text> {p.label}</Text>
        ))}
      </View>
    </View>
  );
}
