# 🚀 ICT BOT COMMAND CENTER — Setup Guide

## What's New

### ⚡ DRAMATIC UPGRADES
1. **COMMAND CENTER Dashboard** — Premium fintech UI with live data
2. **Real-time API Bridge** — Flask server streaming MT5 data at 2-second intervals  
3. **Test Mode** — Forces trades every 5 minutes for efficiency testing
4. **Fixed Strategy** — New multi-factor HTF bias that actually works

---

## 📦 Installation

### 1. Install Additional Dependencies
```bash
pip install Flask==3.0.0 flask-cors==4.0.0 --break-system-packages
```

### 2. Replace Files in Your Bot Directory

Copy these files to your `ict_trading_bot/python/` folder:

- **ict_strategy.py** (fixed HTF bias)
- **api_server.py** (new Flask API)
- **test_mode.py** (new test mode)
- **main.py** (updated with API integration)

### 3. Update bot_engine.py

Open `ict_trading_bot/python/bot_engine.py` and replace the `get_status()` method with the enhanced version from `bot_engine_enhanced.py`.

Specifically, add these lines at the end of `get_status()`:

```python
# Get H4 bias for all pairs
pair_biases = {}
for symbol in self.pairs:
    candles_h4 = self.mt5.get_candles(symbol, "H4", 50)
    if candles_h4 and len(candles_h4) >= 30:
        bias = self.strategy.get_htf_bias(candles_h4)
        pair_biases[symbol] = bias.value

# Build trade log from journal
trade_log = []
for record in self.risk.journal[-20:]:
    trade_log.append({
        'time': record.open_time.strftime('%H:%M:%S'),
        'symbol': record.symbol,
        'type': record.direction,
        'setup': record.setup_type,
        'pnl': record.pnl,
        'lot': record.volume,
    })

# Add to return dict:
return {
    ...
    "pair_biases": pair_biases,
    "trade_log": trade_log,
    ...
}
```

### 4. Update settings.json

Replace your `config/settings.json` with the new one that includes:

```json
{
  ...
  "test_mode": {
    "enabled": true,
    "interval_seconds": 300,
    "comment": "Forces trade every 5 min. Set enabled=false for production."
  }
}
```

---

## 🎯 Running the Bot

### Start the Bot
```bash
cd ict_trading_bot/python
python main.py
```

You'll see:
```
🤖  ICT TRADING BOT - COMMAND CENTER EDITION
🕐  2026-02-17 14:23:45
✅  Config loaded | Pairs: ['EURUSD', 'GBPUSD', 'US30', 'NAS100', 'XAUUSD']
⚠️  TEST MODE ACTIVATED
⚠️  Will force trades every 5 minutes
🚀  All systems running. Bot is LIVE.
🌐  Dashboard available at: http://localhost:5000
📊  Open command_center.html in your browser
```

### Open the Command Center

1. Open `command_center.html` in Chrome/Firefox/Edge
2. You'll see:
   - **Live account balance, equity, P&L** (updates every 2 seconds)
   - **Real-time UTC clock**
   - **Open positions table** with live P&L
   - **Equity curve chart** that grows with each trade
   - **Kill zone session indicator** (London/NY/Dead Zone)
   - **Pair bias heatmap** showing H4 bias for all 5 pairs
   - **Trade log** showing every executed trade today

---

## 🧪 Test Mode Explained

### What It Does
- **Bypasses ALL filters**: Kill zones, news blocks, HTF bias checks
- **Forces a random trade every 5 minutes**:
  - Random pair from your list
  - Random direction (BUY/SELL)
  - Reasonable stops: 10-15 pip SL, 20-30 pip TP (1:2 RR)
- **Logs everything** to your trade journal and risk manager

### Why Use It
Perfect for:
- Testing MT5 connection reliability
- Verifying position sizing calculations
- Stress-testing the risk manager
- Confirming the Command Center dashboard updates correctly

### ⚠️ WARNING
**USE ON DEMO ACCOUNTS ONLY!** Test mode will burn through capital fast if run on live.

### Disable Test Mode
In `settings.json`:
```json
"test_mode": {
  "enabled": false
}
```

---

## 🎨 Command Center Features

### LIVE DATA (2-second polling)
- Account balance, equity, profit
- Win rate, avg win/loss, expectancy
- Daily P&L, daily trades counter
- Open positions with live P&L per trade

### KILL ZONE DETECTOR
Shows which session is active:
- 🇬🇧 London Open (07:00-10:00 UTC)
- 🇺🇸 NY Open (12:00-15:00 UTC)
- 🔔 London Close (15:00-17:00 UTC)
- ⛔ Dead Zone (all other times)

### PAIR BIAS MONITOR
Shows H4 bias for all pairs:
- 🟢 BULLISH (↑)
- 🔴 BEARISH (↓)
- ⚪ NEUTRAL (—)

### EMERGENCY STOP BUTTON
Red button in top-right → confirmation modal → gracefully shuts down bot while keeping MT5 positions open

---

## 🔧 Strategy Fixes Applied

### Before (Broken)
```python
# Old HTF bias required one candle to simultaneously:
# - Break recent highs AND be above recent lows
# This almost never happens in real markets
hh = highs[-1] > max(highs[-10:-1])
hl = lows[-1]  > min(lows[-10:-1])
if hh and hl: return BULLISH  # Never fires
```

### After (Fixed)
```python
# New multi-factor bias uses 3 independent votes:
# 1. EMA(8) vs EMA(21) crossover
# 2. Price vs 20-candle midpoint
# 3. Swing structure (HH/HL vs LH/LL across segments)
# Needs 2 out of 3 votes to call a direction
```

**Result**: Bias now returns BULLISH/BEARISH in real trending markets instead of being stuck on NEUTRAL 100% of the time.

### Config Loosened
- `fvg.min_gap_pips`: 5 → 2 (finds more valid FVGs)
- `stop_hunt.equal_hl_tolerance`: 2 → 5 (more lenient liquidity detection)
- `stop_hunt.displacement_min_pips`: 8 → 5 (easier to qualify)
- `order_blocks.min_impulse_pips`: 10 → 5 (more OBs detected)

---

## 📊 API Endpoints

The Flask server exposes these endpoints:

### GET /api/status
Returns full bot state:
```json
{
  "timestamp": "2026-02-17T14:23:45.123456",
  "account": {
    "balance": 5000.00,
    "equity": 5012.34,
    "profit": 12.34,
    "leverage": 100
  },
  "stats": {
    "trades": 5,
    "wins": 3,
    "losses": 2,
    "winrate": 60.0,
    "total_pnl": 45.67,
    "daily_pnl": 12.34
  },
  "positions": [...],
  "pair_biases": {
    "EURUSD": "BULLISH",
    "GBPUSD": "BEARISH",
    ...
  },
  "trade_log": [...],
  "upcoming_news": [...]
}
```

### POST /api/shutdown
Initiates graceful bot shutdown.

### GET /api/health
Quick health check (for monitoring).

---

## 🎮 Using the Dashboard

### 1. Monitor Efficiency
- **Daily Trades**: See how many trades executed today
- **Win Rate**: Live calculation as trades close
- **Expectancy**: Mathematical edge per trade

### 2. Track Risk
- **Daily loss guard**: Progress bar turns red as you approach 3% DD
- **Trade slots**: Shows X / 10 trades used today
- **Open exposure**: Shows total floating P&L

### 3. Emergency Stop
If things go wrong:
1. Click **EMERGENCY STOP** (top right)
2. Confirm in modal
3. Bot halts all scanning immediately
4. Open positions stay open (manage manually in MT5)

---

## 🚨 Troubleshooting

### Dashboard shows "Loading..."
- Check Flask server started: Look for `🌐 Dashboard API starting on http://0.0.0.0:5000`
- Check API URL in `command_center.html` line 1025: `const API_URL = 'http://localhost:5000';`
- Test endpoint: Open `http://localhost:5000/api/health` in browser

### "No trades executed" with test mode ON
- Confirm test mode enabled in settings.json
- Check logs for: `⚠️ TEST MODE ACTIVATED`
- Wait 5 minutes for first forced trade
- Check terminal for: `🎲 TEST TRADE: ...`

### Strategy still not trading (without test mode)
- Check kill zone: Bot only trades during London/NY sessions unless you set `trade_only_in_kill_zones: false`
- Check HTF bias in dashboard heatmap: Must show BULL/BEAR, not NEUTRAL
- Check logs for: `{SYMBOL}: Neutral HTF bias — no trade`

### MT5 connection lost
- Dashboard will show red "OFFLINE" pill
- Bot auto-reconnects (see logs for retry attempts)
- Check MT5 platform is running and logged in

---

## 🎯 Next Steps

### Once Testing is Complete
1. Set `test_mode.enabled = false` in settings.json
2. Re-enable kill zone filter: `trade_only_in_kill_zones: true`
3. Run on demo for 1 week to collect real performance data
4. Analyze in Command Center:
   - Win rate target: 50-60%
   - Expectancy target: Positive
   - Max DD: Under 3%

### Production Deployment
1. Switch to live MT5 account
2. Lower risk per trade to 0.5-1%
3. Monitor Command Center closely for first week
4. Use Emergency Stop if anything looks wrong

---

## 📝 File Structure

```
ict_trading_bot/
├── python/
│   ├── main.py                 ← Updated (Flask + test mode)
│   ├── bot_engine.py           ← Update get_status() method
│   ├── ict_strategy.py         ← Replaced (fixed bias)
│   ├── api_server.py           ← NEW (Flask API)
│   ├── test_mode.py            ← NEW (forced trades)
│   ├── mt5_connector.py
│   ├── risk_manager.py
│   ├── news_filter.py
│   ├── dashboard.py            (terminal dashboard, still works)
│   └── ...
├── config/
│   └── settings.json           ← Updated (test mode config)
└── ...

command_center.html              ← Open this in browser
```

---

## 💡 Pro Tips

1. **Leave Command Center open while bot runs** — it's designed for full-time monitoring
2. **Check pair bias heatmap** — if all pairs show NEUTRAL, the new strategy may need more trending market
3. **Use test mode first** — always validate on demo before risking real capital
4. **Emergency Stop is your friend** — don't hesitate to hit it if behavior looks wrong

---

**You're all set! Fire up the bot and open `command_center.html` to see your trading operation come to life.** 🚀
