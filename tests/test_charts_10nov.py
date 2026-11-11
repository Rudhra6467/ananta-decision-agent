"""Madhav, 10 Nov 2026 19:09 Toronto: the numbers in Home's two boxes open their charts with ranges 1D 5D 1M 3M 6M and timeframes 5M 15M
30M 1H 4H 1D; Stocks and Options open their own history with the portfolio and Ask Ananta; a hide button next to the bell hides the
portfolio numbers; on Markets the Nifty 50, Bank Nifty and fear gauge boxes open their history. No network here: Kite and Binance are fakes."""
import datetime as dt
import json
from pathlib import Path

import pytest

from jarvis import chartkit as CK
from jarvis import placekit as K
from jarvis.india import livesession as L
from jarvis.india import places as IP
from jarvis.india import surfaces as IS
from jarvis.india import views
from jarvis.service import places as CP

APP = Path(__file__).resolve().parents[1] / "jarvis" / "app" / "src"


# ------------------------------------------------------------------------------------------------ the window rule
def test_a_pair_is_offered_when_it_draws_4_to_300_candles():
    assert CK.offered("india", "1D") == ["5M", "15M", "30M", "1H"]
    assert CK.offered("india", "6M") == ["4H", "1D"]
    assert CK.offered("crypto", "1D") == ["5M", "15M", "30M", "1H", "4H"]
    assert CK.offered("crypto", "6M") == ["1D"]
    assert CK.pick("india", "1D", None) == ("1D", "5M", ["5M", "15M", "30M", "1H"])           # nearest 80 candles: 75
    assert CK.pick("india", "6M", "5M")[1] == "1D"                                             # not offered: the nearest that is
    assert CK.pick("crypto", "nonsense", "1H")[:2] == ("1D", "1H")
    for mk in ("india", "crypto"):
        for r in CK.RANGES:
            assert CK.offered(mk, r), (mk, r)                                                  # every range has a timeframe


def test_four_hour_candles_merge_the_hourly_ones():
    bars = [[1, 10, 12, 9, 11], [2, 11, 15, 10, 14], [3, 14, 14, 8, 9], [4, 9, 10, 9, 10]]
    out = CK.agg(bars, key=lambda b: b[0] <= 2)
    assert out == [[1, 10, 15, 9, 14], [3, 14, 14, 8, 10]]


def test_a_history_offers_the_ranges_its_record_fills_and_all():
    pts = [(f"2026-10-{d:02d}", 100 + d) for d in range(1, 11)]
    h = CK.history("x", "india", pts, None, ccy="₹")
    assert h["ranges"] == ["5D", "ALL"] and h["range"] == "ALL" and len(h["bars"]) == 10 and h["kind"] == "line" and h["tfs"] == []
    h5 = CK.history("x", "india", pts, "5D", ccy="₹")
    assert len(h5["bars"]) == 6 and h5["change"] == 5 and h5["first"] == 105
    assert CK.history("x", "crypto", pts, "6M", ccy="C$", per="night", neutral=True)["neutral"] is True


# ------------------------------------------------------------------------------------------------ India: Kite candles (read-only), and the fallback
def _kite_5m(days: list[str]):
    out = []
    for d in days:
        t = dt.datetime.fromisoformat(d + "T09:15:00+05:30")
        for i in range(75):
            px = 25000 + i
            out.append([(t + dt.timedelta(minutes=5 * i)).strftime("%Y-%m-%dT%H:%M:%S%z"), px, px + 3, px - 3, px + 1, 0])
    return out


def test_india_1d_keeps_the_last_session_and_4h_makes_two_a_day(monkeypatch):
    L._BARS.clear()
    calls = []

    def fetch(tok, interval, a, b):
        calls.append((tok, interval))
        if interval == "5minute":
            return _kite_5m(["2026-11-06", "2026-11-09"])
        hourly = []
        for d in ("2026-11-06", "2026-11-09"):
            t = dt.datetime.fromisoformat(d + "T09:15:00+05:30")
            hourly += [[(t + dt.timedelta(hours=h)).strftime("%Y-%m-%dT%H:%M:%S%z"), 1, 2, 0.5, 1.5, 0] for h in range(7)]
        return hourly

    c = IP.candles("NIFTY", "1D", None, fetch=fetch)
    assert c["kind"] == "candles" and c["tf"] == "5M" and len(c["bars"]) == 75 and c["tz_min"] == 330 and not c.get("fell_back")
    assert dt.datetime.fromtimestamp(c["bars"][0][0], L.IST).strftime("%Y-%m-%d %H:%M") == "2026-11-09 09:15"
    assert calls[0] == (256265, "5minute")
    c4 = IP.candles("BANKNIFTY", "5D", "4H", fetch=fetch)
    assert c4["tf"] == "4H" and len(c4["bars"]) == 4 and calls[-1] == (260105, "60minute")      # 09:15-13:15 and 13:15 to the close, two days
    assert IP.candles("VIX", "1M", "1D", fetch=lambda *a: [])["fell_back"]                      # nothing back from Kite: said, not drawn as a flat line


def test_india_falls_back_to_the_daily_closes_when_kite_refuses(monkeypatch):
    L._BARS.clear()
    monkeypatch.setattr(IP, "_tech", lambda: {"NIFTY 50": {"chart": {"dates": [f"2026-11-0{d}" for d in range(2, 8)], "closes": [100, 101, 102, 103, 104, 105]}}})

    def refuse(*a):
        raise RuntimeError("403 Client Error: Forbidden")

    c = IP.candles("NIFTY", "1D", "5M", fetch=refuse)
    assert c["kind"] == "line" and c["fell_back"].startswith("Zerodha's feed is signed out") and len(c["bars"]) == 6 and c["over"] == "over the last 5 sessions"


def test_the_account_lines_are_the_owners_only():
    with pytest.raises(PermissionError):
        IP.candles("STOCKS", full=False)
    with pytest.raises(PermissionError):
        IP.candles("OPTIONS", full=False)
    with pytest.raises(KeyError):
        IP.candles("RELIANCE")


def test_the_stocks_return_takes_the_sales_and_buys_out(tmp_path, monkeypatch):
    """2 Nov: the book sold ₹43,412 of cut stocks into cash and bought ₹29,058; the stocks' value fell, but that is not a loss."""
    (tmp_path / "paper" / "account").mkdir(parents=True)
    (tmp_path / "paper" / "managed").mkdir(parents=True)
    rows = [{"day": "2026-10-30", "managed_inr": 160000}, {"day": "2026-11-02", "managed_inr": 161000}, {"day": "2026-11-03", "managed_inr": 162000}]
    (tmp_path / "paper" / "account" / "benchmark.jsonl").write_text("".join(json.dumps(r) + "\n" for r in rows))
    fills = [{"for_session": "2026-11-02", "side": "SELL", "value_inr": 20000, "cost_inr": 0, "filled": True},
             {"for_session": "2026-11-02", "side": "BUY", "value_inr": 5000, "cost_inr": 0, "filled": True}]
    (tmp_path / "paper" / "managed" / "ledger.jsonl").write_text("".join(json.dumps(f) + "\n" for f in fills))
    monkeypatch.setattr(views, "DATA", tmp_path)
    monkeypatch.setattr(IS, "_managed", lambda: {"cash_inr": 25000, "options_inr": 50000, "stocks_inr": 87000, "day": "2026-11-03"})
    pts = IP.stock_points()
    assert pts == [("2026-10-30", 100000), ("2026-11-02", 86000), ("2026-11-03", 87000)]       # cash 10,000 before the fills, 25,000 after
    ret = IP.stock_return(pts)
    assert ret[0] == ("2026-10-30", 0.0) and ret[1] == ("2026-11-02", 1.0)                       # (86,000 + 15,000 sold net) / 100,000
    assert ret[2][1] == pytest.approx(100 * (1.01 * 87000 / 86000 - 1), abs=0.01)


# ------------------------------------------------------------------------------------------------ crypto
def test_crypto_coin_candles_and_the_books_lines(monkeypatch):
    from jarvis.service import feed
    now = int(dt.datetime.now(dt.timezone.utc).timestamp()) // 900 * 900
    monkeypatch.setattr(feed, "bars", lambda j, coin, tf, n: [(now - 900 * (n - i), 100 + i, 101 + i, 99 + i, 100.5 + i, 1) for i in range(n)])
    monkeypatch.setattr(feed, "daily", lambda j, coin: [(now - 86400 * (200 - i), 1, 2, 0.5, 1.5, 1) for i in range(200)])
    c = CP.candles(None, "BTC", "1D", "15M")
    assert c["name"] == "Bitcoin" and c["ccy"] == "$" and c["tf"] == "15M" and 90 <= len(c["bars"]) <= 98 and c["live"]
    assert CP.candles(None, "ethereum", "6M", "5M")["tf"] == "1D"
    with pytest.raises(PermissionError):
        CP.candles(None, "CASH", is_owner=False)
    with pytest.raises(KeyError):
        CP.candles(None, "DOGE")


# ------------------------------------------------------------------------------------------------ the parts and the app
def test_the_price_chart_is_a_building_block_and_breaks_no_rule():
    assert "pricechart" in K.PART_TYPES
    pg = K.page("Nifty 50", [K.hero("Nifty 50", "25,045"), K.pricechart("NIFTY", "Nifty 50")], ask_q="Tell me about the Nifty 50.")
    assert K.problems("nifty", pg) == []
    assert K.pricechart("STOCKS", "Your stocks", kind="line", private=True) == {"t": "pricechart", "sym": "STOCKS", "name": "Your stocks", "kind": "line", "private": True}


def test_every_box_opens_its_own_page():
    src = Path(IP.__file__).read_text()
    assert 'to=K.place({"NIFTY 50": "nifty", "NIFTY BANK": "banknifty"}[key])' in src and 'to=K.place("stocks")' in src and 'to=K.place("vix")' in src
    for n in ("nifty", "banknifty", "vix", "stocks", "options"):
        assert n in IP.PLACES
    csrc = Path(CP.__file__).read_text()
    assert 'to=K.place("coins")' in csrc and 'to=K.place("cash")' in csrc and 'to=K.place("coin:" + str(p.get("coin") or "BTC"))' in csrc
    assert "coins" in CP.PLACES and "cash" in CP.PLACES


def test_the_app_hides_the_amounts_next_to_the_bell():
    place = (APP / "place.tsx").read_text()
    screen = (APP / "placescreen.tsx").read_text()
    assert "<HideButton /><Bell count={count} />" in screen and "<HideButton />\n        </View>" in screen
    assert 'const HKEY = "ananta_hide_money"' in place and "export function useMask()" in place
    for comp in ("function Hero(", "function BoxBody(", "export function Row(", "function KV(", "function Points(", "function Split("):
        body = place.split(comp, 1)[1][:200]
        assert "const m = useMask();" in body, comp
    assert 'case "pricechart"' in place and "function PriceChart(" in place
