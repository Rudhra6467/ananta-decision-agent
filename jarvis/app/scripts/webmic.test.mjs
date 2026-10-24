// Plain-Node tests for the website microphone's pure parts (src/webmic.js):
//   node --no-warnings scripts/webmic.test.mjs
// End-of-speech rules (same as src/mic.ts), the 400 ms pre-roll, the resampler and the WAV, on synthetic sound. The worst case
// first: he starts talking the very instant the mic arms; his first word must be in the audio, whole.
import assert from "node:assert/strict";
import { WEBMIC, createTurnCapture, createVad, encodeWav, floatTo16, levelDb, packTurn, resample, toBase64, turnSlice } from "../src/webmic.js";

let checks = 0;
const check = (name, fn) => { fn(); checks++; console.log(`  ok  ${name}`); };

// ---- synthetic sound ----
function rng(seed) { let s = seed >>> 0; return () => { s = (s * 1664525 + 1013904223) >>> 0; return s / 4294967296 * 2 - 1; }; }
const room = (rate, ms, rms = 0.001, seed = 7) => { const r = rng(seed), n = Math.round(rate * ms / 1000), x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = r() * rms * Math.sqrt(3); return x; };
// speech-like: noise through two resonances (~500 Hz, ~1500 Hz), ~4 syllables a second (never fully quiet), sharp 3 ms edges
function speech(rate, ms, seed = 11) {
  const r = rng(seed), n = Math.round(rate * ms / 1000), x = new Float32Array(n);
  const res = (f, q) => { const w = 2 * Math.PI * f / rate, a = Math.exp(-w / (2 * q)); return { b1: 2 * a * Math.cos(w), b2: -a * a, y1: 0, y2: 0 }; };
  const f1 = res(500, 6), f2 = res(1500, 8);
  const edge = Math.round(rate * 0.003);
  for (let i = 0; i < n; i++) {
    const e = r();
    const y1 = e + f1.b1 * f1.y1 + f1.b2 * f1.y2; f1.y2 = f1.y1; f1.y1 = y1;
    const y2 = e + f2.b1 * f2.y1 + f2.b2 * f2.y2; f2.y2 = f2.y1; f2.y1 = y2;
    const t = i / rate;
    const syl = 0.15 + 0.85 * Math.abs(Math.sin(Math.PI * 4 * t + 0.6)) ** 1.5;   // syllables: loud, then a dip about 16 dB down
    const ramp = Math.min(1, i / edge, (n - 1 - i) / edge);
    x[i] = (0.06 * y1 + 0.04 * y2) * syl * ramp;
  }
  // scale to about -20 dBFS
  const g = 0.1 / Math.sqrt(x.reduce((s, v) => s + v * v, 0) / n);
  for (let i = 0; i < n; i++) x[i] *= g;
  return x;
}
const concat = (...parts) => { const n = parts.reduce((s, p) => s + p.length, 0), out = new Float32Array(n); let o = 0; for (const p of parts) { out.set(p, o); o += p.length; } return out; };
const mix = (a, b) => { const out = Float32Array.from(a); for (let i = 0; i < Math.min(a.length, b.length); i++) out[i] += b[i]; return out; };

// run one turn through the capture as the browser would (512-sample blocks)
function runTurn(pcm, rate, roomIn) {
  const buf = new Float32Array(Math.ceil(rate * WEBMIC.MAX_KEEP_S));
  const t = createTurnCapture(rate, roomIn, buf);
  const evs = [];
  for (let i = 0; i < pcm.length && t.endSample == null; i += 512) evs.push(...t.push(pcm.subarray(i, i + 512)));
  return { t, evs };
}
// decode our WAV and find where the burst starts / ends (2 ms windows above -40 dBFS)
function decodeWav(b64) {
  const b = Buffer.from(b64, "base64");
  assert.equal(b.toString("ascii", 0, 4), "RIFF"); assert.equal(b.toString("ascii", 8, 12), "WAVE");
  const rate = b.readUInt32LE(24), n = b.readUInt32LE(40) / 2, x = new Float32Array(n);
  for (let i = 0; i < n; i++) x[i] = b.readInt16LE(44 + 2 * i) / 32768;
  return { rate, x };
}
function burst(x, rate, thr = 0.01) {
  const w = Math.round(rate * 0.002); let first = -1, last = -1;
  for (let i = 0; i + w <= x.length; i += w) { if (Math.sqrt(levelSq(x, i, i + w)) > thr) { if (first < 0) first = i; last = i + w; } }
  return { startMs: first * 1000 / rate, endMs: last * 1000 / rate, durMs: (last - first) * 1000 / rate, totalMs: x.length * 1000 / rate };
}
const levelSq = (x, a, b) => { let s = 0; for (let i = a; i < b; i++) s += x[i] * x[i]; return s / (b - a); };

console.log("webmic pure parts:");
const R = 48000;

// ---- 1. the worst case: he talks the instant the mic arms ----
check("speech at the arm moment (room already learned): the WAV starts with his first word, whole", () => {
  const pcm = mix(concat(speech(R, 1500), new Float32Array(R * 3)), room(R, 4500));
  const { t, evs } = runTurn(pcm, R, { floor: -60, calibrated: true });
  assert.deepEqual(evs, ["onset", "silence"]);
  assert.equal(t.vad.state.onsetMs, 0, "onset found at the first 100 ms");
  const out = t.pack(); const w = decodeWav(out.b64), b = burst(w.x, w.rate);
  assert.equal(w.rate, 16000);
  assert.ok(b.startMs <= 30, `burst onset at ${b.startMs} ms in the WAV (<= 30)`);
  assert.ok(Math.abs(b.durMs - 1500) <= 30, `burst kept whole: ${b.durMs} ms of 1500`);
  const tail = b.totalMs - b.endMs;
  assert.ok(tail >= 1950 && tail <= 2250, `turn ended ${tail} ms after he stopped (about 2 s, request 92)`);
});
check("speech at the arm moment on the FIRST turn (room still being learned): nothing is cut either", () => {
  const pcm = mix(concat(speech(R, 1500), new Float32Array(R * 3)), room(R, 4500));
  const { t, evs } = runTurn(pcm, R, null);
  assert.ok(evs.includes("onset") && evs.at(-1) === "silence", evs.join());
  const b = burst(decodeWav(t.pack().b64).x, 16000);
  assert.ok(b.startMs <= 30 && Math.abs(b.durMs - 1500) <= 30, JSON.stringify(b));
  assert.ok(t.vad.state.floor <= -35, "a loud start can't set the room above -35 dBFS");
});
check("speech 2 s after arming: the WAV starts 400 ms before he does (pre-roll)", () => {
  const pcm = mix(concat(new Float32Array(R * 2), speech(R, 1200), new Float32Array(R * 3)), room(R, 6200));
  const { t } = runTurn(pcm, R, { floor: -60, calibrated: true });
  assert.equal(t.vad.state.onsetMs, 2000);
  const out = t.pack(); assert.equal(out.prerollMs, 400);
  const b = burst(decodeWav(out.b64).x, 16000);
  assert.ok(Math.abs(b.startMs - 400) <= 30, `burst at ${b.startMs} ms in the WAV (400 expected)`);
  assert.ok(Math.abs(b.durMs - 1200) <= 30);
});
check("speech starting mid-way through a 100 ms reading: pre-roll still at least 400 ms before it", () => {
  const pcm = mix(concat(new Float32Array(Math.round(R * 2.05)), speech(R, 1200), new Float32Array(R * 3)), room(R, 6250));
  const { t } = runTurn(pcm, R, { floor: -60, calibrated: true });
  const b = burst(decodeWav(t.pack().b64).x, 16000);
  assert.ok(b.startMs >= 370 && b.startMs <= 530, `burst at ${b.startMs} ms`);
});
check("44.1 kHz capture works the same", () => {
  const r = 44100, pcm = mix(concat(speech(r, 1000), new Float32Array(r * 3)), room(r, 4000));
  const { t, evs } = runTurn(pcm, r, { floor: -60, calibrated: true });
  assert.deepEqual(evs, ["onset", "silence"]);
  const b = burst(decodeWav(t.pack().b64).x, 16000);
  assert.ok(b.startMs <= 30 && Math.abs(b.durMs - 1000) <= 30, JSON.stringify(b));
});

// ---- 2. the end-of-speech rules (same as src/mic.ts), level by level ----
const feed = (vad, levels) => { const out = []; levels.forEach((m, i) => { const e = vad.step(m, (i + 1) * 100); if (e) out.push([e, (i + 1) * 100]); }); return out; };
const rep = (m, n) => Array(n).fill(m);
check("first turn learns the room in 400 ms, then two loud readings = speech, 2 s of quiet ends it (request 92)", () => {
  const v = createVad(null);
  const ev = feed(v, [...rep(-60, 6), ...rep(-25, 8), ...rep(-60, 25)]);
  assert.deepEqual(ev, [["onset", 800], ["silence", 3500]]);
  assert.equal(v.state.onsetMs, 600, "onset = start of the first loud reading");
  assert.ok(v.room().calibrated && Math.abs(v.room().floor + 60) < 0.5);
});
check("room carried over: no 400 ms of re-learning, speech at once is speech", () => {
  const v = createVad({ floor: -60, calibrated: true });
  assert.deepEqual(feed(v, [...rep(-25, 5), ...rep(-60, 22)]), [["onset", 300], ["silence", 2600]]);
  assert.equal(v.state.onsetMs, 0, "onset = where he started, even though 'hearing you' waits for 250 ms");
  const fresh = createVad(null);                                 // the old way: the first 400 ms only learn the room
  assert.deepEqual(feed(fresh, rep(-25, 4)), []);
});
check("the tail of Ananta's voice (loud only in the first 250 ms) is not speech; speech through it is", () => {
  assert.deepEqual(feed(createVad({ floor: -60, calibrated: true }), [-30, -30, ...rep(-60, 160)]).at(-1), ["nospeech", 15100]);
  const v = createVad({ floor: -60, calibrated: true });
  assert.deepEqual(feed(v, [-30, -30, -25, -25, ...rep(-60, 12)])[0], ["onset", 300]);
  assert.equal(v.state.onsetMs, 0);
});
check("quiet is measured against his own voice (18 dB under his loudest)", () => {
  const v = createVad({ floor: -60, calibrated: true });
  // he speaks at -15, then the room gets louder (-36: above the room bar of -50, but 21 dB under his voice) -> ends
  const q = [-36, -38, -35, -37, -39, -36, -38, -35, -37, -39, -36];
  assert.deepEqual(feed(v, [...rep(-15, 5), ...q, ...q]).at(-1), ["silence", 2600]);
});
check("a flat hum after he speaks ends the turn (2.2 s, < 5 dB of change)", () => {
  const v = createVad({ floor: -60, calibrated: true });
  const ev = feed(v, [...rep(-30, 3), ...rep(-44, 30)]);      // -44 is above the bar (-48) but perfectly steady
  assert.equal(ev.at(-1)[0], "flat");
});
check("15 s with nothing said = no speech; 30 s of talking = max; 3 s of digital silence = dead mic", () => {
  assert.deepEqual(feed(createVad(null), rep(-60, 200)).at(-1), ["nospeech", 15100]);
  const talk = Array.from({ length: 320 }, (_, i) => (i % 2 ? -22 : -16));
  assert.deepEqual(feed(createVad({ floor: -60, calibrated: true }), talk).map((e) => e[0]), ["onset", "max"]);
  assert.deepEqual(feed(createVad(null), rep(-160, 40)), [["dead", 3100]]);
});
check("the carried-over room is kept within -75..-35 dBFS", () => {
  assert.equal(createVad({ floor: -20, calibrated: true }).state.floor, -35);
  assert.equal(createVad({ floor: -99, calibrated: true }).state.floor, -75);
  assert.equal(createVad({ floor: -50, calibrated: false }).state.calibrated, false);
});

// ---- 3. pre-roll slicing ----
check("pre-roll slice: 400 ms before the onset, never before the capture started", () => {
  assert.deepEqual(turnSlice(1000, 96000, 48000), { start: 28800, end: 96000, prerollMs: 400 });
  assert.deepEqual(turnSlice(100, 96000, 48000), { start: 0, end: 96000, prerollMs: 100 });
  assert.deepEqual(turnSlice(0, 96000, 48000), { start: 0, end: 96000, prerollMs: 0 });
  assert.deepEqual(turnSlice(null, 96000, 48000), { start: 0, end: 96000, prerollMs: 0 });
  assert.equal(packTurn(new Float32Array(48000), 48000, null).prerollMs, 0);
});

// ---- 4. resampler ----
const sine = (rate, f, ms, a = 0.5) => Float32Array.from({ length: Math.round(rate * ms / 1000) }, (_, i) => a * Math.sin(2 * Math.PI * f * i / rate));
const rms = (x, a = 0, b = x.length) => Math.sqrt(levelSq(x, a, b));
check("resampler: speech band passes at the right pitch and level; above 8 kHz is removed (no aliasing)", () => {
  const y = resample(sine(48000, 1000, 500), 48000, 16000);
  assert.equal(y.length, 8000);
  assert.ok(Math.abs(rms(y, 200, 7800) / (0.5 / Math.SQRT2) - 1) < 0.01, "1 kHz level kept");
  let zc = 0; for (let i = 201; i < 7800; i++) if ((y[i - 1] < 0) !== (y[i] < 0)) zc++;
  assert.ok(Math.abs(zc / ((7800 - 201) / 16000) / 2 - 1000) < 5, `pitch kept (${zc} crossings)`);
  assert.ok(rms(resample(sine(48000, 3400, 500), 48000, 16000), 200, 7800) > 0.34, "3.4 kHz passes");
  assert.ok(rms(resample(sine(48000, 12000, 500), 48000, 16000), 200, 7800) < 0.0035, "12 kHz is at least 40 dB down");
  assert.equal(resample(sine(44100, 1000, 1000), 44100, 16000).length, 16000);
  assert.ok(Math.abs(rms(resample(sine(44100, 1000, 1000), 44100, 16000), 300, 15700) / (0.5 / Math.SQRT2) - 1) < 0.01);
  const same = resample(Float32Array.from([0.1, 0.2]), 16000, 16000); assert.deepEqual([...same].map((v) => +v.toFixed(3)), [0.1, 0.2]);
});

// ---- 5. WAV + base64 ----
check("WAV header: 16 kHz mono 16-bit PCM, right sizes; samples clamp; base64 matches Node's", () => {
  const pcm = floatTo16(Float32Array.from([0, 0.5, -0.5, 1.5, -1.5]));
  assert.deepEqual([...pcm], [0, 16384, -16384, 32767, -32768]);
  const w = encodeWav(pcm, 16000), b = Buffer.from(w);
  assert.equal(w.length, 44 + 10);
  assert.equal(b.toString("ascii", 0, 4), "RIFF"); assert.equal(b.readUInt32LE(4), 36 + 10); assert.equal(b.toString("ascii", 8, 16), "WAVEfmt ");
  assert.equal(b.readUInt32LE(16), 16); assert.equal(b.readUInt16LE(20), 1); assert.equal(b.readUInt16LE(22), 1);
  assert.equal(b.readUInt32LE(24), 16000); assert.equal(b.readUInt32LE(28), 32000); assert.equal(b.readUInt16LE(32), 2); assert.equal(b.readUInt16LE(34), 16);
  assert.equal(b.toString("ascii", 36, 40), "data"); assert.equal(b.readUInt32LE(40), 10); assert.equal(b.readInt16LE(44 + 2), 16384);
  for (const n of [0, 1, 2, 3, 4, 5, 100, 20001]) { const u = Uint8Array.from({ length: n }, (_, i) => (i * 37 + 11) & 255); assert.equal(toBase64(u), Buffer.from(u).toString("base64"), `len ${n}`); }
  assert.equal(levelDb(new Float32Array(10)), -160);
  assert.ok(Math.abs(levelDb(sine(48000, 1000, 100, 0.1)) - 20 * Math.log10(0.1 / Math.SQRT2)) < 0.05);
});
check("one whole 20 s turn packs to a WAV of the expected size (about 640 KB)", () => {
  const out = packTurn(new Float32Array(48000 * 20), 48000, null);
  assert.equal(out.bytes, 44 + 16000 * 20 * 2); assert.equal(out.mime, "audio/wav");
});

console.log(`webmic: all ${checks} checks passed`);
