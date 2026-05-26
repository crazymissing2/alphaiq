"""AlphaIQ Arena — weekly competitions"""
import logging, uuid
from datetime import datetime
from fastapi import APIRouter, Request, HTTPException
from pydantic import BaseModel
from typing import Optional

log = logging.getLogger("arena")
router = APIRouter()

# In-memory paper portfolios per user per competition
# Structure: { user_id: { cash, positions: {sym: {qty, avg_cost}}, trades: [] } }
_portfolios: dict = {}

class PaperTradeRequest(BaseModel):
    user_id:  str
    symbol:   str
    side:     str   # "buy" | "sell"
    qty:      float
    price:    float
    comp_id:  Optional[str] = None
    confirmed: bool = False

def _get_portfolio(user_id: str, start_cash: float = 100_000.0) -> dict:
    if user_id not in _portfolios:
        _portfolios[user_id] = {
            "cash":      start_cash,
            "positions": {},
            "trades":    [],
            "start_cash": start_cash,
        }
    return _portfolios[user_id]

def _portfolio_value(p: dict) -> float:
    pos_val = sum(v["qty"] * v["last_price"] for v in p["positions"].values())
    return p["cash"] + pos_val

@router.get("/competition")
async def get_competition(request: Request):
    db   = request.app.state.db
    comp = await db.get_active_competition()
    if not comp:
        return {"competition": None}
    lb = await db.get_leaderboard(comp["id"])
    return {"competition": comp, "leaderboard": lb,
            "participant_count": len(lb), "timestamp": datetime.now().isoformat()}

@router.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str):
    p     = _get_portfolio(user_id)
    total = _portfolio_value(p)
    pnl   = total - p["start_cash"]
    return {
        "cash":      round(p["cash"], 2),
        "positions": p["positions"],
        "trades":    p["trades"][-20:],
        "total_value": round(total, 2),
        "pnl":       round(pnl, 2),
        "pnl_pct":   round(pnl / p["start_cash"] * 100, 2),
        "start_cash": p["start_cash"],
    }

@router.post("/trade")
async def paper_trade(req: PaperTradeRequest, request: Request):
    if not req.confirmed:
        raise HTTPException(400, "confirmed=true required")

    db = request.app.state.db
    p  = _get_portfolio(req.user_id)
    cost = req.qty * req.price

    if req.side == "buy":
        if cost > p["cash"]:
            raise HTTPException(400, f"Insufficient cash. Have ${p['cash']:.2f}, need ${cost:.2f}")
        p["cash"] -= cost
        sym = req.symbol.upper()
        if sym in p["positions"]:
            pos   = p["positions"][sym]
            total = pos["qty"] + req.qty
            pos["avg_cost"] = (pos["qty"] * pos["avg_cost"] + cost) / total
            pos["qty"]        = total
            pos["last_price"] = req.price
        else:
            p["positions"][sym] = {"qty": req.qty, "avg_cost": req.price, "last_price": req.price}

    elif req.side == "sell":
        sym = req.symbol.upper()
        if sym not in p["positions"] or p["positions"][sym]["qty"] < req.qty:
            raise HTTPException(400, "Not enough shares to sell")
        pos   = p["positions"][sym]
        pnl   = (req.price - pos["avg_cost"]) * req.qty
        p["cash"] += cost
        pos["qty"] -= req.qty
        if pos["qty"] <= 0:
            del p["positions"][sym]

        # Save to DB
        await db.save_paper_trade({
            "user_id": req.user_id, "comp_id": req.comp_id,
            "symbol": sym, "side": "sell",
            "qty": req.qty, "price": req.price, "pnl": pnl
        })

    trade = {"side": req.side, "symbol": req.symbol.upper(),
             "qty": req.qty, "price": req.price, "ts": datetime.now().isoformat()}
    p["trades"].append(trade)

    # Update competition entry
    if req.comp_id:
        total  = _portfolio_value(p)
        ret    = (total - p["start_cash"]) / p["start_cash"] * 100
        await db.upsert_competition_entry(req.comp_id, req.user_id, p["cash"], total, ret)

    return {"success": True, "trade": trade,
            "portfolio": {"cash": round(p["cash"],2), "total": round(_portfolio_value(p),2)}}

@router.get("/leaderboard/{comp_id}")
async def get_leaderboard(comp_id: str, request: Request):
    db = request.app.state.db
    lb = await db.get_leaderboard(comp_id)
    return {"leaderboard": lb, "timestamp": datetime.now().isoformat()}

@router.post("/join/{comp_id}/{user_id}")
async def join_competition(comp_id: str, user_id: str, request: Request):
    db = request.app.state.db
    p  = _get_portfolio(user_id, 100_000.0)
    await db.upsert_competition_entry(comp_id, user_id, p["cash"], p["cash"], 0.0)
    return {"status": "joined", "starting_cash": 100_000.0}
