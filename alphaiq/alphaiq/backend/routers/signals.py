"""AlphaIQ Signals Router"""
import logging, random
from datetime import datetime
from typing import List
from fastapi import APIRouter, Request
from pydantic import BaseModel

log = logging.getLogger("signals")
router = APIRouter()

class ScanRequest(BaseModel):
    symbols: List[str]
    interval: int = 20

@router.post("/analyze/{symbol}")
async def analyze(symbol: str, request: Request):
    symbol = symbol.upper()
    market = request.app.state.market
    ai     = request.app.state.ai
    whale  = request.app.state.whale
    bars   = await market.get_bars(symbol)
    quote  = await market.get_quote(symbol)
    sig    = await ai.analyze(symbol, bars, quote)
    w      = await whale.check(symbol, bars, quote)
    return {"symbol": symbol, "signal": sig, "whale": w, "quote": quote,
            "timestamp": datetime.now().isoformat()}

@router.get("/watchlist/{user_id}")
async def get_watchlist_signals(user_id: str, request: Request):
    db     = request.app.state.db
    market = request.app.state.market
    ai     = request.app.state.ai
    whale  = request.app.state.whale
    symbols = await db.get_watchlist(user_id)
    if not symbols:
        symbols = ["AAPL","TSLA","NVDA","AMD","SPY"]
    results = []
    for sym in symbols:
        bars  = await market.get_bars(sym)
        quote = await market.get_quote(sym)
        sig   = await ai.analyze(sym, bars, quote)
        w     = await whale.check(sym, bars, quote)
        results.append({"symbol": sym, "signal": sig, "whale": w, "quote": quote})
    return {"signals": results, "timestamp": datetime.now().isoformat()}

@router.post("/watchlist/{user_id}/add/{symbol}")
async def add_symbol(user_id: str, symbol: str, request: Request):
    db = request.app.state.db
    await db.add_to_watchlist(user_id, symbol.upper())
    return {"status": "added", "symbol": symbol.upper()}

@router.delete("/watchlist/{user_id}/remove/{symbol}")
async def remove_symbol(user_id: str, symbol: str, request: Request):
    db = request.app.state.db
    await db.remove_from_watchlist(user_id, symbol.upper())
    return {"status": "removed", "symbol": symbol.upper()}
