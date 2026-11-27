"""The live options rules in code (design part 2; INDIA_LOCK.md, decisions of 25 Nov; pass_marks_v1.md go-live item 6).

Live only: the paper line (SP1 v2) stays exactly as frozen and keeps running beside it. The live path follows the paper line's decisions
and never makes its own; these rules only decide whether a paper decision is also traded with real money.
  - Rs 75,000 of options money.
  - The 1-lot premium at the decision must be Rs 37,500 or less, or the trade is skipped ("over the cap").
  - At most one options position held overnight: a second decision that would also be held overnight is skipped while one is held.
    As in pre-live test T1: a position held overnight is one entered today whose exit is the next open (NEXTOPEN); a position from
    yesterday leaves at today's open and does not block today's decisions.
  - Exactly 1 lot.
  - Before every entry, Kite's margin calculator (a calculation, never an order) must confirm the money covers it.
Pure functions, except margin_check, which asks the calculator through india/kite.py's own basket_margin.
"""
from __future__ import annotations

from dataclasses import dataclass, field

OPTIONS_MONEY = 75_000
PREMIUM_CAP = 37_500
LOTS = 1
OVERNIGHT_EXIT = "NEXTOPEN"
INDEX_STOP_EXITS = ("ATRSTOP", "ORSTOP")
SKIP_CAP = "skip: premium over Rs 37,500"
SKIP_OVERNIGHT = "skip: one overnight position already held"
SKIP_MONEY = "skip: the options money does not cover it"
SKIP_NO_CONTRACT = "skip: no option contract recorded"


@dataclass(frozen=True)
class Plan:
    """One paper decision, as the live path reads it."""
    date: str
    index: str
    point: str
    exit: str
    tradingsymbol: str
    lot: int
    price: float                      # the option's quote at the decision (rupees per unit)
    expiry: str | None = None
    extra: dict = field(default_factory=dict, compare=False, hash=False)

    @property
    def premium(self) -> float:
        return float(self.price) * int(self.lot) * LOTS

    @property
    def overnight(self) -> bool:
        return self.exit == OVERNIGHT_EXIT


def plan_from_decision(d: dict) -> Plan | None:
    """A paper decision row (paper/sp1/decisions.jsonl, kind 'decision' with a choice) as a Plan; None when it chose nothing."""
    c = d.get("choice") or {}
    if d.get("kind") != "decision" or not c:
        return None
    opt = (d.get("contracts") or {}).get("option") or {}
    sym, lot = opt.get("tradingsymbol"), opt.get("lot")
    q = (d.get("quotes_at_decision") or {}).get(f"NFO:{sym}") if sym else None
    return Plan(date=d["date"], index=d["index"], point=d["point"], exit=c.get("exit") or "", tradingsymbol=sym or "",
                lot=int(lot or 0), price=float(q or 0), expiry=opt.get("expiry"))


def held_overnight(plan: Plan, held: list[Plan]) -> bool:
    """Is a position already going to be held overnight tonight? (entered today, exit at the next open)"""
    return any(h.overnight and h.date == plan.date for h in held)


def committed(plan: Plan, held: list[Plan]) -> float:
    """Premium already in open positions on the plan's day (yesterday's next-open position has left at today's open)."""
    return sum(h.premium for h in held if h.date == plan.date or not h.overnight)


def verdict(plan: Plan, held: list[Plan], money: float = OPTIONS_MONEY) -> tuple[str, str]:
    """('trade', '') or ('skip', reason). The order of the checks is T1's: the contract, the cap, the overnight rule, the money."""
    if not plan.tradingsymbol or not plan.lot or not plan.price:
        return "skip", SKIP_NO_CONTRACT
    if plan.premium > PREMIUM_CAP:
        return "skip", SKIP_CAP
    if plan.overnight and held_overnight(plan, held):
        return "skip", SKIP_OVERNIGHT
    if plan.premium + committed(plan, held) > money:
        return "skip", SKIP_MONEY
    return "trade", ""


def walk(plans: list[Plan], money: float = OPTIONS_MONEY) -> list[tuple[Plan, str, str]]:
    """The rules over a run of decisions in time order; a skipped decision holds nothing. (T1's table, from code.)"""
    held: list[Plan] = []
    out = []
    for p in plans:
        held = [h for h in held if h.date == p.date]          # earlier days' positions have left by this day's decisions
        v, why = verdict(p, held, money)
        if v == "trade":
            held.append(p)
        out.append((p, v, why))
    return out


def margin_order(plan: Plan) -> dict:
    """The one order the margin calculator is asked about: 1 lot, buy, NRML, LIMIT at the decision's quote."""
    return {"exchange": "NFO", "tradingsymbol": plan.tradingsymbol, "transaction_type": "BUY", "variety": "regular",
            "product": "NRML", "order_type": "LIMIT", "quantity": int(plan.lot) * LOTS, "price": float(plan.price)}


def margin_check(kite, plan: Plan, held: list[Plan], money: float = OPTIONS_MONEY) -> tuple[bool, str, float | None]:
    """Kite's margin calculator (india/kite.py basket_margin, a calculation) must say the money left covers the lot. Any doubt is a no."""
    try:
        d = kite.basket_margin([margin_order(plan)])
    except Exception as e:  # noqa: BLE001  no answer is a no
        return False, f"the margin calculator did not answer ({type(e).__name__})", None
    need = ((d or {}).get("final") or {}).get("total")
    if need is None:
        need = ((d or {}).get("initial") or {}).get("total")
    if need is None:
        return False, "the margin calculator gave no total", None
    left = money - committed(plan, held)
    if float(need) > left:
        return False, f"needs Rs {float(need):,.0f}, Rs {left:,.0f} left", float(need)
    return True, "covered", float(need)
