"""A fake Kite for the live path's tests: it records every request and never reaches the network."""


class _Resp:
    def __init__(self, data, status=200):
        self._data, self.status_code = data, status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"HTTP {self.status_code}")

    def json(self):
        return {"status": "success", "data": self._data}


class FakeSession:
    def __init__(self, kite):
        self.k = kite

    def request(self, method, url, **kw):
        self.k.sent.append((method.upper(), url, kw.get("data")))
        if self.k.fail_sends:
            self.k.fail_sends -= 1
            return _Resp({}, 500)
        n = len(self.k.sent)
        return _Resp({"trigger_id": 900 + n} if "/gtt" in url else {"order_id": f"O{n}"})

    def _refuse(self, *a, **k):
        raise AssertionError(f"the live path used the session directly: {a}")

    get = post = put = delete = patch = _refuse


class FakeKite:
    def __init__(self, margin=30_000.0, fail_sends=0):
        self.sent, self.calc, self.gets = [], [], []
        self.margin, self.fail_sends = margin, fail_sends
        self.s = FakeSession(self)
        self._trades, self._positions, self._gtts = [], {"net": []}, []

    def basket_margin(self, orders):
        self.calc.append(orders)
        return {"initial": {"total": self.margin}, "final": {"total": self.margin}}

    def get(self, path, params=None, raw=False):
        self.gets.append(path)
        return self._gtts if path == "/gtt/triggers" else []

    def trades(self):
        self.gets.append("/trades")
        return self._trades

    def positions(self):
        self.gets.append("/portfolio/positions")
        return self._positions

    def orders(self):
        self.gets.append("/orders")
        return []
