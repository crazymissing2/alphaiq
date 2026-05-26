"""AlphaIQ AI Signal Engine"""
import random, logging
from datetime import datetime
from typing import List, Dict, Any

log = logging.getLogger("ai")

try:
    import numpy as np; HAS_NP = True
except ImportError:
    HAS_NP = False


class AISignalEngine:
    def __init__(self):
        self._history: Dict[str, List[float]] = {}

    async def analyze(self, symbol: str, bars: list, quote: dict) -> dict:
        if not bars:
            return {"action": "HOLD", "confidence": 0, "reasons": ["No data"]}

        closes  = [b["c"] for b in bars]
        volumes = [b["v"] for b in bars]
        price   = quote.get("price", closes[-1])
        change  = quote.get("change_pct", 0)

        rsi           = self._rsi(closes)
        macd, sig_line, macd_trend = self._macd(closes)
        ema9          = self._ema(closes, 9)
        ema21         = self._ema(closes, 21)
        ema50         = self._ema(closes, 50)
        bb_u, bb_m, bb_l = self._bollinger(closes)
        vwap          = self._vwap(bars[-50:])
        vol_spike     = self._vol_spike(volumes)
        vol_ratio     = round(volumes[-1] / max(sum(volumes[:-1])/max(len(volumes)-1,1), 1), 2)
        pattern       = self._pattern(bars)

        score, reasons = 0.0, []

        if rsi < 30:   score += 0.30; reasons.append(f"RSI {rsi:.0f} — oversold, bounce likely 🟢")
        elif rsi > 70: score -= 0.30; reasons.append(f"RSI {rsi:.0f} — overbought, pullback risk 🔴")
        else:          reasons.append(f"RSI {rsi:.0f} — neutral zone")

        if macd_trend == "bullish": score += 0.20; reasons.append(f"MACD bullish crossover 🟢")
        else:                       score -= 0.15; reasons.append(f"MACD bearish 🔴")

        if ema9 > ema21 > ema50: score += 0.20; reasons.append("EMA stack bullish (9>21>50) 🟢")
        elif ema9 < ema21 < ema50: score -= 0.20; reasons.append("EMA stack bearish 🔴")
        else: reasons.append("EMAs mixed — no clear trend")

        if price > vwap: score += 0.10; reasons.append(f"Price above VWAP (${vwap:.2f}) — institutional buy zone")
        else:            score -= 0.10; reasons.append(f"Price below VWAP (${vwap:.2f}) — selling pressure")

        if price < bb_l: score += 0.15; reasons.append(f"Below Bollinger lower band — oversold zone")
        elif price > bb_u: score -= 0.15; reasons.append(f"Above Bollinger upper band — overbought zone")

        if vol_spike:
            d = "confirms buying" if score > 0 else "confirms selling"
            score += 0.10 if score > 0 else -0.10
            reasons.append(f"Volume spike {vol_ratio}x avg — {d} 🔥")

        reasons.append(f"Pattern: {pattern}")
        if "Bullish" in pattern or "Uptrend" in pattern: score += 0.05
        if "Bearish" in pattern or "Downtrend" in pattern: score -= 0.05

        if change > 3: score += 0.05; reasons.append(f"Strong intraday gain +{change:.1f}%")
        elif change < -3: score -= 0.05; reasons.append(f"Significant drop {change:.1f}%")

        confidence = min(abs(score), 1.0)
        if   score >  0.50: action = "STRONG BUY"
        elif score >  0.25: action = "BUY"
        elif score < -0.50: action = "STRONG SELL"
        elif score < -0.25: action = "SELL"
        elif score >  0.10: action = "WATCH"
        else:               action = "HOLD"

        sl = round(price * 0.98, 2)
        tp = round(price * (1.04 if score > 0 else 0.96), 2)
        rr = round(abs(tp - price) / max(abs(price - sl), 0.01), 2)

        return {
            "action":      action,
            "confidence":  round(confidence, 3),
            "score":       round(score, 3),
            "reasons":     reasons,
            "entry_price": round(price, 2),
            "stop_loss":   sl,
            "take_profit": tp,
            "risk_reward": rr,
            "indicators": {
                "rsi": round(rsi, 1), "macd": round(macd, 4),
                "macd_signal": round(sig_line, 4), "macd_trend": macd_trend,
                "ema9": round(ema9, 2), "ema21": round(ema21, 2), "ema50": round(ema50, 2),
                "vwap": round(vwap, 2), "bb_upper": round(bb_u, 2),
                "bb_mid": round(bb_m, 2), "bb_lower": round(bb_l, 2),
                "vol_spike": vol_spike, "vol_ratio": vol_ratio, "pattern": pattern,
            },
            "analyzed_at": datetime.now().isoformat(),
        }

    def _rsi(self, closes: list, period: int = 14) -> float:
        if len(closes) < period + 1: return 50.0
        if HAS_NP:
            arr = np.array(closes[-(period+1):])
            d   = np.diff(arr)
            g   = np.where(d>0,d,0).mean()
            l   = np.where(d<0,-d,0).mean()
            return round(100.0 if l==0 else 100-100/(1+g/l), 1)
        gains = losses = 0
        for i in range(1, period+1):
            diff = closes[-i] - closes[-i-1]
            if diff > 0: gains += diff
            else: losses -= diff
        if losses == 0: return 100.0
        return round(100 - 100/(1+gains/losses), 1)

    def _ema(self, closes: list, period: int) -> float:
        if not closes: return 0.0
        k, ema = 2/(period+1), closes[0]
        for v in closes[1:]: ema = v*k + ema*(1-k)
        return round(ema, 4)

    def _macd(self, closes: list):
        if len(closes) < 26: return 0.0, 0.0, "neutral"
        ema12 = self._ema(closes, 12)
        ema26 = self._ema(closes, 26)
        macd  = ema12 - ema26
        signal = self._ema(closes[-9:], 9)
        return round(macd,4), round(signal,4), "bullish" if macd > signal else "bearish"

    def _bollinger(self, closes: list, period: int = 20):
        if len(closes) < period: return 0, 0, 0
        w    = closes[-period:]
        mean = sum(w) / period
        std  = (sum((x-mean)**2 for x in w)/period)**0.5
        return mean+2*std, mean, mean-2*std

    def _vwap(self, bars: list) -> float:
        if not bars: return 0.0
        pv = sum(((b["h"]+b["l"]+b["c"])/3)*b["v"] for b in bars)
        tv = sum(b["v"] for b in bars)
        return round(pv/tv, 2) if tv else 0.0

    def _vol_spike(self, volumes: list) -> bool:
        if len(volumes) < 5: return False
        avg = sum(volumes[:-1]) / max(len(volumes)-1, 1)
        return volumes[-1] > avg * 1.6 if avg > 0 else False

    def _pattern(self, bars: list) -> str:
        if len(bars) < 3: return "Insufficient data"
        last = bars[-1]
        body = abs(last["c"] - last["o"])
        wick = last["h"] - last["l"]
        if wick > 0 and body/wick < 0.1: return "Doji — indecision signal"
        lower = min(last["o"],last["c"]) - last["l"]
        if lower > body*2 and last["c"] > bars[-2]["c"]: return "Hammer — bullish reversal 🟢"
        upper = last["h"] - max(last["o"],last["c"])
        if upper > body*2 and last["c"] < bars[-2]["c"]: return "Shooting Star — bearish 🔴"
        closes = [b["c"] for b in bars[-5:]]
        if all(closes[i]>closes[i-1] for i in range(1,len(closes))): return "Strong Uptrend 📈"
        if all(closes[i]<closes[i-1] for i in range(1,len(closes))): return "Strong Downtrend 📉"
        return "Consolidating ↔"


class WhaleTracker:
    async def check(self, symbol: str, bars: list, quote: dict) -> dict:
        if not bars: return {"is_whale": False}
        volumes = [b["v"] for b in bars]
        avg_vol = sum(volumes[:-1]) / max(len(volumes)-1, 1)
        last_vol = volumes[-1]
        price   = quote.get("price", bars[-1]["c"])
        dollar_vol = last_vol * price
        vol_ratio  = round(last_vol / avg_vol, 2) if avg_vol else 1.0
        is_whale   = last_vol > avg_vol * 2.0 and dollar_vol > 50_000_000
        pressure   = "BUY" if bars[-1]["c"] > bars[-1]["o"] else "SELL"
        return {
            "is_whale":      is_whale,
            "vol_ratio":     vol_ratio,
            "dollar_volume": round(dollar_vol, 0),
            "avg_volume":    round(avg_vol, 0),
            "current_volume": last_vol,
            "pressure":      pressure,
            "intensity":     "HIGH" if vol_ratio > 3 else "MEDIUM" if vol_ratio > 2 else "LOW",
        }
