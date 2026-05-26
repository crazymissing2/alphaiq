"""
AlphaIQ AI Mentor — Claude-powered trading coach
Explains signals, teaches concepts, answers questions
"""

import logging, os
from datetime import datetime
from typing import List, Optional

from fastapi import APIRouter, HTTPException, Depends, Request
from pydantic import BaseModel

log = logging.getLogger("mentor")
router = APIRouter()

CLAUDE_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

SYSTEM_PROMPT = """You are AlphaIQ's AI Trading Mentor — a friendly, knowledgeable trading coach who teaches people how to understand the stock market.

Your personality:
- Encouraging and patient — many users are beginners
- Clear and plain-English — never use jargon without explaining it
- Honest about risk — always mention that trading carries risk
- Educational — every answer teaches something
- Specific — give concrete examples with real numbers when helpful

Your expertise:
- Technical analysis (RSI, MACD, moving averages, Bollinger Bands, candlestick patterns)
- Market structure (support/resistance, trends, volume analysis)
- Risk management (position sizing, stop-losses, risk/reward ratios)
- Whale/institutional flow (what it means when big money moves)
- Trading psychology (emotion management, discipline, consistency)
- Paper trading strategy (how to practice effectively)

When explaining a signal:
1. Start with what the signal IS in plain English
2. Explain WHY the indicators are showing this
3. What would CHANGE the signal (what to watch for)
4. Concrete risk management advice (stop loss, position size)
5. What this TEACHES the user about trading

Always end responses that involve real trading with:
"⚠️ Remember: Practice with paper trading first. Never risk money you can't afford to lose."

Keep responses concise — 3-5 paragraphs max unless the user asks for more detail."""


class MentorMessage(BaseModel):
    message: str
    context: Optional[dict] = None   # current signal, symbol, price data


class MentorResponse(BaseModel):
    reply: str
    timestamp: str


async def call_claude(messages: list, system: str) -> str:
    """Call Claude API for mentor responses."""
    if not CLAUDE_API_KEY:
        return _mock_mentor_response(messages[-1]["content"] if messages else "")

    try:
        import httpx
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={
                    "x-api-key":         CLAUDE_API_KEY,
                    "anthropic-version": "2023-06-01",
                    "content-type":      "application/json",
                },
                json={
                    "model":      "claude-sonnet-4-5",
                    "max_tokens": 1024,
                    "system":     system,
                    "messages":   messages,
                }
            )
            if r.status_code == 200:
                data = r.json()
                return data["content"][0]["text"]
            else:
                log.error(f"Claude API error: {r.status_code} {r.text}")
                return _mock_mentor_response(messages[-1]["content"])
    except Exception as e:
        log.error(f"Claude call failed: {e}")
        return _mock_mentor_response(messages[-1]["content"])


def _mock_mentor_response(question: str) -> str:
    """Fallback mentor responses when API key not set."""
    q = question.lower()
    if "rsi" in q:
        return """Great question! RSI stands for Relative Strength Index — it's a momentum indicator that measures how overbought or oversold a stock is on a scale of 0 to 100.

**Here's how to read it:**
- RSI below 30 → stock is *oversold* — it may have dropped too far, too fast, and could bounce back
- RSI above 70 → stock is *overbought* — it may have risen too fast and could pull back
- RSI around 50 → neutral territory, no strong signal either way

Think of RSI like a rubber band. If you stretch it too far in one direction, it tends to snap back. RSI helps you see when a stock has been "stretched" too far.

**Important:** RSI works best in sideways markets. In a strong uptrend, RSI can stay above 70 for a long time — that's not necessarily a sell signal, it just means the trend is strong.

⚠️ Remember: Practice with paper trading first. Never risk money you can't afford to lose."""

    if "macd" in q:
        return """MACD (Moving Average Convergence Divergence) sounds complicated but it's actually simple once you get it!

**What it is:** MACD compares two moving averages of a stock's price to show momentum and trend direction.

**The three parts:**
1. MACD Line — the difference between 12-day and 26-day averages
2. Signal Line — 9-day average of the MACD line
3. Histogram — the gap between MACD and Signal lines

**How to use it:**
- When MACD crosses ABOVE the signal line → bullish signal (potential buy)
- When MACD crosses BELOW the signal line → bearish signal (potential sell)
- When the histogram grows bigger → momentum is increasing

**In plain English:** MACD tells you if a stock's short-term behavior is getting faster or slower compared to its longer-term trend. A bullish MACD crossover means short-term buying is accelerating.

⚠️ Remember: Practice with paper trading first. Never risk money you can't afford to lose."""

    if "whale" in q or "institutional" in q:
        return """Whale tracking is one of AlphaIQ's most powerful features — let me explain what it means!

**Who are "whales"?** These are institutional investors — hedge funds, mutual funds, investment banks — that move millions or billions of dollars at a time. When a whale buys or sells, it can move the entire market.

**Why track them?** Retail traders (like you and me) often trade on news and emotions. Whales trade on deep research and inside knowledge of market structure. Following the smart money can give you an edge.

**How AlphaIQ detects whales:**
- Volume spikes: if a stock suddenly trades 3x+ its average volume, big money is moving
- Dollar flow: we track how much actual money (not just shares) is being traded
- Price impact: large orders leave footprints in the order book

**What to do with this info:**
- 🐳 Whale buying + bullish signal = stronger conviction to consider a trade
- 🐳 Whale selling + bearish signal = extra caution is warranted
- Whale activity with no signal = something might be happening, worth watching

⚠️ Remember: Practice with paper trading first. Never risk money you can't afford to lose."""

    if "stop loss" in q or "risk" in q:
        return """Risk management is THE most important skill in trading — more important than picking winners!

**The stop-loss rule:** Before every trade, decide the maximum you're willing to lose. Then set your stop-loss at that level. Period. No exceptions.

**AlphaIQ recommends the 2% rule:**
- Never risk more than 2% of your total account on a single trade
- Example: $10,000 account → max $200 risk per trade
- If your stop-loss is $5 away from entry, you can buy 40 shares ($200 ÷ $5)

**Risk/Reward ratio:** Only take trades where potential profit is at least 2x potential loss
- Risk $200 to make $400 minimum → 2:1 ratio
- This means you can be wrong 40% of the time and still profit!

**The psychology:** Most beginners lose because they hold losing trades hoping they'll come back. Professional traders cut losses fast and let winners run. Your stop-loss is your promise to yourself.

⚠️ Remember: Practice with paper trading first. Never risk money you can't afford to lose."""

    # Default response
    return """Welcome to AlphaIQ's AI Mentor! I'm here to help you learn how to read the market like a pro.

**I can teach you about:**
- 📊 Technical indicators (RSI, MACD, moving averages, Bollinger Bands)
- 🐳 Whale tracking and institutional flow
- 📈 Chart patterns and candlestick analysis
- 🛡️ Risk management and position sizing
- 🧠 Trading psychology and discipline
- 🏆 How to use the Arena competitions to practice

**To get started, try asking me:**
- "What does RSI mean and how do I use it?"
- "Explain the MACD indicator"
- "How do I set a proper stop-loss?"
- "What are whales and why should I track them?"
- "How do I read candlestick patterns?"

Remember: The best traders never stop learning. Ask me anything!

⚠️ AlphaIQ provides education and signals only — not financial advice. Always practice with paper trading before using real money."""


@router.post("/chat")
async def mentor_chat(msg: MentorMessage, request: Request):
    """Send a message to the AI mentor and get a response."""
    db = request.app.state.db

    # Build context string if signal data provided
    context_str = ""
    if msg.context:
        ctx = msg.context
        context_str = f"""
Current market context:
- Symbol: {ctx.get('symbol', 'N/A')}
- Price: ${ctx.get('price', 'N/A')}
- Signal: {ctx.get('signal', 'N/A')}
- RSI: {ctx.get('rsi', 'N/A')}
- MACD trend: {ctx.get('macd_trend', 'N/A')}
- Volume spike: {ctx.get('vol_spike', False)}
- Whale activity: {ctx.get('is_whale', False)}
"""

    # Build full message with context
    full_message = msg.message
    if context_str:
        full_message = f"{context_str}\n\nUser question: {msg.message}"

    messages = [{"role": "user", "content": full_message}]
    reply = await call_claude(messages, SYSTEM_PROMPT)

    return {
        "reply":     reply,
        "timestamp": datetime.now().isoformat(),
    }


@router.get("/lessons")
async def get_lessons():
    """Get structured trading lessons."""
    return {
        "lessons": [
            {
                "id": "1",
                "title": "Understanding Candlestick Charts",
                "level": "Beginner",
                "duration": "5 min",
                "topics": ["What is a candlestick?", "Reading open/high/low/close", "Bullish vs bearish candles"],
                "prompt": "Explain candlestick charts to a complete beginner. What is each part of the candle?",
            },
            {
                "id": "2",
                "title": "RSI — The Momentum Meter",
                "level": "Beginner",
                "duration": "7 min",
                "topics": ["What RSI measures", "Oversold vs overbought", "How to use RSI in trades"],
                "prompt": "Teach me everything about RSI — what it is, how to read it, and how to use it in trading decisions.",
            },
            {
                "id": "3",
                "title": "MACD Crossovers",
                "level": "Intermediate",
                "duration": "8 min",
                "topics": ["MACD components", "Bullish crossover signals", "Divergence patterns"],
                "prompt": "Explain MACD in detail — all three components, how crossovers work, and what divergence means.",
            },
            {
                "id": "4",
                "title": "Whale Hunting 101",
                "level": "Intermediate",
                "duration": "10 min",
                "topics": ["Who are institutional traders?", "Volume analysis", "Dark pool activity", "Following smart money"],
                "prompt": "Teach me how to track whale and institutional activity. What volume patterns should I look for?",
            },
            {
                "id": "5",
                "title": "Risk Management Masterclass",
                "level": "Essential",
                "duration": "12 min",
                "topics": ["The 2% rule", "Stop-loss placement", "Risk/reward ratios", "Position sizing"],
                "prompt": "Give me a complete masterclass on trading risk management — position sizing, stop losses, and the 2% rule.",
            },
            {
                "id": "6",
                "title": "Reading Market Structure",
                "level": "Advanced",
                "duration": "15 min",
                "topics": ["Support and resistance", "Higher highs and lower lows", "Trend identification", "Breakout patterns"],
                "prompt": "Explain market structure — support, resistance, trends, and how to identify breakout patterns.",
            },
        ]
    }
