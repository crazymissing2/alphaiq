"""
AlphaIQ — AI Trading Academy Backend
FastAPI + WebSocket + PostgreSQL + Claude AI Mentor
"""

import asyncio, json, logging, os, secrets, hashlib
from contextlib import asynccontextmanager
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Set

import uvicorn
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, HTTPException, Depends
from fastapi.middleware.cors import CORSMiddleware
from fastapi.security import HTTPBearer, HTTPAuthorizationCredentials
from pydantic import BaseModel, EmailStr

from routers import signals, whale, arena, mentor, market
from db.database import Database
from services.auth import AuthService
from services.market_data import MarketDataService
from services.ai_engine import AISignalEngine
from services.whale_tracker import WhaleTracker

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s — %(message)s")
log = logging.getLogger("alphaiq")

# ── Globals ───────────────────────────────────────────────────────────────────
db:       Optional[Database]          = None
auth_svc: Optional[AuthService]       = None
market:   Optional[MarketDataService] = None
ai:       Optional[AISignalEngine]    = None
whale_svc:Optional[WhaleTracker]      = None
ws_rooms: Dict[str, Set[WebSocket]]   = {}   # room → set of sockets
scan_task: Optional[asyncio.Task]     = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    global db, auth_svc, market, ai, whale_svc
    log.info("🚀 AlphaIQ starting up...")
    db        = Database()
    await db.init()
    auth_svc  = AuthService(db)
    market    = MarketDataService()
    ai        = AISignalEngine()
    whale_svc = WhaleTracker()
    # Share with routers via app.state
    app.state.db        = db
    app.state.auth      = auth_svc
    app.state.market    = market
    app.state.ai        = ai
    app.state.whale     = whale_svc
    app.state.ws_rooms  = ws_rooms
    log.info("✅ All services ready — AlphaIQ is live")
    yield
    if scan_task: scan_task.cancel()
    await db.close()
    log.info("🛑 AlphaIQ stopped")

app = FastAPI(
    title="AlphaIQ API",
    description="AI Trading Academy — Learn, Track Whales, Compete",
    version="1.0.0",
    lifespan=lifespan,
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_origin_regex=r"chrome-extension://.*",
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# ── Include routers ───────────────────────────────────────────────────────────
app.include_router(signals.router, prefix="/api/signals",  tags=["Signals"])
app.include_router(whale.router,   prefix="/api/whale",    tags=["Whale"])
app.include_router(arena.router,   prefix="/api/arena",    tags=["Arena"])
app.include_router(mentor.router,  prefix="/api/mentor",   tags=["AI Mentor"])
app.include_router(market.router,  prefix="/api/market",   tags=["Market"])

# ── Auth Models ───────────────────────────────────────────────────────────────
class RegisterRequest(BaseModel):
    username: str
    email: str
    password: str

class LoginRequest(BaseModel):
    email: str
    password: str

class AlpacaConnectRequest(BaseModel):
    api_key: str
    secret_key: str
    paper_mode: bool = True

# ── Auth Endpoints ────────────────────────────────────────────────────────────
@app.post("/api/auth/register")
async def register(req: RegisterRequest):
    user = await auth_svc.register(req.username, req.email, req.password)
    if not user:
        raise HTTPException(status_code=400, detail="Email already registered")
    token = auth_svc.create_token(user["id"])
    return {"token": token, "user": {k: user[k] for k in ["id","username","email","created_at"]}}

@app.post("/api/auth/login")
async def login(req: LoginRequest):
    user = await auth_svc.authenticate(req.email, req.password)
    if not user:
        raise HTTPException(status_code=401, detail="Invalid credentials")
    token = auth_svc.create_token(user["id"])
    return {"token": token, "user": {k: user[k] for k in ["id","username","email","created_at","skill_rating","competitions_won"]}}

@app.post("/api/auth/connect-alpaca")
async def connect_alpaca(req: AlpacaConnectRequest, user=Depends(auth_svc.get_current_user if auth_svc else None)):
    # Validate Alpaca keys
    result = await market.validate_alpaca_keys(req.api_key, req.secret_key, req.paper_mode)
    if not result["valid"]:
        raise HTTPException(status_code=400, detail=f"Invalid Alpaca keys: {result['error']}")
    # Store encrypted in DB
    await db.save_alpaca_keys(user["id"], req.api_key, req.secret_key, req.paper_mode)
    return {"status": "connected", "paper_mode": req.paper_mode, "account": result["account"]}

@app.get("/api/auth/me")
async def get_me(user=Depends(auth_svc.get_current_user if auth_svc else None)):
    return user

# ── Health ────────────────────────────────────────────────────────────────────
@app.get("/api/health")
async def health():
    return {
        "status": "running",
        "version": "1.0.0",
        "platform": "AlphaIQ",
        "ws_connections": sum(len(v) for v in ws_rooms.values()),
        "timestamp": datetime.now().isoformat(),
    }

# ── WebSocket ─────────────────────────────────────────────────────────────────
@app.websocket("/ws/{room}")
async def websocket_endpoint(ws: WebSocket, room: str):
    await ws.accept()
    if room not in ws_rooms:
        ws_rooms[room] = set()
    ws_rooms[room].add(ws)
    log.info(f"WS joined room '{room}' — {len(ws_rooms[room])} in room")

    try:
        await ws.send_json({"type": "joined", "room": room, "ts": datetime.now().isoformat()})
        while True:
            raw = await ws.receive_text()
            msg = json.loads(raw)
            # Handle ping
            if msg.get("type") == "ping":
                await ws.send_json({"type": "pong", "ts": datetime.now().isoformat()})
            # Broadcast to room
            elif msg.get("type") == "broadcast":
                await broadcast_room(room, msg.get("data", {}))
    except WebSocketDisconnect:
        ws_rooms[room].discard(ws)
        log.info(f"WS left room '{room}'")

async def broadcast_room(room: str, msg: dict):
    if room not in ws_rooms:
        return
    dead = set()
    txt  = json.dumps(msg, default=str)
    for ws in ws_rooms[room]:
        try:    await ws.send_text(txt)
        except: dead.add(ws)
    ws_rooms[room].difference_update(dead)

if __name__ == "__main__":
    uvicorn.run("main:app", host="0.0.0.0", port=8765, reload=True)
