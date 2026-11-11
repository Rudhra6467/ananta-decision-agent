"""The redesign's shared kit (Madhav, 10 Nov 2026: "yes for all your recommendations. lets complete it and test it as planned").

A place (Home, Markets, Activity, More) or a page under it is a short list of PARTS, and every part is one of the twelve building blocks
the design canvas drew: hero number, summary box, row, section with a chevron, chip line, tile grid, information page, receipt, notice
card, the bell, bottom sheet, floating tab bar. The server writes the parts in plain words; the app only draws them. So a wording fix
needs no new app build, and the eight rules of the redesign are checked here, on the payload, by problems() (tests/test_places.py):

  1. one number and one sentence at the top of a screen       5. colour only for meaning (a tone is "good", "bad" or "warn")
  2. a row is a name, a grey label and a number               6. one main button, pinned, on a page
  3. three rows per section on an overview, then a chevron    7. a locked thing says what unlocks it
  4. a card has at most three points of ten words             8. every label can be read by a first-time reader

Nothing here reads a market or changes anything: it is shapes and counting only."""
from __future__ import annotations

import re

OVERVIEWS = ("home", "markets", "more")          # rules 3 and 4 are for these first layers
TONES = (None, "good", "bad", "warn")
PART_TYPES = ("hero", "today", "boxes", "peek", "rows", "chips", "tiles", "pill", "heading", "line", "points", "trust", "kv", "notices",
              "bars", "split", "chart", "link", "identity", "counts", "needs", "pricechart")     # needs: the app fills it from /v3/place/needs (the open list)
# word budgets (rule 2 to 4 and 8); the app's row is cut at one line anyway, the budget keeps the words whole
MAX = {"row_title": 6, "row_sub": 9, "row_right": 4, "today_line": 9, "today_sub": 13, "notice": 11, "point_overview": 10, "points_overview": 3,
       "rows_overview": 3, "tile_label": 3, "tile_value": 4, "chip": 4, "box_label": 3, "box_caption": 6, "foot": 16, "page_line": 22,
       "home_words": 150, "markets_words": 170, "more_words": 110}


def nwords(s) -> int:
    return len(str(s or "").split())


SMALL = {"a", "an", "the", "of", "to", "and", "or", "on", "at", "in", "for", "with", "its", "is", "are", "was", "by", "from", "as", "that", "when", "but", "it"}


def clip(s, words: int = 8, chars: int = 46) -> str:
    """The first words of a sentence, whole words only, never past a full stop; "…" when something was left out."""
    s = re.sub(r"\s+", " ", str(s or "")).strip()
    first = re.split(r"(?<=[^0-9])\.\s|(?<=\d)\.\s(?=[A-Z])", s, maxsplit=1)[0].rstrip(".")
    out = []
    for w in first.split():
        if len(out) >= words or len(" ".join(out + [w])) > chars:
            break
        out.append(w)
    while len(out) > 2 and out[-1].lower().strip(",;:") in SMALL and len(" ".join(out)) < len(first):
        out.pop()
    t = " ".join(out).rstrip(",;:·(—-")
    return t + ("…" if len(t) < len(first) else "")


def title_sub(line: str, title_words: int = 6, sub_words: int = 8) -> tuple[str, str]:
    """An open-list line written as "Title: the rest." gives a row its name and its grey label; a line with no colon is cut by words."""
    s = re.sub(r"\s+", " ", str(line or "")).strip()
    m = re.match(r"^([^:.]{3,44}):\s+(.+)$", s)
    if m and nwords(m.group(1)) <= title_words:
        rest = m.group(2).strip()
        return m.group(1).strip(), clip(rest[:1].upper() + rest[1:], sub_words, 44)
    sents = [x for x in re.split(r"(?<=[a-z0-9)])\.\s+(?=[A-Z])", s) if x.strip()]
    t = clip(sents[0], title_words, 34) if sents else ""
    rest = sents[1] if len(sents) > 1 else ""
    return t, clip(rest, sub_words, 44) if rest else ""


def _drop(d: dict) -> dict:
    return {k: v for k, v in d.items() if v is not None and v != [] and v != ""}


# ---- where a tap goes
def tab(name: str) -> dict:
    return {"tab": name}


def place(name: str) -> dict:
    return {"place": name}


def ask(q: str) -> dict:
    return {"ask": q}


def route(path: str) -> dict:
    return {"route": path}


def to_page(p: dict | None) -> dict | None:
    return {"page": p} if p else None


def sheet(title: str, text: str, advice: str | None = None, icon: str = "you", primary: dict | None = None, secondary: str = "Not now",
          key: str | None = None, answers: list | None = None) -> dict:
    """answers (11 Nov 2026): what he can answer right there, [{"id": "yes"|"no"|"done"|"later", "label": ...}], sent with the item's key to
    /v3/openlist/answer. An older app shows primary and secondary as before."""
    return {"sheet": _drop({"icon": icon, "title": title, "text": text, "advice": advice, "primary": primary, "secondary": secondary, "key": key,
                            "answers": answers or None})}


# ---- the parts
def hero(label, value, change=None, tone=None, since=None, status=None) -> dict:
    return _drop({"t": "hero", "label": label, "value": value, "change": change, "tone": tone, "since": since, "status": status})


def today(label, line, sub, to=None) -> dict:
    return _drop({"t": "today", "label": label, "line": line, "sub": sub, "to": to})


def box(label, value, change=None, tone=None, since=None, spark=None, bar=None, caption=None, to=None) -> dict:
    return _drop({"label": label, "value": value, "change": change, "tone": tone, "since": since, "spark": spark, "bar": bar, "caption": caption, "to": to})


def paged(pages) -> dict | None:
    """One box, several numbers swiped up inside it (Madhav, 10 Nov 14:46: "like we use to show banknifty and nift 50 in one box")."""
    ps = [p for p in pages if p]
    if not ps:
        return None
    return {**ps[0], "pages": ps} if len(ps) > 1 else ps[0]


def boxes(items) -> dict:
    return {"t": "boxes", "items": [x for x in items if x]}


def peek(items, note=None, tags=None) -> dict:
    return _drop({"t": "peek", "items": [x for x in items if x], "note": note, "tags": tags})


def row(title, sub=None, right=None, tone=None, icon=None, tint=None, to=None, right_sub=None, right_tone=None, chip=None, tag=None, letter=None, grade=None) -> dict:
    return _drop({"title": title, "sub": sub, "right": right, "tone": tone, "icon": icon, "tint": tint, "to": to, "right_sub": right_sub,
                  "right_tone": right_tone, "chip": chip, "tag": tag, "letter": letter, "grade": grade})


def rows(title, items, count=None, more=None, foot=None, badge=False, sub=None, tags=None, plain=False) -> dict:
    return _drop({"t": "rows", "title": title, "rows": [x for x in items if x], "count": count, "more": more, "foot": foot, "badge": badge or None,
                  "sub": sub, "tags": tags, "plain": plain or None})


def chips(items) -> dict:
    return {"t": "chips", "items": [_drop(x) for x in items]}


def tile(label, value=None, icon="dot", tint=None, to=None, quiet=False) -> dict:
    return _drop({"label": label, "value": value, "icon": icon, "tint": tint, "to": to, "quiet": quiet or None})


def tiles(title, items) -> dict:
    return {"t": "tiles", "title": title, "items": [x for x in items if x]}


def pill(text, tone=None, icon=None) -> dict:
    return _drop({"t": "pill", "text": text, "tone": tone, "icon": icon})


def heading(text) -> dict:
    return {"t": "heading", "text": text}


def line(text) -> dict:
    return {"t": "line", "text": text}


def points(items, title=None) -> dict:
    return _drop({"t": "points", "title": title, "items": [({"text": x} if isinstance(x, str) else _drop(x)) for x in items if x]})


def trust(text) -> dict:
    return {"t": "trust", "text": text}


def kvrow(k, v, k_sub=None, v_sub=None, tone=None, bold=False) -> dict:
    return _drop({"k": k, "v": v, "k_sub": k_sub, "v_sub": v_sub, "tone": tone, "bold": bold or None})


def kv(items, title=None, foot=None) -> dict:
    return _drop({"t": "kv", "title": title, "rows": [x for x in items if x], "foot": foot})


def notices(items) -> dict:
    return {"t": "notices", "items": [_drop(x) for x in items if x]}


def notice(nid, text, to=None) -> dict:
    return {"id": nid, "line": text, "to": to}


def bars(items, title=None) -> dict:
    return _drop({"t": "bars", "title": title, "items": [_drop(x) for x in items if x]})


def bar(name, done, need, right=None, note=None) -> dict:
    return {"name": name, "done": done, "need": need, "right": right, "note": note}


def split(parts, title=None) -> dict:
    return _drop({"t": "split", "title": title, "parts": [_drop(p) for p in parts if p]})


def chart(lines, left=None, right=None, legend=None, caption=None, label=None, baseline=None) -> dict:
    """lines: [{"values": [...], "style": "main" | "dash" | "dot", "color": "ink" | "bronze" | "dim", "last_dash": n}]; one shared scale."""
    return _drop({"t": "chart", "lines": [_drop(x) for x in lines if x and x.get("values")], "left": left, "right": right, "legend": legend,
                  "caption": caption, "label": label, "baseline": baseline})


def pricechart(sym: str, name: str, kind: str = "candles", rng: str | None = None, tf: str | None = None, private: bool = False, caption: str | None = None) -> dict:
    """A chart the app fetches itself (/v3/candles/<sym>?range=&tf=) with its range and timeframe chips (jarvis/chartkit.py). kind: candles for
    a price, line for a history of the account; private: the amounts hide with the hide button."""
    return _drop({"t": "pricechart", "sym": sym, "name": name, "kind": kind, "range": rng, "tf": tf, "private": private or None, "caption": caption})


def link(label, to) -> dict:
    return {"t": "link", "label": label, "to": to}


def identity(text) -> dict:
    return {"t": "identity", "line": text}


def counts(title, items, to=None) -> dict:
    return _drop({"t": "counts", "title": title, "items": items, "to": to})


def page(title: str, parts: list, ask_q: str | None = None, second: dict | None = None, bar_kind: str = "back") -> dict:
    """A page one tap down: its own short list of parts, one main button pinned (rule 6), and at most one quiet second button."""
    return _drop({"kind": "page", "title": title, "bar": bar_kind, "parts": [p for p in parts if p],
                  "pinned": _drop({"ask": ask_q, "second": second}) if (ask_q or second) else None})


def surface(name: str, market: str, parts: list, bell: int = 0, title: str | None = None, ask_q: str | None = None, second: dict | None = None, **more) -> dict:
    out = {"ready": True, "kind": "place", "name": name, "market": market, "title": title, "bell": {"count": int(bell or 0)},
           "parts": [p for p in parts if p], "paper": True}
    if ask_q or second:
        out["pinned"] = _drop({"ask": ask_q, "second": second})
    out.update(more)
    return _drop(out)


def thin(values, n: int = 30) -> list:
    """A long series as about n points, the last one kept (a small chart needs no more)."""
    v = [x for x in (values or []) if isinstance(x, (int, float))]
    if len(v) <= n:
        return [round(x, 2) for x in v]
    k = len(v) / n
    out = [v[min(len(v) - 1, int(i * k))] for i in range(n - 1)] + [v[-1]]
    return [round(x, 2) for x in out]


# ---- the rules, checked on the payload
def _texts(x):
    """Every string a person would read in a payload (labels, values, lines), for counting."""
    if isinstance(x, dict):
        for k, v in x.items():
            if k in ("t", "icon", "tint", "tone", "right_tone", "tag", "tags", "id", "to", "more", "kind", "bar", "name", "market", "letter", "grade", "style", "color", "page", "pages"):   # a paged box shows one page at a time: its first is counted where it sits
                continue
            yield from _texts(v)
    elif isinstance(x, list):
        for v in x:
            yield from _texts(v)
    elif isinstance(x, str):
        yield x


def words_on(payload: dict) -> int:
    return sum(nwords(s) for s in _texts(payload.get("parts") or []))


def pages_in(x):
    """Every page reachable by one tap from a payload (they ride inside it)."""
    if isinstance(x, dict):
        if isinstance(x.get("page"), dict):
            yield x["page"]                      # problems() goes into it; its own pages are found there
        for k, v in x.items():
            if k != "page":
                yield from pages_in(v)
    elif isinstance(x, list):
        for v in x:
            yield from pages_in(v)


def problems(name: str, payload: dict, _depth: int = 0) -> list[str]:
    """What breaks the eight rules in one place or page. An empty list is a pass."""
    out: list[str] = []
    over = name in OVERVIEWS
    parts = payload.get("parts") or []
    say = lambda why, what="": out.append(f"{name}: {why}" + (f": {str(what)[:70]}" if what else ""))   # noqa: E731
    if sum(1 for p in parts if p.get("t") == "hero") > 1:
        say("more than one hero number (rule 1)")
    for p in parts:
        t = p.get("t")
        if t not in PART_TYPES:
            say("a part that is not one of the building blocks", t)
        for k in ("tone",):
            if p.get(k) not in TONES:
                say("a tone that is not good, bad or warn (rule 5)", p.get(k))
        if t == "today":
            if nwords(p.get("line")) > MAX["today_line"]:
                say("today's line is too long (rule 1)", p.get("line"))
            if nwords(p.get("sub")) > MAX["today_sub"]:
                say("today's second line is too long (rule 1)", p.get("sub"))
        if t == "rows":
            rs = p.get("rows") or []
            filtered = bool(p.get("tags")) and "all" not in p["tags"]      # a chip's own list is the whole list, shown only when that chip is on
            if over and not filtered and len(rs) > MAX["rows_overview"]:
                say(f"{len(rs)} rows in one section on an overview (rule 3)", p.get("title"))
            if over and len(rs) >= MAX["rows_overview"] and p.get("count") and p["count"] > len(rs) and not p.get("more"):
                say("more rows exist and no chevron opens them (rule 3)", p.get("title"))
            if nwords(p.get("foot")) > MAX["foot"]:
                say("a section's small print is too long", p.get("foot"))
            for r in rs:
                if nwords(r.get("title")) > MAX["row_title"]:
                    say("a row's name is too long (rule 2)", r.get("title"))
                if nwords(r.get("sub")) > MAX["row_sub"] or re.search(r"[a-z]\. [A-Z]", str(r.get("sub") or "")):
                    say("a row's grey label is a sentence (rule 2)", r.get("sub"))
                if nwords(r.get("right")) > MAX["row_right"]:
                    say("a row's right side is not a number or a word (rule 2)", r.get("right"))
                for k in ("tone", "right_tone"):
                    if r.get(k) not in TONES:
                        say("a tone that is not good, bad or warn (rule 5)", r.get(k))
        if t == "points" and over:
            its = p.get("items") or []
            if len(its) > MAX["points_overview"]:
                say("more than three points on an overview (rule 4)")
            for i in its:
                if nwords(i.get("text")) > MAX["point_overview"]:
                    say("a point of more than ten words on an overview (rule 4)", i.get("text"))
        if t == "notices":
            for n in p.get("items") or []:
                if nwords(n.get("line")) > MAX["notice"]:
                    say("a notice of more than one short line", n.get("line"))
        if t == "tiles":
            for x in p.get("items") or []:
                if nwords(x.get("label")) > MAX["tile_label"] or nwords(x.get("value")) > MAX["tile_value"]:
                    say("a tile with too many words", f"{x.get('label')} / {x.get('value')}")
                if x.get("quiet") and not x.get("to"):
                    say("a thing not set up yet that does not say what sets it up (rule 7)", x.get("label"))
        if t == "chips":
            for c in p.get("items") or []:
                if nwords(c.get("label")) > MAX["chip"]:
                    say("a chip with too many words", c.get("label"))
        if t in ("boxes", "peek"):
            if t == "boxes" and len(p.get("items") or []) > 2:
                say("more than two boxes in a row", len(p["items"]))
            for b in [x for it in p.get("items") or [] for x in (it.get("pages") or [it])]:
                if nwords(b.get("label")) > MAX["box_label"] or nwords(b.get("caption")) > MAX["box_caption"]:
                    say("a box with too many words", f"{b.get('label')} / {b.get('caption')}")
        if t == "line" and nwords(p.get("text")) > MAX["page_line"]:
            say("a page's one line is too long", p.get("text"))
    if over and words_on(payload) > MAX.get(name + "_words", 10 ** 6):
        say(f"{words_on(payload)} words on the screen, over the budget of {MAX[name + '_words']}")
    if payload.get("kind") == "page":
        if not (payload.get("pinned") or {}).get("ask"):
            say("a page with no main button (rule 6)", payload.get("title"))
    if _depth < 3:
        for pg in pages_in(parts):
            out += problems(f"{name} › {pg.get('title') or 'page'}", pg, _depth + 1)
    return out
