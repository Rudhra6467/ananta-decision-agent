// Plain-Node tests for the voice loop:  node --experimental-strip-types --no-warnings scripts/voiceloop.test.mjs
// The fake mic below follows src/mic.ts: operations run one after another (a queue), start() checks wanted() before it
// records, cancel() always stops. A monitor checks the one rule that matters most: the mic is NEVER recording while
// Ananta is thinking, speaking, or when voice mode is off.
import assert from "node:assert/strict";
import { VoiceLoop, LIMITS } from "../src/voiceloop.ts";

const tick = () => new Promise((r) => setImmediate(r));
const flush = async (n = 30) => { for (let i = 0; i < n; i++) await tick(); };

function makeMic(deliver, opts = {}) {
  const m = { status: "idle", recording: false, done: true, gen: 0, starts: 0, failStarts: opts.failStarts ?? 0, queue: Promise.resolve(), log: [] };
  const serial = (fn) => { const p = m.queue.then(fn, fn); m.queue = p.catch(() => {}); return p; };
  m.start = (force = false, wanted = () => true) => serial(async () => {
    if (!wanted()) return false;
    await tick();                                                   // permission
    if (!wanted()) return false;
    const live = m.status === "listening" || m.status === "hearing";
    if (live && !force && !m.done) return true;
    m.starts++;
    await tick(); await tick();                                     // stop old, audio mode, prepare
    if (!wanted()) { m.status = "idle"; return false; }
    if (m.failStarts > 0) { m.failStarts--; return false; }
    m.recording = true; m.done = false; m.gen++; m.status = "listening"; m.log.push(`REC on${force ? "!" : ""}`);
    return true;
  });
  m.finish = (send) => {
    if (m.done) return m.queue.then(() => undefined);
    const gen = m.gen; m.done = true; m.status = send ? "sending" : "idle";
    return serial(async () => {
      if (gen !== m.gen) return;
      m.recording = false; m.log.push("REC off"); await tick(); await tick();   // stop + read the file
      m.status = "idle"; if (send) deliver("b64-" + gen);
    });
  };
  m.cancel = () => { m.done = true; m.status = "idle"; return serial(async () => { if (m.recording) m.log.push("REC off"); m.recording = false; await tick(); m.done = true; m.status = "idle"; }); };
  m.busy = () => m.status === "sending" || m.status === "hearing" || (m.status === "listening" && !m.done && m.recording);
  return m;
}

function rig(opts = {}) {
  const log = [], bad = [];
  let clock = 1000, loop, answerFns = [], speakDone = null;
  const mic = makeMic((b) => loop.onAudio(b), opts);
  loop = new VoiceLoop({
    micStart: (f, w) => mic.start(f, w), micStop: () => mic.cancel(), micSend: () => { mic.finish(true); },
    micBusy: () => mic.busy(), micState: () => mic.status,
    ask: (b64, current) => new Promise((res) => { log.push(`ask:${b64}`); answerFns.push(res); }),
    respond: (r) => new Promise((res) => { log.push(`speak:${r.answer ?? r.error}`); speakDone = () => { speakDone = null; res(); }; }),
    stopSpeaking: () => { log.push("voice:stop"); if (speakDone) speakDone(); },
    onPhase: (p) => log.push(`phase:${p}`), onNote: (m) => log.push(`note:${m}`),
    now: () => clock, sleep: async () => { await tick(); },
  });
  const timer = setInterval(() => {
    if (mic.recording && (loop.phase === "thinking" || loop.phase === "speaking" || loop.phase === "off")) bad.push(`recording while ${loop.phase}`);
  }, 0);
  return {
    loop, mic, log, bad, adv: (ms) => { clock += ms; },
    answer: (r) => { const f = answerFns.shift(); f && f(r); },
    finishSpeaking: () => speakDone && speakDone(),
    say: async (b) => { mic.status = "hearing"; mic.finish(true); await flush(); },   // he talks, the detector sends it
    stop: () => clearInterval(timer),
  };
}
const ok = (t) => { assert.deepEqual(t.bad, [], "mic must never record while thinking / speaking / off"); t.stop(); };

// 1. Extra taps on the wave button do nothing; it listens once.
{ const t = rig(); t.loop.start(); t.loop.start(); t.loop.start(); await flush();
  assert.equal(t.loop.phase, "listening"); assert.equal(t.mic.starts, 1); ok(t); }

// 2. Normal turn: listening -> thinking -> speaking -> listening again, mic off while thinking and speaking.
{ const t = rig(); t.loop.start(); await flush();
  await t.say(); assert.equal(t.loop.phase, "thinking"); assert.ok(!t.mic.recording);
  t.answer({ heard: "how is btc", answer: "BTC is up." }); await flush();
  assert.equal(t.loop.phase, "speaking");
  t.finishSpeaking(); await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(t.mic.recording, "mic restarted after speaking"); ok(t); }

// 3. Tap while speaking (3 taps): stops the voice and listens right away. (The old dead end.)
{ const t = rig(); t.loop.start(); await flush(); await t.say();
  t.answer({ heard: "x", answer: "Long answer." }); await flush();
  t.loop.tap(); t.loop.tap(); t.loop.tap(); await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(t.mic.recording); assert.ok(t.log.includes("voice:stop")); ok(t); }

// 4. Tap while thinking: the late answer is NOT spoken; it listens.
{ const t = rig(); t.loop.start(); await flush(); await t.say();
  t.loop.tap(); await flush(); assert.equal(t.loop.phase, "listening");
  t.answer({ heard: "x", answer: "Late answer." }); await flush();
  assert.ok(!t.log.some((l) => l.startsWith("speak:"))); assert.equal(t.loop.phase, "listening"); ok(t); }

// 5. End while thinking: the answer arrives later and nothing happens; extra taps are harmless.
{ const t = rig(); t.loop.start(); await flush(); await t.say();
  t.loop.end(); t.loop.tap(); t.loop.tap();
  t.answer({ heard: "x", answer: "Too late." }); await flush();
  assert.equal(t.loop.phase, "off"); assert.ok(!t.log.some((l) => l.startsWith("speak:"))); assert.ok(!t.mic.recording); ok(t); }

// 6. Audio arriving after voice was ended is dropped.
{ const t = rig(); t.loop.start(); await flush(); t.loop.end();
  await t.loop.onAudio("stray"); await flush(); assert.ok(!t.log.includes("ask:stray")); ok(t); }

// 7. Tap while he talks sends it; tap while quiet restarts the mic.
{ const t = rig(); t.loop.start(); await flush();
  t.mic.status = "hearing"; t.loop.tap(); await flush(); assert.equal(t.loop.phase, "thinking");
  t.answer({ answer: "ok" }); await flush(); t.finishSpeaking(); await flush();
  const before = t.mic.starts; t.loop.tap(); await flush();
  assert.equal(t.mic.starts, before + 1); assert.ok(t.mic.log.at(-1) === "REC on!"); ok(t); }

// 8. Mic fails to start twice: it retries and gets there.
{ const t = rig({ failStarts: 2 }); t.loop.start(); await flush(60);
  assert.equal(t.loop.phase, "listening"); assert.ok(t.mic.recording); ok(t); }

// 9. Watchdog: a mic that silently stopped recording is restarted after ~2.5 s.
{ const t = rig(); t.loop.start(); await flush();
  t.mic.recording = false;
  t.loop.tick(); t.adv(1000); t.loop.tick(); t.adv(1600); t.loop.tick(); await flush();
  assert.ok(t.mic.recording, "watchdog restarted the mic"); ok(t); }

// 10. Watchdog: a question that never comes back is dropped after the limit; then it listens.
{ const t = rig(); t.loop.start(); await flush(); await t.say();
  t.adv(LIMITS.thinkingMs + 1); t.loop.tick(); await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(t.log.some((l) => l.startsWith("note:That took too long")));
  t.answer({ answer: "very late" }); await flush(); assert.ok(!t.log.some((l) => l.startsWith("speak:"))); ok(t); }

// 11. Nothing was said (empty transcript): straight back to listening.
{ const t = rig(); t.loop.start(); await flush(); await t.say();
  t.answer({ heard: "" }); await flush();
  assert.equal(t.loop.phase, "listening"); assert.ok(t.mic.recording); assert.ok(!t.log.some((l) => l.startsWith("speak:"))); ok(t); }

// 12. A voice sample while quietly listening: pauses the mic, plays, listens again. While thinking: refused.
{ const t = rig(); t.loop.start(); await flush();
  let played = false;
  const r = await t.loop.aside(async () => { assert.ok(!t.mic.recording, "mic paused during the sample"); played = true; }); await flush();
  assert.ok(r && played); assert.equal(t.loop.phase, "listening"); assert.ok(t.mic.recording);
  await t.say(); const r2 = await t.loop.aside(async () => { throw new Error("must not play"); });
  assert.equal(r2, false); assert.equal(t.loop.phase, "thinking"); ok(t); }

// 13. Errors are spoken (so he knows), then it listens again.
{ const t = rig(); t.loop.start(); await flush(); await t.say();
  t.answer({ error: "network down" }); await flush();
  assert.equal(t.loop.phase, "speaking"); t.finishSpeaking(); await flush();
  assert.equal(t.loop.phase, "listening"); ok(t); }

// 14. Back from the background while listening: mic restarted; while speaking: no change.
{ const t = rig(); t.loop.start(); await flush();
  t.mic.recording = false; const before = t.mic.starts; t.loop.resume(); await flush();
  assert.equal(t.mic.starts, before + 1); assert.ok(t.mic.recording);
  await t.say(); t.answer({ answer: "Hi." }); await flush();
  const n = t.mic.starts; t.loop.resume(); await flush();
  assert.equal(t.mic.starts, n, "no mic restart while speaking"); t.finishSpeaking(); await flush(); ok(t); }

// 15. (review #1) Double tap while it is handing over what he said: the extra tap is ignored, no stray recording.
{ const t = rig(); t.loop.start(); await flush();
  t.mic.status = "hearing"; t.loop.tap(); t.loop.tap(); await flush();
  assert.equal(t.loop.phase, "thinking"); assert.ok(!t.mic.recording);
  t.answer({ heard: "q", answer: "A." }); await flush(); assert.ok(!t.mic.recording, "not recording while speaking");
  t.finishSpeaking(); await flush(); assert.equal(t.loop.phase, "listening"); assert.ok(t.mic.recording); ok(t); }

// 16. (review #2) End voice while a mic start is still queued: it never starts recording.
{ const t = rig(); t.loop.start(); t.loop.end(); await flush();
  assert.equal(t.loop.phase, "off"); assert.ok(!t.mic.recording); ok(t); }
{ const t = rig(); t.loop.start(); await flush(); t.loop.tap(); t.loop.end(); await flush();
  assert.ok(!t.mic.recording, "restart queued by a tap must not record after End"); ok(t); }

// 17. Rapid mixed taps never leave it stuck: always ends up listening with the mic on, cancelled answers never spoken.
{ const t = rig(); t.loop.start(); await flush();
  for (let k = 0; k < 6; k++) {
    await t.say(); t.loop.tap(); t.loop.tap();
    t.answer({ answer: "A" + k }); await flush(3); t.loop.tap(); await flush();
  }
  assert.equal(t.loop.phase, "listening"); assert.ok(t.mic.recording);
  assert.ok(!t.log.some((l) => l.startsWith("speak:")), "answers to cancelled questions are never spoken"); ok(t); }

// 18. A long tour keeps itself alive with touch(): the watchdog does not cut it off.
{ const t = rig(); t.loop.start(); await flush(); await t.say();
  t.answer({ tour: [1, 2, 3], answer: "Tour" }); await flush();
  for (let i = 0; i < 6; i++) { t.adv(60000); t.loop.touch(); t.loop.tick(); }
  assert.equal(t.loop.phase, "speaking"); t.finishSpeaking(); await flush(); assert.equal(t.loop.phase, "listening"); ok(t); }

console.log("voice loop: all 19 checks passed (mic never recorded while thinking, speaking or off)");
process.exit(0);
