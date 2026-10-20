// The website's microphone for voice mode: ONE capture session for the whole conversation (Madhav, repair #74, Oct 20:
// "a tiny inconsistency between the timing of what I speak and when it hears"; "And Solana?" came out as "N. Solana.").
//
// Why: in the browser, expo-audio's recorder asks for the microphone again on EVERY turn (a permission stream, then a second
// getUserMedia, a device list, an analyser and a new MediaRecorder) and lets it go after each turn. On an iPhone each
// getUserMedia costs hundreds of milliseconds, the orb already said "listening" during all that, and the first word was lost.
// Now:
//  - open() asks for the microphone once, when voice mode starts (echo cancellation, noise suppression, auto gain on);
//  - arm() / disarm() are instant: the stream stays open, they only start / stop keeping the sound;
//  - while Ananta speaks the session is disarmed (nothing is kept, so it never hears itself) but the stream stays open;
//  - close() (voice ends) lets everything go.
// End of speech follows the same rules and numbers as src/mic.ts (the phone app), with one change: the room level is learned on
// the FIRST turn only and kept for the rest of the conversation (no 400 ms re-learning at the start of each turn). The audio
// handed over starts 400 ms before the detected start of speech (never before the mic armed), so a word that begins as the
// mic arms is never cut. Output: 16 kHz mono 16-bit WAV, base64.
//
// Plain JavaScript with JSDoc types (no TypeScript syntax) so a browser can import it directly for tests and Metro bundles it.
// The pure parts (end-of-speech rules, pre-roll, resampler, WAV) are exported and tested in Node: scripts/webmic.test.mjs.
// The browser parts are tested in headless Chromium: scripts/webmic_browser_test.py.

export const WEBMIC = Object.freeze({
  // the same end-of-speech rules as src/mic.ts
  CALIBRATE_MS: 400, END_SILENCE_MS: 1000, MAX_TURN_MS: 20000, NO_SPEECH_MS: 15000, DEAD_MS: 3000,
  BELOW_PEAK_DB: 18, STEADY_DB: 5, STEADY_N: 12, MIN_TURN_MS: 1200,
  // a loud stretch that is over within the first 250 ms after the mic arms is not speech: it is the tail of Ananta's own voice
  // still leaving the speaker (Bluetooth adds ~200 ms). The 400 ms of re-learning the room used to absorb it. Nothing is lost:
  // all of it is kept; only "hearing you" waits until the loudness outlasts 250 ms.
  GUARD_MS: 250,
  // one level reading per 100 ms of sound (mic.ts reads the meter every 100 ms)
  TICK_MS: 100,
  PREROLL_MS: 400,                 // the audio starts this long before the detected start of speech
  OUT_RATE: 16000,                 // what the service gets: 16 kHz mono 16-bit WAV
  LIVE_TIMEOUT_MS: 1500,           // arm(): no sound arriving within this = the session is broken (reopen)
  STALL_MS: 1500,                  // armed, and the sound stopped arriving for this long = dead (iOS took the mic, etc.)
  MAX_KEEP_S: 21,                  // capture buffer (the longest turn is 20 s)
});

/** @typedef {{ floor: number, calibrated: boolean }} Room */
/** @typedef {"onset" | "silence" | "flat" | "max" | "nospeech" | "dead"} VadEvent */
/**
 * @typedef {{ floor: number, calibrated: boolean, samples: number[], spoke: boolean, lastLoud: number, loudRun: number,
 *   runStart: number, peak: number, spokeAt: number, onsetMs: number | null, win: number[], heardAny: boolean,
 *   done: boolean, endMs: number | null, reason: VadEvent | null }} VadState
 */

const clampFloor = (/** @type {number} */ f) => Math.max(-75, Math.min(-35, f));

/**
 * Level of a stretch of samples in dBFS (RMS), -160 for digital silence. Same formula as expo-audio's meter.
 * @param {ArrayLike<number>} x @param {number} [from] @param {number} [to]
 */
export function levelDb(x, from = 0, to = x.length) {
  const n = to - from;
  if (n <= 0) return -160;
  let s = 0;
  for (let i = from; i < to; i++) s += x[i] * x[i];
  const rms = Math.sqrt(s / n);
  return rms > 0 ? Math.max(-160, 20 * Math.log10(rms)) : -160;
}

/**
 * End-of-speech detector: one step per 100 ms of sound. Same rules as src/mic.ts: learn the room (first 400 ms, first turn
 * only when a Room is passed back in); speech = clearly louder than the room (10 dB, at least -30 dBFS), two readings in a row,
 * still loud after the first 250 ms (Ananta's tail);
 * after he starts, "quiet" means 18 dB under his own loudest; the turn ends after 1.0 s of quiet, or after 1.2 s of flat hum
 * (fan, TV), or at 20 s; nothing said in 15 s = no speech; no sound at all for 3 s = dead.
 * @param {Room | null} [room] the room learned on an earlier turn of this conversation
 */
export function createVad(room = null) {
  const C = WEBMIC;
  /** @type {VadState} */
  const v = {
    floor: room && room.calibrated ? clampFloor(room.floor) : -60, calibrated: !!(room && room.calibrated), samples: [],
    spoke: false, lastLoud: 0, loudRun: 0, runStart: 0, peak: -160, spokeAt: 0, onsetMs: null, win: [], heardAny: false,
    done: false, endMs: null, reason: null,
  };
  /** @param {VadEvent} r @param {number} now @returns {VadEvent} */
  const end = (r, now) => { v.done = true; v.endMs = now; v.reason = r; return r; };
  return {
    state: v,
    /** @returns {Room} what to carry to the next turn */
    room: () => ({ floor: clampFloor(v.floor), calibrated: v.calibrated }),
    /**
     * @param {number} m level of this 100 ms (dBFS)
     * @param {number} now end of this 100 ms, in ms since the capture went live
     * @returns {VadEvent | null}
     */
    step(m, now) {
      if (v.done) return null;
      if (m > -159) v.heardAny = true;
      if (now > C.DEAD_MS && !v.heardAny) return end("dead", now);              // no sound at all: the mic is not really working
      if (!v.calibrated) {
        if (now <= C.CALIBRATE_MS) { if (m > -160) v.samples.push(m); return null; }
        if (v.samples.length) {
          const sorted = [...v.samples].sort((a, b) => a - b);
          v.floor = clampFloor(sorted[Math.floor(sorted.length / 2)]);         // a loud start can't set the bar too high
          v.calibrated = true;
        }
        v.samples = [];
      }
      const thr = Math.min(v.floor + 10, -30);
      if (v.spoke) v.peak = Math.max(v.peak, m);
      const bar = v.spoke ? Math.max(thr, v.peak - C.BELOW_PEAK_DB) : thr;     // after he starts: "loud" = close to his own voice
      v.win.push(m);
      if (v.win.length > C.STEADY_N) v.win.shift();
      /** @type {VadEvent | null} */
      let ev = null;
      if (m > bar) {
        if (v.loudRun === 0) v.runStart = now - C.TICK_MS;                      // where this loud stretch began
        v.loudRun += 1;
        v.lastLoud = now;
        if (v.loudRun >= 2 && !v.spoke && now > C.GUARD_MS) { v.spoke = true; v.spokeAt = now; v.peak = m; v.onsetMs = v.runStart; ev = "onset"; }
      } else {
        v.loudRun = 0;
        if (!v.spoke) v.floor = 0.97 * v.floor + 0.03 * m;                     // follow slow changes in room noise
      }
      if (v.spoke && now - v.lastLoud > C.END_SILENCE_MS) return end("silence", now);
      if (v.spoke && now - v.spokeAt > C.MIN_TURN_MS && v.win.length >= C.STEADY_N &&
          Math.max(...v.win) - Math.min(...v.win) < C.STEADY_DB) return end("flat", now);   // a flat hum is not speech
      if (now > C.MAX_TURN_MS) return end(v.spoke ? "max" : "nospeech", now);
      if (!v.spoke && now > C.NO_SPEECH_MS) return end("nospeech", now);
      return ev;
    },
  };
}

/**
 * Which part of the captured sound to hand over: from PREROLL_MS before the detected start of speech (never before the
 * capture started) to the end of the turn. No detected start (a tap on Done while quiet): all of it.
 * @param {number | null} onsetMs detected start of speech, ms since the capture went live
 * @param {number} total samples captured for this turn
 * @param {number} rate sample rate of the capture
 * @param {number} [prerollMs]
 * @returns {{ start: number, end: number, prerollMs: number }}
 */
export function turnSlice(onsetMs, total, rate, prerollMs = WEBMIC.PREROLL_MS) {
  if (onsetMs == null || !(onsetMs >= 0)) return { start: 0, end: total, prerollMs: 0 };
  const startMs = Math.max(0, onsetMs - prerollMs);
  const start = Math.min(total, Math.round((startMs * rate) / 1000));
  return { start, end: total, prerollMs: Math.round(onsetMs - startMs) };
}

/**
 * Resample mono audio (windowed-sinc low-pass, Blackman window, ~8 lobes each side). 48 or 44.1 kHz -> 16 kHz in practice.
 * @param {Float32Array} x @param {number} inRate @param {number} outRate
 * @returns {Float32Array}
 */
export function resample(x, inRate, outRate) {
  if (inRate === outRate) return Float32Array.from(x);
  const ratio = inRate / outRate;                       // input samples per output sample
  const n = Math.floor(x.length / ratio);
  const out = new Float32Array(n);
  const fc = 0.5 * Math.min(1, outRate / inRate) * 0.9;  // cutoff, cycles per input sample (90% of the lower Nyquist)
  const half = Math.ceil(8 / (2 * fc));                  // 8 zero crossings each side
  for (let i = 0; i < n; i++) {
    const t = i * ratio;
    const k0 = Math.max(0, Math.ceil(t - half)), k1 = Math.min(x.length - 1, Math.floor(t + half));
    let acc = 0, wsum = 0;
    for (let k = k0; k <= k1; k++) {
      const d = k - t;
      const u = d / half;
      const win = 0.42 + 0.5 * Math.cos(Math.PI * u) + 0.08 * Math.cos(2 * Math.PI * u);
      const a = 2 * fc * d;
      const sinc = a === 0 ? 1 : Math.sin(Math.PI * a) / (Math.PI * a);
      const h = sinc * win;
      acc += x[k] * h;
      wsum += h;
    }
    out[i] = wsum !== 0 ? acc / wsum : 0;
  }
  return out;
}

/** @param {Float32Array} x @returns {Int16Array} */
export function floatTo16(x) {
  const out = new Int16Array(x.length);
  for (let i = 0; i < x.length; i++) {
    const s = Math.max(-1, Math.min(1, x[i]));
    out[i] = s < 0 ? Math.round(s * 0x8000) : Math.round(s * 0x7fff);
  }
  return out;
}

/**
 * A 16-bit mono PCM WAV file (44-byte header + data).
 * @param {Int16Array} pcm @param {number} rate @returns {Uint8Array}
 */
export function encodeWav(pcm, rate) {
  const data = pcm.length * 2;
  const buf = new ArrayBuffer(44 + data);
  const dv = new DataView(buf);
  const str = (/** @type {number} */ o, /** @type {string} */ s) => { for (let i = 0; i < s.length; i++) dv.setUint8(o + i, s.charCodeAt(i)); };
  str(0, "RIFF"); dv.setUint32(4, 36 + data, true); str(8, "WAVE");
  str(12, "fmt "); dv.setUint32(16, 16, true); dv.setUint16(20, 1, true); dv.setUint16(22, 1, true);
  dv.setUint32(24, rate, true); dv.setUint32(28, rate * 2, true); dv.setUint16(32, 2, true); dv.setUint16(34, 16, true);
  str(36, "data"); dv.setUint32(40, data, true);
  for (let i = 0; i < pcm.length; i++) dv.setInt16(44 + 2 * i, pcm[i], true);
  return new Uint8Array(buf);
}

const B64 = "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
/** @param {Uint8Array} b @returns {string} */
export function toBase64(b) {
  const parts = [];
  let s = "";
  let i = 0;
  for (; i + 2 < b.length; i += 3) {
    const n = (b[i] << 16) | (b[i + 1] << 8) | b[i + 2];
    s += B64[(n >> 18) & 63] + B64[(n >> 12) & 63] + B64[(n >> 6) & 63] + B64[n & 63];
    if (s.length >= 8192) { parts.push(s); s = ""; }
  }
  if (i < b.length) {
    const n = (b[i] << 16) | ((i + 1 < b.length ? b[i + 1] : 0) << 8);
    s += B64[(n >> 18) & 63] + B64[(n >> 12) & 63] + (i + 1 < b.length ? B64[(n >> 6) & 63] : "=") + "=";
  }
  parts.push(s);
  return parts.join("");
}

/**
 * One turn's sound -> what the service gets: the pre-roll slice, resampled to 16 kHz, as a base64 WAV.
 * @param {Float32Array} pcm captured samples (from the moment the capture went live)
 * @param {number} rate @param {number | null} onsetMs
 */
export function packTurn(pcm, rate, onsetMs) {
  const sl = turnSlice(onsetMs, pcm.length, rate);
  const wav = encodeWav(floatTo16(resample(pcm.subarray(sl.start, sl.end), rate, WEBMIC.OUT_RATE)), WEBMIC.OUT_RATE);
  return { b64: toBase64(wav), bytes: wav.length, mime: "audio/wav", startSample: sl.start, prerollMs: sl.prerollMs };
}

/**
 * One turn's capture: keeps the samples (in a buffer reused across turns) and runs the end-of-speech rules every 100 ms of
 * sound. The browser session feeds it whatever the microphone delivers; the Node tests feed it synthetic sound.
 * @param {number} rate sample rate of the capture
 * @param {Room | null} room the room learned on an earlier turn (null: learn it now)
 * @param {Float32Array} buf where the samples go
 */
export function createTurnCapture(rate, room, buf) {
  const tickN = Math.max(1, Math.round((rate * WEBMIC.TICK_MS) / 1000));
  const vad = createVad(room);
  let len = 0, sum = 0, count = 0, ticks = 0;
  /** @type {number | null} */ let endSample = null;
  return {
    vad,
    rate,
    get length() { return len; },
    get endSample() { return endSample; },
    /** End the turn here (the sound stopped arriving). */
    stop() { if (endSample == null) endSample = len; },
    /**
     * Keep d[from..] and run the rules on each full 100 ms. Returns the events, in order; the turn's end is always last.
     * @param {ArrayLike<number>} d @param {number} [from] @param {(db: number) => void} [onLevel]
     * @returns {VadEvent[]}
     */
    push(d, from = 0, onLevel) {
      /** @type {VadEvent[]} */ const evs = [];
      if (endSample != null) return evs;                    // the turn already ended; waiting to be handed over
      const take = Math.min(d.length - from, buf.length - len);
      for (let i = 0; i < take; i++) {
        const x = d[from + i];
        buf[len++] = x;
        sum += x * x;
        if (++count >= tickN) {
          const rms = Math.sqrt(sum / count);
          const db = rms > 0 ? Math.max(-160, 20 * Math.log10(rms)) : -160;
          sum = 0; count = 0; ticks += 1;
          if (onLevel) { try { onLevel(db); } catch { /* */ } }
          const ev = vad.step(db, ticks * WEBMIC.TICK_MS);
          if (ev) evs.push(ev);
          if (ev && ev !== "onset") { endSample = len; break; }
        }
      }
      return evs;
    },
    /** What to hand over: from 400 ms before he started (never before the capture did) to the end of the turn. */
    pack() { return packTurn(buf.subarray(0, endSample != null ? endSample : len), rate, vad.state.spoke ? vad.state.onsetMs : null); },
  };
}

// ---- the browser session ----

// The capture tap: an AudioWorklet that posts the sound to the page in small blocks, each with the frame it starts at.
const WORKLET = `
class AnantaTap extends AudioWorkletProcessor {
  constructor() { super(); this.buf = new Float32Array(512); this.n = 0; this.first = 0; }
  process(inputs) {
    const ch = inputs[0] && inputs[0][0];
    if (ch) {
      if (this.n + ch.length > this.buf.length) this.flush();
      if (this.n === 0) this.first = currentFrame;
      this.buf.set(ch, this.n);
      this.n += ch.length;
      if (this.n >= 512) this.flush();
    }
    return true;
  }
  flush() {
    if (!this.n) return;
    const d = this.buf.slice(0, this.n);
    this.port.postMessage({ f: this.first, d }, [d.buffer]);
    this.n = 0;
  }
}
registerProcessor("ananta-tap", AnantaTap);
`;

/** True when this browser can run the session (else mic.ts falls back to expo-audio's recorder). */
export function webMicSupported() {
  const g = /** @type {any} */ (globalThis);
  return !!(g.navigator && g.navigator.mediaDevices && g.navigator.mediaDevices.getUserMedia && (g.AudioContext || g.webkitAudioContext));
}

/**
 * @typedef {{ onLevel?: (db: number) => void, onSpeech?: () => void, onEnd?: (reason: VadEvent) => void }} ArmHandlers
 * @typedef {{ armAt: number, liveAt: number | null, armToLiveMs: number | null, onsetMs: number | null, onsetAt: number | null,
 *   endMs: number | null, endAt: number | null, speechMs: number | null, endSilenceMs: number | null, prerollMs: number | null,
 *   bytes: number | null, rate: number, capture: string, reason: string | null }} TurnTiming
 */

/**
 * The voice-mode microphone session.
 * @param {{ navigator?: any, AudioContext?: any, now?: () => number, log?: (msg: string) => void }} [env]
 */
export function createWebMic(env = {}) {
  const g = /** @type {any} */ (globalThis);
  const nav = env.navigator || g.navigator;
  const AC = env.AudioContext || g.AudioContext || g.webkitAudioContext;
  const now = env.now || (() => (g.performance && g.performance.now ? g.performance.now() : Date.now()));
  const C = WEBMIC;

  /** @type {any} */ let ctx = null;
  /** @type {any} */ let stream = null;
  /** @type {any} */ let src = null;
  /** @type {any} */ let node = null;
  /** @type {any} */ let sink = null;
  let capture = "none";
  let ready = false, broken = false, sid = 0;                 // sid: which open session (close() makes a late open() give up)
  /** @type {Promise<boolean> | null} */ let opening = null;
  /** @type {Room | null} */ let room = null;

  // the turn being captured
  let armed = false, live = false, rate = 48000;
  /** @type {number | null} */ let armFrame = null;
  /** @type {Float32Array | null} */ let buf = null;
  /** @type {ReturnType<typeof createTurnCapture> | null} */ let turn = null;
  /** @type {ArmHandlers} */ let h = {};
  /** @type {((ok: boolean) => void) | null} */ let liveResolve = null;
  /** @type {any} */ let watch = null;
  let lastChunkAt = 0;
  /** @type {TurnTiming | null} */ let timing = null;
  /** @type {any} */ let lastError = null;

  const log = (/** @type {string} */ m) => { try { env.log && env.log(m); } catch { /* */ } };

  function teardown() {
    armed = false; live = false; ready = false;
    if (watch) { clearInterval(watch); watch = null; }
    if (liveResolve) { const r = liveResolve; liveResolve = null; r(false); }
    try { if (node && node.port) node.port.onmessage = null; } catch { /* */ }
    try { if (node) node.onaudioprocess = null; } catch { /* */ }
    for (const n of [src, node, sink]) { try { n && n.disconnect(); } catch { /* */ } }
    try { stream && stream.getTracks().forEach((/** @type {any} */ t) => t.stop()); } catch { /* */ }
    try { ctx && ctx.close && ctx.close(); } catch { /* */ }
    ctx = stream = src = node = sink = null;
    capture = "none";
  }

  /** @param {number | null} frame first frame of this block (null = unknown, ScriptProcessor) @param {Float32Array} d */
  function onChunk(frame, d) {
    lastChunkAt = now();
    if (!armed || !turn) return;
    let from = 0;
    if (frame != null && armFrame != null) {
      if (frame + d.length <= armFrame) return;             // captured before arm(): not this turn's (Ananta may still have been talking)
      from = Math.max(0, armFrame - frame);
    }
    if (!live) {
      live = true;
      if (timing) { timing.liveAt = lastChunkAt; timing.armToLiveMs = Math.round(lastChunkAt - timing.armAt); }
      if (liveResolve) { const r = liveResolve; liveResolve = null; r(true); }
    }
    const hh = h;
    for (const ev of turn.push(d, from, hh.onLevel)) {
      if (ev === "onset") {
        if (timing) timing.onsetAt = now();
        try { hh.onSpeech && hh.onSpeech(); } catch { /* */ }
      } else {
        if (timing) timing.endAt = now();
        if (ev === "dead") broken = true;                   // no sound at all: the next arm() opens the mic again
        try { hh.onEnd && hh.onEnd(ev); } catch { /* */ }
      }
    }
  }

  /** @param {any} c */
  async function makeWorklet(c) {
    if (!c.audioWorklet || typeof g.AudioWorkletNode === "undefined" || typeof g.Blob === "undefined") return null;
    const url = g.URL.createObjectURL(new g.Blob([WORKLET], { type: "application/javascript" }));
    try {
      await Promise.race([c.audioWorklet.addModule(url), new Promise((_, rej) => setTimeout(() => rej(new Error("worklet timeout")), 2500))]);
    } finally {
      try { g.URL.revokeObjectURL(url); } catch { /* */ }
    }
    const n = new g.AudioWorkletNode(c, "ananta-tap", { numberOfInputs: 1, numberOfOutputs: 1, outputChannelCount: [1],
      channelCount: 1, channelCountMode: "explicit", channelInterpretation: "speakers" });
    n.port.onmessage = (/** @type {any} */ e) => onChunk(e.data.f, e.data.d);
    return n;
  }

  /** @param {any} c */
  function makeScriptProcessor(c) {
    const n = c.createScriptProcessor(2048, 1, 1);
    n.onaudioprocess = (/** @type {any} */ e) => onChunk(null, new Float32Array(e.inputBuffer.getChannelData(0)));
    return n;
  }

  /**
   * Ask for the microphone and start the capture graph. Call it straight from the tap that starts voice mode: the
   * AudioContext is made right away (before any waiting), because Safari only lets sound start inside a tap.
   * @returns {Promise<boolean>}
   */
  function open() {
    if (ready && !broken) return Promise.resolve(true);
    if (opening) return opening;
    if (broken) teardown();
    broken = false;
    const my = sid;
    let c = null;
    try { c = new AC({ latencyHint: "interactive" }); } catch { try { c = new AC(); } catch { c = null; } }
    try { c && c.resume && c.resume().catch(() => {}); } catch { /* */ }
    opening = (async () => {
      /** @type {any} */ let s = null, sr = null, nd = null, sk = null;
      const drop = () => {                                     // let go of what this attempt made
        for (const n of [sr, nd, sk]) { try { n && n.disconnect(); } catch { /* */ } }
        try { s && s.getTracks().forEach((/** @type {any} */ t) => t.stop()); } catch { /* */ }
        try { c && c.close && c.close(); } catch { /* */ }
      };
      try {
        if (!c) throw new Error("no AudioContext");
        s = await nav.mediaDevices.getUserMedia({ audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 } });
        if (my !== sid) { drop(); return false; }              // voice ended while the browser was asking: let it go at once
        const track = s.getAudioTracks()[0];
        const want = track && track.getSettings ? track.getSettings().sampleRate : undefined;
        if (want && c.sampleRate !== want) {
          // Safari: a context made before the mic opened can run at another rate than the mic (garbled sound): make it again,
          // now that capture is on (a page that is capturing may start sound without a tap)
          try { c.close(); } catch { /* */ }
          try { c = new AC({ latencyHint: "interactive", sampleRate: want }); } catch { c = new AC(); }
        }
        if (c.state !== "running") { try { await Promise.race([c.resume(), new Promise((r) => setTimeout(r, 800))]); } catch { /* */ } }
        sr = c.createMediaStreamSource(s);
        sk = c.createGain();
        sk.gain.value = 0;                                     // the tap must be pulled by the graph; it plays nothing
        sk.connect(c.destination);
        let kind = "worklet";
        try { nd = await makeWorklet(c); } catch (e) { log(`worklet failed: ${e}`); nd = null; }
        if (!nd) { nd = makeScriptProcessor(c); kind = "scriptprocessor"; }
        sr.connect(nd);
        nd.connect(sk);
        if (my !== sid) { drop(); return false; }
        if (track) track.addEventListener("ended", () => { if (my === sid) broken = true; });
        ctx = c; stream = s; src = sr; node = nd; sink = sk; capture = kind;
        rate = c.sampleRate;
        if (!buf || buf.length !== Math.ceil(rate * C.MAX_KEEP_S)) buf = new Float32Array(Math.ceil(rate * C.MAX_KEEP_S));
        ready = true;
        lastError = null;
        return true;
      } catch (e) {
        lastError = e;
        log(`open failed: ${e}`);
        drop();
        return false;
      } finally {
        if (my === sid) opening = null;
      }
    })();
    return opening;
  }

  /**
   * Start keeping the sound for one turn. Resolves true once sound is really arriving (the orb may say "listening").
   * @param {ArmHandlers} [handlers]
   * @returns {Promise<boolean>}
   */
  async function arm(handlers = {}) {
    if (armed) disarm(false);
    const track = stream && stream.getAudioTracks()[0];
    if (!ready || broken || (track && track.readyState === "ended")) {
      teardown();
      broken = false;
      if (!(await open())) return false;
    }
    if (ctx.state !== "running") { try { await Promise.race([ctx.resume(), new Promise((r) => setTimeout(r, 800))]); } catch { /* */ } }
    h = handlers;
    turn = createTurnCapture(rate, room, /** @type {Float32Array} */ (buf));
    live = false;
    timing = { armAt: now(), liveAt: null, armToLiveMs: null, onsetMs: null, onsetAt: null, endMs: null, endAt: null, speechMs: null,
      endSilenceMs: null, prerollMs: null, bytes: null, rate, capture, reason: null };
    armFrame = capture === "worklet" ? Math.round(ctx.currentTime * rate) : null;
    const p = new Promise((res) => { liveResolve = res; });
    armed = true;
    lastChunkAt = now();
    if (watch) clearInterval(watch);
    const t0 = now();
    watch = setInterval(() => {
      if (!armed) return;
      const t = now();
      if (!live && t - t0 > C.LIVE_TIMEOUT_MS) { broken = true; if (liveResolve) { const r = liveResolve; liveResolve = null; r(false); } return; }
      if (live && turn && turn.endSample == null && t - lastChunkAt > C.STALL_MS) {   // the sound stopped arriving (iOS took the mic)
        broken = true;
        turn.stop();
        if (timing) timing.endAt = t;
        try { h.onEnd && h.onEnd("dead"); } catch { /* */ }
      }
    }, 250);
    const ok = await p;
    if (!ok) {
      armed = false;
      if (watch) { clearInterval(watch); watch = null; }
      return false;
    }
    return true;
  }

  /**
   * Stop keeping the sound (instant; the stream stays open). deliver = hand over what was said.
   * @param {boolean} deliver
   * @returns {{ b64: string, bytes: number, mime: string, timing: TurnTiming } | null}
   */
  function disarm(deliver) {
    const was = armed;
    armed = false;
    if (watch) { clearInterval(watch); watch = null; }
    if (liveResolve) { const r = liveResolve; liveResolve = null; r(false); }
    if (!was || !turn) return null;
    const st = turn.vad.state;
    if (st.calibrated) room = turn.vad.room();                // the room level carries over to the next turn
    const total = turn.endSample != null ? turn.endSample : turn.length;
    if (timing) {
      timing.onsetMs = st.onsetMs;
      timing.endMs = Math.round((total / rate) * 1000);
      timing.reason = st.reason || (deliver ? "sent" : "cancelled");
      if (st.spoke && st.onsetMs != null) {
        timing.speechMs = Math.round(st.lastLoud - st.onsetMs);
        timing.endSilenceMs = Math.round(timing.endMs - st.lastLoud);
      }
    }
    if (!deliver) return null;
    const out = turn.pack();
    if (timing) { timing.prerollMs = out.prerollMs; timing.bytes = out.bytes; }
    return { b64: out.b64, bytes: out.bytes, mime: out.mime, timing: /** @type {TurnTiming} */ ({ ...timing }) };
  }

  /** Voice mode ended: let the microphone go (the next open() asks again and learns the room again). */
  function close() {
    sid += 1;
    teardown();
    room = null;
    broken = false;
    opening = null;
  }

  return {
    open, arm, disarm, close,
    get isOpen() { return ready && !broken; },
    get armed() { return armed; },
    get live() { return armed && live; },
    get timing() { return timing; },
    get room() { return room; },
    get capture() { return capture; },
    get rate() { return rate; },
    get lastError() { return lastError; },
    get context() { return ctx; },
  };
}
