"""The headline figures of a company's results filing (9 Nov 2026; Madhav, 19:51 Toronto: "Yes to all your recommendations", recommendation 3).

The holdings' lines of the morning view said "Tata Chemicals filed its results" and nothing about the results. Since 2025 a listed company
files its quarter as one "integrated filing" with a data file (XBRL) at NSE; Ananta had the list of those filings but had not read a figure
from one (its older reader covers the pre-2025 format only, and the files of the newest quarter had not been downloaded).

  parse(xml)                      the top line (revenue; net premium for insurers; total income for banks), the profit for the period and
                                  basic EPS of the QUARTER (the filing's own quarter context), with the period, consolidated or standalone,
                                  audited or not; None when not readable
  headline(symbols, since)        for each named stock with a results filing broadcast since `since`: the consolidated filing's figures
                                  (standalone when there is no consolidated one) and the change on the same quarter a year before

Which filings may be read is decided and logged by india/sealed.py (read_filings, purpose holdings_results): only the named holdings' new
filings and each one's year-ago filing. A new filing's file is fetched once from NSE's archive (one polite request) and kept under
bronze/xbrl_live, apart from the research download; older files are read from bronze/xbrl where the research download has them. When
the figures cannot be read the line simply says what was filed. A profit that follows a loss, or a loss, is said with last year's figure,
never as a percentage. Display only: no rule reads this.
"""
from __future__ import annotations

import datetime as dt
import re

from india import paths

PURPOSE = "holdings_results"
CRORE = 1e7


def _fact(xml: str, tag: str, ctx: str = "OneD") -> str | None:
    m = re.search(r"<in-capmkt:" + tag + r"\b[^>]*contextRef=\"" + ctx + r"\"[^>]*>([^<]*)<", xml)
    return m.group(1).strip() if m and m.group(1).strip() else None


def _num(v: str | None) -> float | None:
    try:
        return float(v) if v is not None else None
    except ValueError:
        return None


# the top line and the profit line, by the kind of filing: companies and NBFCs (revenue from operations), life and general insurers (net
# premium), banks (total income). The first tag present decides.
TOP = (("RevenueFromOperations", "revenue"), ("NetPremiumIncome", "net premium income"), ("NetPremiumWritten", "net premium written"), ("Income", "total income"))
PROFIT = ("ProfitLossForPeriod", "ProfitLossForThePeriod", "ProfitLossAfterTaxAndExtraordinaryItems", "ProfitLossAfterTax")


def parse(xml: str) -> dict | None:
    """The quarter's headline figures from one integrated filing's data file (context OneD: the reporting quarter), in rupees."""
    if not xml or "in-capmkt:" not in xml:
        return None
    top, label = next(((_num(_fact(xml, t)), lab) for t, lab in TOP if _num(_fact(xml, t)) is not None), (None, None))
    pat = next((_num(_fact(xml, t)) for t in PROFIT if _num(_fact(xml, t)) is not None), None)
    if top is None and pat is None:
        return None
    return {"top": top, "top_label": label, "profit": pat,
            "eps_basic": _num(_fact(xml, "BasicEarningsLossPerShareFromContinuingAndDiscontinuedOperations")),
            "period_start": _fact(xml, "DateOfStartOfReportingPeriod"), "period_end": _fact(xml, "DateOfEndOfReportingPeriod"),
            "nature": _fact(xml, "NatureOfReportStandaloneConsolidated"), "audited": _fact(xml, "WhetherResultsAreAuditedOrUnaudited"),
            "symbol": _fact(xml, "Symbol")}


def _file(url: str, fetch_new: bool, fetcher=None) -> str | None:
    """The filing's data file: from the research download, else from the live cache, else (a new filing only) one request to NSE's archive."""
    name = url.rsplit("/", 1)[-1]
    root = paths.data_dir() / "bronze"
    for p in list(root.glob(f"xbrl/*/{name}")) + list(root.glob(f"xbrl_live/*/{name}")):
        try:
            return p.read_text(encoding="utf-8", errors="replace")
        except OSError:
            continue
    if not fetch_new:
        return None
    try:
        if fetcher is None:
            from india import nse
            fetcher = nse.Fetcher(rate_s=1.5)
        st, body, _ = fetcher.get(url)
    except Exception:  # noqa: BLE001
        return None
    if st != 200 or not body.lstrip()[:5] == b"<?xml":
        return None
    out = root / "xbrl_live" / str(dt.date.today().year) / name
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(body)
    return body.decode("utf-8", errors="replace")


def _pct(now: float | None, was: float | None) -> float | None:
    if now is None or was is None or was <= 0:
        return None          # a change from a loss or from nothing is not a percentage
    return round(100 * (now / was - 1), 1)


def headline(symbols: list[str], since: str, fetcher=None, filings: list[dict] | None = None) -> dict:
    """{symbol: {...figures, "yoy": {...}, "words": one sentence}} for the named stocks' results filings broadcast since `since`."""
    if filings is None:
        from india import sealed
        filings = sealed.read_filings(PURPOSE, symbols, since)
    out = {}
    new = [f for f in filings if f["role"] == "new"]
    for sym in sorted({f["symbol"] for f in new}):
        mine = sorted([f for f in new if f["symbol"] == sym], key=lambda f: (f["quarter_end"], f["consolidated"] == "Consolidated", f["broadcast"]))
        pick = mine[-1]                                   # the newest quarter; consolidated before standalone
        d = parse(_file(pick["url"], True, fetcher) or "")
        if not d:
            continue
        prev = next((f for f in filings if f["role"] == "year_ago" and f["symbol"] == sym and f["consolidated"] == pick["consolidated"]), None)
        was = parse(_file(prev["url"], False) or "") if prev else None
        same = bool(was) and was.get("top_label") == d.get("top_label")
        yoy = {"top_pct": _pct(d.get("top"), was.get("top")) if same else None, "top_was": was.get("top") if same else None,
               "profit_pct": _pct(d.get("profit"), was.get("profit")) if (d.get("profit") or 0) > 0 else None, "profit_was": was.get("profit")} if was else None
        out[sym] = {**d, "consolidated": pick["consolidated"], "quarter_end": str(pick["quarter_end"]), "broadcast": str(pick["broadcast"]), "yoy": yoy,
                    "source": pick["url"], "words": words(d, pick, yoy)}
    return out


def _cr(v: float) -> str:
    c = v / CRORE
    return f"₹{c:,.0f} crore" if abs(c) >= 100 else f"₹{c:,.1f} crore"


def words(d: dict, pick: dict, yoy: dict | None) -> str:
    q = pick["quarter_end"]
    y = yoy or {}
    bits = []
    if d.get("top") is not None:
        ch = y.get("top_pct")
        bits.append(f"{d['top_label']} {_cr(d['top'])}" + (f" ({ch:+.0f}% on the same quarter a year before)" if ch is not None else ""))
    if d.get("profit") is not None:
        ch, was = y.get("profit_pct"), y.get("profit_was")
        before = (f" ({ch:+.0f}%)" if ch is not None else
                  (f" (a year before: {'a loss of ' + _cr(-was) if was < 0 else 'a profit of ' + _cr(was)})" if was is not None else ""))
        bits.append((f"a profit for the quarter of {_cr(d['profit'])}" if d["profit"] >= 0 else f"a loss for the quarter of {_cr(-d['profit'])}") + before)
    kind = ("consolidated" if pick["consolidated"] == "Consolidated" else "standalone") + (", unaudited" if str(d.get("audited") or "").lower().startswith("un") else "")
    return f"For the quarter ended {q.day} {q:%b %Y} ({kind}): " + ", ".join(bits) + "."
