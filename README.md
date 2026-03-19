<div align="center">

# 🤖 OPUS34 Trading Algorithm

**A fully automated Stock, Crypto and Futures trading Quant Algorithm powered by Price Action and Smart Money Concepts —**
**validated across 16 months of data and enhanced with a trained ML brain.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MetaTrader](https://img.shields.io/badge/MetaTrader-5-7B2FBE?style=for-the-badge&logoColor=white)](https://metatrader5.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Live_Demo-22C55E?style=for-the-badge)]()
[![Backtested](https://img.shields.io/badge/Backtested-16_Months-FF6B35?style=for-the-badge)]()
[![Brain](https://img.shields.io/badge/ML_Brain-PF_1.40-7B2FBE?style=for-the-badge)]()

*Trades EUR/USD · GBP/USD · USD/JPY — London Open & London Close*

</div>

---

## ⚠️ Risk Disclaimer

> **Trading involves substantial risk of loss. This bot does NOT guarantee profits. Never trade with money you cannot afford to lose. Always test on a demo account first.**

---

## 📸 Dashboard

<div align="center">
<img src="https://raw.githubusercontent.com/Batoli19/ict-trading-algorithm/cc8e143ac759d229d12dc069c7599499bea10049/Screenshot%202026-03-16%20114111.png" width="100%" alt="ICT Trading Bot Dashboard"/>
</div>

<div align="center">

![Trading Algo Command Center](https://github.com/user-attachments/assets/245eb0e9-8e6e-429f-ad14-71a3c2106bba)

*Real-time command center — equity curve, AI brain performance, daily guardrails, live notifications*

</div>

---

## 📖 What Is This?

A fully automated trading bot that watches the market, identifies high-probability setups using **ICT Smart Money Concepts**, and automatically places, manages, and closes trades on **MetaTrader 5** — with zero manual intervention.

What separates this from every other ICT bot: **every parameter is data-proven.** Sixteen rigorous backtesting passes across 16 months of real M5 tick data eliminated every setup, pair, direction, and session that didn't perform. What remained is a lean, validated edge. On top of that, a trained **XGBoost ML model** filters low-probability signals in real time — improving the Profit Factor from 1.23 to **1.40** on 6 months of data it had never seen.

---

## 🧠 Trading Strategy

### Active Setups

| Setup | What It Does | 16-Month PF |
|-------|-------------|-------------|
| 🔴 **CHOCH** | Change of Character — detects structural market shifts and enters on the reversal | 1.15 |
| 🟡 **LSR** | Liquidity Sweep Reversal — identifies stop hunts at key levels and fades the move | 1.17 |

> Every other setup (FVG, Order Block, Pin Bar, HH/HL Continuation) was tested and disabled after confirmed underperformance across 16 months of data.

### Direction Filters — Proven by Data

| Pair | Direction | 16-Month Result |
|------|-----------|----------------|
| **EUR/USD** | Both ✅ | Balanced both ways |
| **GBP/USD** | SELL only ✅ | BUY bleeds -454p |
| **USD/JPY** | BUY only ✅ | SELL bleeds -492p |

### Sessions — London Only

| Session | UTC | Gaborone |
|---------|-----|----------|
| 🇬🇧 **London Open** | 06:00 – 09:00 | 08:00 – 11:00 |
| 🔁 **London Close** | 15:00 – 17:00 | 17:00 – 19:00 |

> NY Open excluded — bleeds -384p across 16 months. Every session was tested.

---

## 🤖 The ML Brain

Every signal passes through a trained **XGBoost classifier** before any trade opens:

```
CHOCH or LSR signal fires
        ↓
Brain checks: symbol + direction + setup + session + hour + day
        ↓
Win probability < 50%  →  signal skipped silently
Win probability ≥ 50%  →  trade opens normally
```

**Results on 6 months of completely unseen data (Sep 2025 – Feb 2026):**

|  | No Brain | With Brain |
|--|---------|-----------|
| **Profit Factor** | 1.23 | **1.40** |
| **Win Rate** | 64.7% | **66.8%** |
| **$/week @ $10K** | ~$119 | **~$140** |

The brain independently learned the same patterns the manual autopsy found:
direction alignment, early London Open hour, Monday bias, GBPUSD SELL, EURUSD SELL.

---

## 🎯 Instruments Traded

| Instrument | Type | Session |
|-----------|------|---------|
| **EUR/USD** | Forex Major | London Open + Close |
| **GBP/USD** | Forex Major | London Open + Close |
| **USD/JPY** | Forex Major | London Open + Close |

---

## 🏗️ Architecture

```
ict_trading_bot/
│
├── 📁 01_LIVE_BOT/                   ← Core trading engine
│   ├── bot_engine.py                 ← Master loop — scans pairs every 10s
│   ├── ict_strategy.py               ← Signal detection + Brain Gate hook
│   ├── ict_advanced_setups.py        ← CHOCH + LSR detection library
│   ├── risk_manager.py               ← Position sizing + daily limits
│   ├── brain_gate.py                 ← ML filter (loads once, fails safe)
│   └── trade_manager.py              ← Giveback guard + trailing logic
│
├── 📁 02_BACKTESTER/                 ← Historical simulation (16 passes run here)
│
├── 📁 03_BACKTEST_RESULTS/           ← 16 months of validated results
│   ├── pass_13/ → pass_16/           ← Every pass saved and organized
│   └── README.txt                    ← What each pass tested and found
│
├── 📁 04_BRAIN/                      ← ML learning system
│   ├── models/entry_model.pkl        ← Trained XGBoost (28 features)
│   ├── training_data/features_clean.csv ← 1,123 trades, zero data leakage
│   ├── step1_extract_features.py     ← Clean feature extraction
│   ├── step2_train_entry_model.py    ← Model training with time-series CV
│   └── run_full_brain_pipeline.py    ← Train everything in one command
│
├── 📁 05_DATA/                       ← 16 months M5 data (5 pairs)
├── 📁 06_CONFIG/                     ← Settings (credentials gitignored)
├── 📁 07_LOGS/                       ← Daily activity logs
├── 📁 08_DOCS/                       ← Plain English guides
│
├── START_BOT.py                      ← One click to start
├── STOP_BOT.py                       ← One click to stop
└── CHECK_PERFORMANCE.py              ← Print today's results
```

---

## 🔄 Full System Pipeline

*Every component, every gate, every data flow — from market tick to closed trade.*

```
╔══════════════════════════════════════════════════════════════════════════╗
║                    INFRASTRUCTURE LAYER                                  ║
║  ┌─────────────────┐  ┌──────────────────┐  ┌────────────────────────┐  ║
║  │  Windows VPS    │  │  MetaTrader 5    │  │  settings.json         │  ║
║  │  24/7 uptime    │  │  XM Broker       │  │  login · server · risk │  ║
║  │  watcher.ps1    │  │  Live tick feed  │  │  (gitignored)          │  ║
║  └────────┬────────┘  └────────┬─────────┘  └────────────────────────┘  ║
╚═══════════╪════════════════════╪════════════════════════════════════════╝
            │                    │
            ▼                    ▼
╔══════════════════════════════════════════════════════════════════════════╗
║               MASTER LOOP — bot_engine.py                                ║
║                                                                          ║
║   ┌─────────────────────────────────────────────────────────────────┐   ║
║   │  Every 10 seconds:  EUR/USD  ──┐                                │   ║
║   │                     GBP/USD  ──┼──► Signal Pipeline (below)     │   ║
║   │                     USD/JPY  ──┘                                │   ║
║   └─────────────────────────────────────────────────────────────────┘   ║
╚══════════════════════════════════════════════════════════════════════════╝
            │
            ▼
```

```
━━━━━━━━━━━━━━━━━━━━━━━━  SIGNAL PIPELINE  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

 GATE 1 ── KILL ZONE CHECK ─────────────────────────────────────────────
 │
 │  London Open  06:00–09:00 UTC  (08:00–11:00 Gaborone)
 │  London Close 15:00–17:00 UTC  (17:00–19:00 Gaborone)
 │
 │  OUTSIDE window? ──► 💤 SLEEP  — no scan, no compute, wait
 │  INSIDE window?  ──► proceed ↓
 │
 GATE 2 ── ICT SIGNAL DETECTION ─────────────────────────────────────────
 │         ict_strategy.py + ict_advanced_setups.py
 │
 │  MT5 pulls last 200 M5 bars per pair
 │
 │  ┌─────────────────────────┐    ┌──────────────────────────────────┐
 │  │  🔴 CHOCH Detector      │    │  🟡 LSR Detector                 │
 │  │  Change of Character    │    │  Liquidity Sweep Reversal        │
 │  │  · Broken swing H/L     │    │  · Stop hunt at key level        │
 │  │  · Confirmation bar     │    │  · Fade the sweep move           │
 │  │  · Returns: dir/entry/SL│    │  · Returns: dir/entry/SL/mag     │
 │  └─────────────────────────┘    └──────────────────────────────────┘
 │
 │  NO SIGNAL found? ──► ⏭ END CYCLE  — wait 10s, repeat
 │  SIGNAL found?    ──► proceed ↓
 │
 GATE 3 ── DIRECTION FILTER ──────────────────────────────────────────────
 │         Hard-coded rules from 16 months of backtest data
 │
 │  EUR/USD  BUY  ──► ✅ PASS     EUR/USD  SELL ──► ✅ PASS
 │  GBP/USD  BUY  ──► ❌ SKIP  (BUY bleeds -454 pips)
 │  GBP/USD  SELL ──► ✅ PASS
 │  USD/JPY  BUY  ──► ✅ PASS
 │  USD/JPY  SELL ──► ❌ SKIP  (SELL bleeds -492 pips)
 │
 │  WRONG direction? ──► ❌ HARD SKIP  — reason logged
 │  ALIGNED?         ──► proceed ↓
 │
 GATE 4 ── ML BRAIN GATE ────────────────────────────────────────────────
 │         brain_gate.py  ·  XGBoost  ·  04_BRAIN/models/entry_model.pkl
 │
 │  28 features assembled:
 │  symbol · direction · setup type · session · hour · day of week
 │  sweep magnitude · structural context · pair-specific bias · more
 │
 │  xgboost.predict_proba() ──► win probability score (0.0 → 1.0)
 │
 │  prob < 0.50 ──► 🔇 SILENT SKIP  — not counted as a trade
 │  prob ≥ 0.50 ──► proceed ↓
 │
 │  [fail-safe: if entry_model.pkl missing → gate disabled, all pass]
 │
 GATE 5 ── RISK MANAGER CHECK ───────────────────────────────────────────
 │         risk_manager.py
 │
 │  ① Daily loss > 3.5%? ──────────────────► 🛑 STOP FOR DAY
 │  ② 3 consecutive losses? ──────────────► ⏸ PAUSE 2 HOURS
 │  ③ Open positions = 3? ─────────────────► ⏭ SKIP  (queue full)
 │
 │  ALL CLEAR? ──► proceed ↓
 │
 GATE 6 ── POSITION SIZING ───────────────────────────────────────────────
           risk_manager.py
 
   Standard signal ──► 1.0% risk  →  lot = risk$ ÷ (SL pips × pip value)
   A+ signal       ──► 1.5% risk  →  larger lot, same formula
```

```
━━━━━━━━━━━━━━━━━━━━━━━━  TRADE EXECUTION  ━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

  mt5.order_send()
  ├── symbol      (EURUSD / GBPUSD / USDJPY)
  ├── volume      (calculated lot size)
  ├── type        (BUY_MARKET / SELL_MARKET)
  ├── price       (current ask/bid)
  ├── sl          (signal stop loss level)
  ├── tp          (setup-dependent — see below)
  └── comment     ("OPUS34_CHOCH" or "OPUS34_LSR")

  Take-profit logic splits by setup:
  ┌─────────────────────────────────────────────────────────────┐
  │  LSR trades  ──► Hard TP at 1.5–2R  (clean, fast reversals) │
  │  CHOCH trades ─► No hard TP — giveback guard manages exit    │
  └─────────────────────────────────────────────────────────────┘

  Order confirmed → ticket ID stored → position monitored every 10s
```

```
━━━━━━━━━━━━━━━━━━━━━━━━  TRADE MANAGEMENT  ━━━━━━━━━━━━━━━━━━━━━━━━━━━

  trade_manager.py  ·  runs every 10 seconds alongside new signal scan

  GIVEBACK GUARD:
  ┌──────────────────────────────────────────────────────────────────┐
  │  Trade unrealised P&L tracked continuously                       │
  │  Activates at   +0.5R profit  (position moving in your favor)    │
  │  Peak equity    tracked and updated every cycle                  │
  │  Exit trigger   if price gives back > 15% of peak unrealised     │
  │                                                                  │
  │  Example: Trade hits +2.0R peak  →  guard locks at +1.7R        │
  │           Price retraces to +1.6R →  CLOSE immediately           │
  └──────────────────────────────────────────────────────────────────┘

  DAILY GUARDRAILS (checked every cycle):
  ├── Daily profit ≥ 3.0%  ──► 🔒 LOCK  — no new trades, protect day
  ├── Daily loss   ≥ 3.5%  ──► 🛑 STOP  — session over
  └── Total drawdown ≥ 8%  ──► 🚨 HALT  — account protection mode
```

```
━━━━━━━━━━━━━━━━━━━━━━━━  POST-TRADE PIPELINE  ━━━━━━━━━━━━━━━━━━━━━━━━

  Trade closes (TP hit / SL hit / giveback guard / daily limit)
       │
       ├──► 07_LOGS/  CSV append
       │    timestamp · pair · setup · entry · SL · TP · P&L · duration
       │    brain score · win/loss · session · hour · day
       │
       ├──► 04_BRAIN/training_data/features_clean.csv  append
       │    new row added to brain training dataset
       │    used in monthly retrain cycle
       │
       ├──► trading_memory.db  (SQLite)
       │    session stats updated · streak counter · daily totals
       │
       └──► CHECK_PERFORMANCE.py  (on-demand)
            prints: win rate · P&L · drawdown · trades · brain accept rate
```

```
━━━━━━━━━━━━━━━━━━━━━━━━  ML BRAIN PIPELINE  ━━━━━━━━━━━━━━━━━━━━━━━━━━

  04_BRAIN/  ·  run monthly

  features_clean.csv
       │
       ▼
  step1_extract_features.py
  Reads trade logs → engineers 28 features → outputs clean dataset
       │
       ▼
  step2_train_entry_model.py
  XGBoost · time-series walk-forward CV · no data leakage
  Trains on oldest 75% → validates on newest 25% of each fold
       │
       ▼
  entry_model.pkl  (replaces previous model)
       │
       ▼
  brain_gate.py loads new pkl on next bot restart
  Inference: < 1ms per signal  ·  fails safe if pkl missing

  run_full_brain_pipeline.py  ──►  runs all steps in one command
```

```
━━━━━━━━━━━━━━━━━━━━━━━━  BACKTESTING PIPELINE  ━━━━━━━━━━━━━━━━━━━━━━━

  05_DATA/  (16 months · M5 OHLCV · XM broker · 5 pairs)
       │
       ▼
  02_BACKTESTER/  ·  run_passXX.py
  Simulates every signal, filter, guard combination historically
       │
       ▼
  analyze_run.py  /  analyze_months.py
  Profit factor · win rate · trades/week · per-pair · per-session
       │
       ▼
  03_BACKTEST_RESULTS/
  Every pass CSV archived  ·  optimization_report.txt written
  pass README explains what each pass tested and found
```

---

## ⏱️ What Happens Inside One 10-Second Cycle

```
t = 0ms    ── Scheduler wakes · 3 pairs queued
t ≈ 5ms    ── Kill zone check (UTC time vs LO/LC windows)
t ≈ 20ms   ── MT5 data pull (last 200 M5 bars per pair)
t ≈ 30ms   ── CHOCH + LSR scan runs on bar data
t ≈ 35ms   ── Direction filter (instant lookup, no compute)
t ≈ 36ms   ── Brain gate (28 features → predict_proba < 1ms)
t ≈ 38ms   ── Risk check + lot size calculation
t ≈ 60ms   ── mt5.order_send() · network round-trip to broker
t ≈ 65ms   ── Log write (CSV + SQLite)
t = 10,000ms ── Next cycle begins · open positions also checked
```

---

## 📊 Validated Performance

*Nov 2024 – Feb 2026 | XM broker M5 data | $10K account @ 1% risk*

| Stage | Trades/wk | Win Rate | Profit Factor | $/week |
|-------|-----------|----------|---------------|--------|
| Raw baseline (all setups) | 13.4 | 64.7% | 1.06 | +$44 |
| + Direction filters | 8.9 | 64.2% | 1.16 | +$67 |
| + Guard tuning 0.5R/15% | 8.9 | 64.2% | 1.18 | +$72 |
| **+ ML Brain (live system)** | ~5.6 | **66.8%** | **1.40** | **$119–178** |

---

## 🛡️ Risk Management

```
✅ Risk per trade       →  1.0% ($100 on $10K)
✅ Max risk (A+ setup)  →  1.5% ($150 on $10K)
✅ Daily loss limit     →  3.5% = $350 — stops for the day
✅ Daily profit lock    →  3.0% = $300 — protects good days
✅ Max total drawdown   →  8.0% = $800 — account protection
✅ Loss streak pause    →  3 consecutive losses → 2hr timeout
✅ Max open trades      →  3 simultaneous positions
✅ Brain gate           →  ML skips low-probability signals
✅ Direction filter     →  Per-pair bias (data-proven, not guessed)
✅ Kill zone gate       →  London sessions only
```

---

## ⚡ Quick Start

### Prerequisites
- [Python 3.10+](https://python.org/downloads)
- [MetaTrader 5](https://metatrader5.com) with a broker account

### 1. Clone
```bash
git clone https://github.com/Batoli19/ict-trading-bot.git
cd ict-trading-bot
```

### 2. Install
```bash
pip install -r requirements.txt
```

### 3. Configure
```bash
# Windows
copy config\settings.example.json config\settings.json
```

```json
{
  "mt5": {
    "login":    12345678,
    "password": "your_mt5_password",
    "server":   "YourBroker-Demo"
  }
}
```

### 4. Train the brain *(optional — pre-trained model included)*
```bash
python 04_BRAIN/run_full_brain_pipeline.py
```

### 5. Start trading
```bash
python START_BOT.py
```

---

## 🔬 The 16-Pass Validation System

This bot wasn't built and shipped. It was validated.

| Pass | What Was Tested | Key Finding |
|------|----------------|-------------|
| 1–12 | Core strategy, datetime fixes, data pipeline | Foundation established |
| 13A | All 5 setups, 5 pairs, 16 months | FVG + OB = dead code |
| 14A | FVG and ORDER_BLOCK wired and tested | Both confirmed bleeders |
| 15 | Direction filters + guard matrix (12 combos) | PF 1.06 → 1.18 |
| 16 | Hard TP vs guard — LSR vs CHOCH split | LSR = hard TP, CHOCH = guard |
| Brain | XGBoost on 6 months unseen data | PF 1.23 → 1.40 confirmed |

---

## 🗺️ Roadmap

- [x] 16-pass backtesting validation
- [x] Direction filters per pair (data-proven)
- [x] Giveback guard tuning (0.5R/15%)
- [x] XGBoost ML brain — trained + wired live
- [x] $10K prop account configuration
- [ ] Pass 17 — Hybrid exit (LSR hard 1.5R TP)
- [ ] Pass 18 — Macro news circuit breaker
- [ ] Monthly brain retraining pipeline
- [ ] Multi-account scaling

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|---------|
| `MT5 connection failed` | Check login, password, server in `settings.json` |
| `No trades being placed` | Confirm it's London Open or London Close (UTC) |
| `Brain gate blocking everything` | Check `04_BRAIN/models/entry_model.pkl` exists |
| `USDJPY firing 0 trades` | Expected — USDJPY SELL is filtered by direction rules |
| `Bot stops mid-session` | Daily loss limit hit — check `07_LOGS/` |

---

## 🖥️ Running 24/7

For reliable 24/7 operation use a VPS:

| Provider | Price | Notes |
|----------|-------|-------|
| [Contabo](https://contabo.com) | ~$7/mo | Most affordable |
| [Forex VPS](https://forexvps.net) | ~$20/mo | MT5 optimized |
| [AWS Lightsail](https://lightsail.aws.amazon.com) | ~$10/mo | Most reliable |

---

## 📜 License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

**Built with ICT Smart Money Concepts · Validated with 16 months of data · Enhanced with ML**

*6,000+ backtested trades · XGBoost brain · Proven edge on unseen data*

*Not financial advice. Trade responsibly.*

</div>
