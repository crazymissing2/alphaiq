"""AlphaIQ Market Data Router"""
from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/bars/{symbol}")
async def get_bars(symbol: str, count: int = 200, request: Request = None):
    market = request.app.state.market
    bars   = await market.get_bars(symbol.upper(), count=count)
    return {"symbol": symbol.upper(), "bars": bars}

@router.get("/quote/{symbol}")
async def get_quote(symbol: str, request: Request = None):
    market = request.app.state.market
    return await market.get_quote(symbol.upper())

@router.get("/movers")
async def get_movers(request: Request):
    market  = request.app.state.market
    symbols = ["AAPL","TSLA","NVDA","AMD","META","GOOGL","MSFT","AMZN","NFLX","CRM"]
    movers  = []
    for sym in symbols:
        q = await market.get_quote(sym)
        movers.append(q)
    movers.sort(key=lambda x: abs(x.get("change_pct", 0)), reverse=True)
    return {"movers": movers}
