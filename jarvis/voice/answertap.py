"""Reads the "answer" out of a model's JSON while it is being written and hands each finished sentence on (5 Nov 2026, Madhav: "start
speaking while it's still writing the answer"). Shared by India's Ask (jarvis/india/ask.py) and the crypto Ask (jarvis/service/ask.py)."""
from __future__ import annotations

import re


class AnswerTap:
    """Reads the "answer" string out of the model's JSON while it is being written, and hands each finished sentence on (5 Nov 2026).
    The JSON is {"kind":..., "stage":..., "answer":"...", ...}; only the answer's characters are taken, JSON escapes decoded."""
    START = re.compile(r'"answer"\s*:\s*"')
    END_SENT = re.compile(r'(?<=[.!?])["”’)]?\s+(?=[A-Z0-9"“‘(₹])|\n+')

    def __init__(self, emit):
        self.emit, self.raw, self.pos, self.buf, self.done = emit, "", None, "", False

    def feed(self, piece: str) -> None:
        if self.done:
            return
        self.raw += piece
        if self.pos is None:
            m = self.START.search(self.raw)
            if not m:
                return
            self.pos = m.end()
        out, i, raw = [], self.pos, self.raw
        while i < len(raw):
            c = raw[i]
            if c == "\\":
                if i + 1 >= len(raw):
                    break
                n = raw[i + 1]
                if n == "u":
                    if i + 6 > len(raw):
                        break
                    try:
                        out.append(chr(int(raw[i + 2:i + 6], 16)))
                    except ValueError:
                        pass
                    i += 6
                    continue
                out.append({"n": "\n", "t": " ", "r": "", "b": "", "f": ""}.get(n, n))
                i += 2
                continue
            if c == '"':
                self.done = True
                i += 1
                break
            out.append(c)
            i += 1
        self.pos = i
        self.buf += "".join(out)
        self._sentences(final=self.done)

    ABBR = re.compile(r"(?:\b(?:Rs|vs|No|Dr|Mr|Mrs|St|approx|e\.g|i\.e|etc|Ltd|Inc|Co)\.)$", re.I)

    def _sentences(self, final: bool = False) -> None:
        start = 0
        while True:
            m = self.END_SENT.search(self.buf, start)
            if not m:
                break
            head = self.buf[:m.start()]
            if self.ABBR.search(head.rstrip("\"”’)")):         # "Rs. 478", "vs. 23,900": not the end of a sentence
                start = m.end()
                continue
            closing = self.buf[m.start():m.end()].strip()
            s, self.buf, start = (head + (closing if closing and closing in "\"”’)" else "")).strip(), self.buf[m.end():], 0
            if s:
                self.emit(s)
        if final and self.buf.strip():
            s, self.buf = self.buf.strip(), ""
            self.emit(s)

    def close(self) -> None:
        self._sentences(final=True)
