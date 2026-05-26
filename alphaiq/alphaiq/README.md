# AlphaIQ — AI Trading Academy

The platform that teaches you to trade while you trade.

## What AlphaIQ Is

- **AI Mentor** — Claude-powered chat coach that explains every signal in plain English
- **Live Charts** — Candlestick charts with EMA, VWAP, Bollinger Bands overlays
- **AI Signals** — RSI, MACD, volume spike, pattern recognition, whale tracking
- **Whale Flow Map** — Real-time institutional money flow visualization
- **Arena** — Weekly paper trading competitions with leaderboards
- **Trading Academy** — Structured lessons taught by AI

## Quick Start (Windows)

1. Double-click `START.bat`
2. Wait for "Server running" message
3. Open `frontend/index.html` in Chrome
4. Create an account and start trading (paper money, no risk)

## Setup API Keys (Optional)

Rename `backend/.env.example` to `backend/.env` and add:

```
ANTHROPIC_API_KEY=your_claude_key    # For AI Mentor chat
FINNHUB_API_KEY=your_finnhub_key     # For real market data
```

Without keys: mock data + built-in mentor responses (still fully functional)

## Project Structure

```
alphaiq/
├── START.bat                    ← Double-click to run
├── backend/
│   ├── main.py                  ← FastAPI server
│   ├── db/database.py           ← SQLite database
│   ├── services/
│   │   ├── auth.py              ← User auth + JWT
│   │   ├── ai_engine.py         ← Signal engine + whale tracker
│   │   └── market_data.py       ← Finnhub/Polygon/mock data
│   ├── routers/
│   │   ├── signals.py           ← Signal endpoints
│   │   ├── mentor.py            ← Claude AI mentor
│   │   ├── arena.py             ← Competitions + paper trading
│   │   ├── whale.py             ← Whale flow endpoints
│   │   └── market.py            ← Market data endpoints
│   ├── requirements.txt
│   ├── railway.toml             ← Railway deployment
│   └── Procfile                 ← Render/Heroku deployment
└── frontend/
    └── index.html               ← Full web app (open in browser)
```

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/api/auth/register` | POST | Create account |
| `/api/auth/login` | POST | Sign in |
| `/api/signals/analyze/{symbol}` | POST | AI signal analysis |
| `/api/mentor/chat` | POST | AI mentor message |
| `/api/mentor/lessons` | GET | Trading lessons |
| `/api/whale/flow` | GET | Live whale flow map |
| `/api/arena/competition` | GET | Current competition + leaderboard |
| `/api/arena/trade` | POST | Place paper trade |
| `/api/market/bars/{symbol}` | GET | OHLCV chart data |
| `/ws/{room}` | WebSocket | Live updates |
| `/api/health` | GET | Server status |

## Deploy to the Cloud (Go Public)

### Railway (Recommended — Free)
1. Create account at railway.app
2. Connect your GitHub repo
3. Deploy the `backend/` folder
4. Set environment variables in Railway dashboard
5. Your API is live at `https://yourapp.railway.app`

### Update Frontend
Change `const API = 'http://127.0.0.1:8765'` in `frontend/index.html`
to your Railway URL: `const API = 'https://yourapp.railway.app'`

Then host the frontend free on:
- Netlify (drag & drop the frontend/ folder)
- Vercel
- GitHub Pages

## Going Public Checklist

- [ ] Add Anthropic API key for real AI mentor
- [ ] Add Finnhub API key for real market data
- [ ] Deploy backend to Railway
- [ ] Deploy frontend to Netlify
- [ ] Buy domain (e.g. alphaiq.trade — ~$12/yr)
- [ ] Add Terms of Service (not financial advice disclaimer)
- [ ] Add Privacy Policy
- [ ] Register LLC (~$150 in most states)
- [ ] Consider Alpaca API for real trade execution (optional)

## Tech Stack

- **Backend**: Python, FastAPI, SQLite, WebSockets
- **Frontend**: Vanilla JS SPA (upgrade to React/Vite for production)
- **AI**: Claude API (Anthropic) for mentor chat
- **Data**: Finnhub, Polygon.io, or mock data
- **Auth**: JWT tokens (upgrade to proper JWT library for production)
- **Hosting**: Railway (backend), Netlify (frontend)

## Important Disclaimers

AlphaIQ provides educational tools and market signals — NOT financial advice.
Always practice with paper trading before using real money.
Past signal performance does not predict future results.
Never risk money you cannot afford to lose.
