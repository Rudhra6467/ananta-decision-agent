// The voice conversation as ONE state machine: off -> listening -> thinking -> speaking -> listening ...
//
// Why: before, the mic, the network call and the voice each kept their own flags and callbacks, so a tap at the wrong
// moment (or a late answer) could leave Ananta "speaking" or "listening" forever. Now:
//  - every step that waits (mic, network, voice) belongs to a numbered turn; a result from an old turn is ignored;
//  - a tap on the orb always does the obvious thing for that moment, and extra taps are harmless;
//  - a watchdog (tick, once a second) repairs anything stuck: a mic that isn't recording, a question that never
//    came back, a voice that never finished.
// No React or Expo in here, so it can be tested with plain Node (see scripts/voiceloop.test.mjs).
//
// Listening has two moments (Madhav, repair #74, Oct 20: his first word was lost when he talked as soon as the orb said
// "listening"): "opening" (the mic is getting ready) and "live" (sound is really being captured). onListening tells the
// screen which, so it says "listening" only once the mic really hears.

export type Phase = "off" | "listening" | "thinking" | "speaking";

export type MicState = "idle" | "listening" | "hearing" | "sending";

export type ListenState = "opening" | "live";

export type LoopFx = {
  // start recording; force = restart even if it seems to be running. The mic must check wanted() right before it
  // starts (its operations are queued), so a start that is no longer wanted (voice ended, question sent) never records.
  micStart: (force: boolean, wanted: () => boolean) => Promise<boolean>;
  micStop: () => Promise<void>;                   // stop recording and throw it away (always, even if a start is queued)
  micSend: () => void;                            // stop recording now and deliver what was said (-> onAudio)
  micBusy: () => boolean;                         // really recording (or handing over what it heard)
  micState: () => MicState;                       // hearing = he is talking; sending = handing over what he said
  ask: (audioB64: string, current: () => boolean) => Promise<any>;   // transcribe + answer; never throws (returns {error})
  askText?: (q: string, current: () => boolean) => Promise<any>;     // a tapped question while voice is on (Oct 16): answer it aloud
  respond: (answer: any, current: () => boolean) => Promise<void>; // move the screen + speak; resolves when finished or stopped
  stopSpeaking: () => void;                       // cut the voice off (its respond() resolves)
  onPhase: (p: Phase) => void;
  onListening?: (s: ListenState) => void;          // while listening: "opening" until micStart really started, then "live"
  micClose?: () => void;                          // voice ended: let the microphone go (the web keeps one mic open per conversation)
  settleMs?: number;                              // wait after Ananta speaks before listening (iPhone app: 250; web: 0, the mic stays open)
  onNote?: (msg: string) => void;                 // a short message for the screen
  now?: () => number;
  sleep?: (ms: number) => Promise<void>;
};

export const LIMITS = { thinkingMs: 65000, speakingMs: 120000, micDeadMs: 2500, micRetries: 3 };   // thinking > the 60 s request timeout

export class VoiceLoop {
  phase: Phase = "off";
  turn = 0;
  private since = 0;
  private micDeadSince: number | null = null;
  private fx: LoopFx;
  private listenSeq = 0;                          // only the newest listen() may say "live"
  private spokeEnd: number | null = null;         // when Ananta last finished speaking (for the timing telemetry)
  live = false;                                   // listening AND the mic really started
  lastGapMs: number | null = null;                // Ananta finished speaking -> mic live, for the listen that followed it (else null)

  constructor(fx: LoopFx) { this.fx = fx; }

  private now() { return this.fx.now ? this.fx.now() : Date.now(); }
  private wait(ms: number) { return this.fx.sleep ? this.fx.sleep(ms) : new Promise<void>((r) => setTimeout(r, ms)); }
  private set(p: Phase) {
    if (this.phase === p) return;
    this.phase = p;
    if (p !== "listening") this.live = false;
    this.since = this.now();
    this.micDeadSince = null;
    this.fx.onPhase(p);
  }

  get on() { return this.phase !== "off"; }

  // The wave button. Tapping it again while voice is on does nothing.
  start() {
    if (this.phase !== "off") return;
    this.turn++;
    this.spokeEnd = null;
    this.lastGapMs = null;
    this.listen(this.turn, true);
  }

  // "End voice": everything stops, whatever it was doing.
  end() {
    if (this.phase === "off") return;
    this.turn++;
    this.live = false;
    this.set("off");
    this.fx.stopSpeaking();
    // stop the mic, then let it go, unless voice was started again meanwhile
    this.fx.micStop().catch(() => {}).then(() => { if (this.phase === "off") this.fx.micClose?.(); });
  }

  // The orb. One tap always does the obvious thing for that moment:
  //  speaking -> stop talking and listen now;  thinking -> drop this question and listen now;
  //  listening while he talks -> send it now;  listening and quiet -> restart the mic (fixes a stuck mic).
  tap() {
    switch (this.phase) {
      case "speaking":
      case "thinking":
        this.turn++;
        this.fx.stopSpeaking();
        this.listen(this.turn, true);
        return;
      case "listening": {
        const m = this.fx.micState();
        if (m === "hearing") this.fx.micSend();
        else if (m !== "sending") this.listen(this.turn, true);   // "sending": it is already handing over what he said
        return;
      }
      default:
        return;
    }
  }

  // The app came back to the front (iOS stops the mic in the background): if it was listening, listen again now.
  resume() {
    if (this.phase === "listening") this.listen(this.turn, true);
  }

  // Something else is about to use the speaker (e.g. a voice sample): only while quietly listening; pauses the mic,
  // plays, then listens again. Returns false (and does nothing) while he talks or Ananta thinks / speaks.
  async aside(fn: () => Promise<void>): Promise<boolean> {
    if (this.phase === "off") { await fn(); return true; }
    if (this.phase !== "listening" || this.fx.micState() === "hearing" || this.fx.micState() === "sending") return false;
    const my = ++this.turn;
    this.set("speaking");
    await this.fx.micStop().catch(() => {});
    if (my !== this.turn) return false;              // tapped or ended meanwhile
    try { await fn(); } catch { /* */ }
    if (my === this.turn) this.listen(my, true);
    return true;
  }

  // Still busy on purpose (e.g. a long guided tour, one step at a time): keeps the watchdog from cutting it off.
  touch() {
    this.since = this.now();
  }

  private listen(turn: number, force: boolean) {
    if (turn !== this.turn) return;
    this.set("listening");
    const seq = ++this.listenSeq;
    this.live = false;
    this.fx.onListening?.("opening");
    const wanted = () => turn === this.turn && this.phase === "listening";
    const run = async () => {
      for (let i = 0; i < LIMITS.micRetries; i++) {
        if (!wanted()) return;
        let ok = false;
        try { ok = await this.fx.micStart(force || i > 0, wanted); } catch { ok = false; }
        if (ok) {
          if (wanted() && seq === this.listenSeq) {           // a newer listen (a tap, a restart) speaks for itself
            this.live = true;
            const t = this.now();
            this.lastGapMs = this.spokeEnd !== null ? Math.max(0, t - this.spokeEnd) : null;
            this.spokeEnd = null;
            this.fx.onListening?.("live");
          }
          return;
        }
        await this.wait(400 + 300 * i);
      }
      if (turn === this.turn && this.phase === "listening") this.fx.onNote?.("The microphone didn't start. Tap the orb to try again.");
    };
    run();
  }

  // ---- mic events ----
  onNoSpeech() {
    if (this.phase === "listening") this.listen(this.turn, false);
  }

  async onAudio(b64: string) {
    if (this.phase !== "listening") return;          // voice was ended / interrupted meanwhile: drop it
    const my = ++this.turn;
    this.live = false;
    this.set("thinking");
    let r: any;
    try { r = await this.fx.ask(b64, () => my === this.turn); } catch (e: any) { r = { error: e?.message ?? String(e) }; }
    await this.answer(my, r);
  }

  // A question tapped while voice is on (a chip on an answer, a section's question; Madhav, Oct 16): the mic stops, the
  // question is asked as text, the answer is spoken, then it listens again. Same turn rules as a spoken question.
  async onText(q: string) {
    if (this.phase === "off" || !this.fx.askText) return;
    const my = ++this.turn;
    this.fx.stopSpeaking();
    await this.fx.micStop().catch(() => {});
    if (my !== this.turn) return;                     // tapped or ended meanwhile
    this.set("thinking");
    let r: any;
    try { r = await this.fx.askText(q, () => my === this.turn); } catch (e: any) { r = { error: e?.message ?? String(e) }; }
    await this.answer(my, r);
  }

  // Ananta says something of its own while voice is on (the section voice button: what this section is). Whatever it was doing
  // stops, it speaks, then listens again. A tap or End while it speaks wins, as always. Returns true if it finished speaking.
  async interject(fn: () => Promise<unknown>): Promise<boolean> {
    if (this.phase === "off") return false;
    const my = ++this.turn;
    this.fx.stopSpeaking();
    await this.fx.micStop().catch(() => {});
    if (my !== this.turn) return false;
    this.set("speaking");
    try { await fn(); } catch { /* */ }
    if (my !== this.turn) return false;
    if (!(await this.settle(my))) return false;
    this.listen(my, false);
    return true;
  }

  // After Ananta speaks: on the iPhone app wait a moment (the phone switches from speaker to microphone); on the web the mic
  // stays open, so listen at once. False if tapped or ended meanwhile.
  private async settle(my: number): Promise<boolean> {
    this.spokeEnd = this.now();
    const ms = this.fx.settleMs ?? 250;
    if (ms > 0) await this.wait(ms);
    return my === this.turn;
  }

  private async answer(my: number, r: any) {
    if (my !== this.turn) return;                     // tapped or ended while thinking: this answer is not spoken
    if (!r || (!r.heard && !r.answer && !r.error && !r.tour?.length)) { this.listen(my, false); return; }   // nothing was said
    this.set("speaking");
    try { await this.fx.respond(r, () => my === this.turn); } catch { /* */ }
    if (my !== this.turn) return;                     // interrupted: the tap already started listening
    if (!(await this.settle(my))) return;             // iPhone app: let the phone switch from speaker to microphone
    this.listen(my, false);
  }

  // ---- watchdog: call once a second ----
  tick() {
    if (this.phase === "off") return;
    const now = this.now();
    if (this.phase === "listening") {
      if (this.fx.micBusy()) { this.micDeadSince = null; return; }
      if (this.micDeadSince === null) { this.micDeadSince = now; return; }
      if (now - this.micDeadSince >= LIMITS.micDeadMs) { this.micDeadSince = null; this.listen(this.turn, true); }
      return;
    }
    const age = now - this.since;
    if (this.phase === "thinking" && age > LIMITS.thinkingMs) {
      this.turn++;
      this.fx.onNote?.("That took too long, so I stopped waiting. Please ask again.");
      this.listen(this.turn, true);
      return;
    }
    if (this.phase === "speaking" && age > LIMITS.speakingMs) {
      this.turn++;
      this.fx.stopSpeaking();
      this.listen(this.turn, true);
    }
  }
}
