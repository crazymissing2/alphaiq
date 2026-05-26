"""AlphaIQ Market Data Service"""
import os, random, logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional

log = logging.getLogger("market")
FINNHUB_KEY = os.getenv("FINNHUB_API_KEY", "")
POLYGON_KEY = os.getenv("POLYGON_API_KEY", "")

try:
    import httpx; HAS_HTTPX = True
except ImportError:
    HAS_HTTPX = False

_prices = {
    "AAPL":190.0,"TSLA":245.0,"NVDA":875.0,"AMZN":183.0,"META":498.0,
    "GOOGL":172.0,"MSFT":415.0,"AMD":158.0,"SPY":519.0,"QQQ":447.0,
    "NFLX":620.0,"CRM":290.0,"SHOP":73.0,"PLTR":21.0,"SOFI":8.5,
    "COIN":180.0,"RBLX":40.0,"UBER":75.0,"LYFT":14.0,"SNAP":12.0,
}

class MarketDataService:
    def __init__(self):
        self._cache: Dict[str, list] = {}

    async def get_quote(self, symbol: str) -> dict:
        if FINNHUB_KEY and HAS_HTTPX:
            try:
                async with httpx.AsyncClient(timeout=4) as c:
                    r = await c.get(f"https://finnhub.io/api/v1/quote?symbol={symbol}&token={FINNHUB_KEY}")
                    if r.status_code == 200:
                        d = r.json()
                        price = d.get("c", 0)
                        if price > 0:
                            prev = d.get("pc", price)
                            chg  = (price - prev) / max(prev, 0.01) * 100
                            _prices[symbol] = price
                            return {"symbol": symbol, "price": price,
                                    "open": d.get("o", price), "high": d.get("h", price),
                                    "low": d.get("l", price), "prev_close": prev,
                                    "change_pct": round(chg, 2), "source": "finnhub"}
            except Exception as e:
                log.debug(f"Finnhub error {symbol}: {e}")
        return self._mock_quote(symbol)

    def _mock_quote(self, symbol: str) -> dict:
        base  = _prices.get(symbol, 100.0)
        chg   = random.gauss(0, 0.009)
        price = round(base * (1 + chg), 2)
        _prices[symbol] = price
        prev  = round(price / (1 + chg), 2)
        return {"symbol": symbol, "price": price, "open": prev,
                "high": round(price*1.005,2), "low": round(price*0.995,2),
                "prev_close": prev, "change_pct": round(chg*100,2),
                "volume": random.randint(1_000_000, 50_000_000), "source": "mock"}

    async def get_bars(self, symbol: str, timeframe: str = "1Min", count: int = 200) -> list:
        bars = self._generate_candles(symbol, count)
        self._cache[symbol] = bars
        return bars

    def _generate_candles(self, symbol: str, count: int) -> list:
        base  = _prices.get(symbol, 100.0)
        bars  = []
        price = base * random.uniform(0.88, 1.0)
        now   = datetime.now()
        for i in range(count):
            t     = now - timedelta(minutes=(count - i))
            chg   = random.gauss(0.0001, 0.007)
            o     = price
            c     = round(o * (1 + chg), 2)
            h     = round(max(o, c) * random.uniform(1.001, 1.007), 2)
            l     = round(min(o, c) * random.uniform(0.993, 0.999), 2)
            v     = random.randint(100_000, 5_000_000)
            bars.append({"t": int(t.timestamp()), "o": o, "h": h, "l": l, "c": c, "v": v})
            price = c
        _prices[symbol] = price
        return bars

    async def validate_alpaca_keys(self, api_key: str, secret: str, paper: bool) -> dict:
        base = "https://paper-api.alpaca.markets" if paper else "https://api.alpaca.markets"
        if not HAS_HTTPX:
            return {"valid": False, "error": "httpx not installed"}
        try:
            async with httpx.AsyncClient(timeout=5) as c:
                r = await c.get(f"{base}/v2/account",
                                headers={"APCA-API-KEY-ID": api_key, "APCA-API-SECRET-KEY": secret})
                if r.status_code == 200:
                    return {"valid": True, "account": r.json()}
                return {"valid": False, "error": f"HTTP {r.status_code}"}
        except Exception as e:
            return {"valid": False, "error": str(e)}
