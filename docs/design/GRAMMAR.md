# One grammar, five screens (Oct 14, 2026)

Madhav rated the dark mode 6.5/10 and asked how an outside designer would redraw the app so it is consistent, easy to understand
and gives him the most use. The answer was not a new palette: the gold, the charcoal and the names Home / Books / Ask Ananta stay.
The points were lost on structure: every card had its own shape, the faint grey was below the readable line, gold and green/red
were used for information as well as for actions, and three things fought for Home. These six rules fix that. If a new card cannot
be written in this shape, the card is wrong, not the rule. The design canvas (Claude Design, "Ananta redesign") shows the five
screens and this grammar; `jarvis/app/src/ui.tsx` and `theme.ts` carry it in code (`TYPE`, `LINE`, `SPACE`, `RADIUS`, `TAP`, `NUM`).

## 1. Five sizes, one font
32 the one number · 24 screen title · 17 card title · 15 body · 13 meta and labels · 11 tab labels only. The system font, with
tabular figures on every number (`NUM`). Spacing 16 (screen) · 14 (inside a card) · 12 (between cards) · 8 (between lines).
Corners 16 on cards, 12 on buttons, round on chips. Every row that can be tapped is 44 tall (`TAP`).

## 2. Colour is a role, not decoration
Ground #141518 · Card #1D1F23 · Raised #26292E (chips, inputs, your bubbles) · Line #33363C (dividers only) · Text #ECEAE6 ·
Dim #A9ACB2 (labels, meta) · Faint #8A8E96 (footnotes, 13 px and up; it was #7E828A, 4.3:1, too low) · Gold #F2CF66 for actions
only: buttons, links, the live tab, the selected segment · Good #5CCB92 and Bad #F2796F for numbers and health dots only, never
words or backgrounds · Warn #F2A65A for brakes and CAUTION only. tests/test_app_theme.py holds every pair to 4.5:1.

## 3. One card, one shape (`StatCard`)
Title (13 dim) → one number (32) → one line (15) → one action (13 gold). Three lines above the fold; everything else waits behind
More, opened in place. The same shape on Home (the account), Books (the result), Markets (the dial) and in Ananta's note.

## 4. Every list has four states (`ListState`)
Empty: one line and one action ("No watches yet." · + Watch). Loading: the shape of a row, not a spinner. Error: what happened and
one Retry. Content: a name, one fact, one number. An empty screen is never a wall of text.

## 5. Voice: three states that say their name
Listening (and Hearing you, with a Done button: no waiting for silence) · Thinking (Stop) · Speaking (Stop). Every reply is
labelled with its model, its language (English or తెలుగు, from the service's `language` field) and, when spoken, its voice, so a
switch is visible, never a surprise. The settings live in one place: More › Voice and model.

## 6. Words
Labels are nouns (Holdings, Cash, Dial); actions are verbs (Review, Approve, Show less). One currency per screen: C$ on the
account, US$ only inside the lab. Status in words first (OPEN, quiet, measuring), colour second. Anything technical gets a Why ›
beside it. Dates read "13 Oct 09:30": no seconds, no time zones. Ananta says "sir"; the interface never does.

## Where everything lives
| Tab | The question it answers | What lives here | What moved |
|---|---|---|---|
| Home | How is my account, and does anything need me? | the account card · Needs you (a rule that passed may step up; portfolio changes; the mandate's actions) · Ananta's note · one line for the lab · findings · activity | ten lines → three and More; the coins and the market rule → Markets; the lab's books → Books › Details › Lab |
| Books | What did the account trade, and how did each go? | Trades: the account alone (open, closed, fills against the bid/ask, Rules ›) · Details: Lab, Trend, Explorer, Mine, Setups · retired strategies | the lab's US$ books → Details › Lab |
| Ask Ananta | Talk, in English or Telugu. | chat and voice · chips · liked replies · every answer labelled · deep links into Books and Markets | voice and model settings → More; the header keeps one label |
| Markets (was Watchlists) | What is the market doing, and what are we watching? | the trend dial and brakes first, with Why › · watches · the coins · the whole market · reasoning · nearing a trade | the dial first; one-line empty state |
| More (was Cockpit) | Settings, evidence, and is everything running? | who is signed in · Controls · Voice and model · Evidence · System · notifications | voice settings from Cockpit and Ask → here; the 3+2 tiles → rows with switches |

The route names (`watchlists`, `cockpit`) did not change, so every deep link and spoken command still lands; `appmap.py` names the
new tabs and keeps the old words as aliases.
