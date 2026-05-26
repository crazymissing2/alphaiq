"""AlphaIQ Whale Router"""
from datetime import datetime
from fastapi import APIRouter, Request
router = APIRouter()

@router.get("/flow")
async def get_whale_flow(request: Request):
    market = request.app.state.market
    whale  = request.app.state.whale
    symbols = ["AAPL","TSLA","NVDA","AMD","META","GOOGL","MSFT","SPY","QQQ","AMZN"]
    flow = []
    for sym in symbols:
        bars  = await market.get_bars(sym, count=50)
        quote = await market.get_quote(sym)
        w     = await whale.check(sym, bars, quote)
        flow.append({"symbol": sym, "whale": w, "price": quote.get("price", 0),
                     "change_pct": quote.get("change_pct", 0)})
    flow.sort(key=lambda x: x["whale"].get("vol_ratio", 0), reverse=True)
    return {"flow": flow, "timestamp": datetime.now().isoformat()}

@router.get("/alerts")
async def get_whale_alerts(request: Request):
    db = request.app.state.db
    alerts = await db.get_recent_whale_alerts()
    return {"alerts": alerts, "timestamp": datetime.now().isoformat()}
