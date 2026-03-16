<div align="center">

<img src="https://github.com/user-attachments/assets/245eb0e9-8e6e-429f-ad14-71a3c2106bba" width="100%" alt="ICT Trading Bot Dashboard"/>

# ICT Trading Algorithm

**A fully automated Forex trading bot powered by ICT Smart Money concepts, validated across 16 months of historical data, and enhanced with a trained ML brain.**

[![Python](https://img.shields.io/badge/Python-3.10+-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://python.org)
[![MetaTrader](https://img.shields.io/badge/MetaTrader-5-7B2FBE?style=for-the-badge&logoColor=white)](https://metatrader5.com)
[![License](https://img.shields.io/badge/License-MIT-22C55E?style=for-the-badge)](LICENSE)
[![Status](https://img.shields.io/badge/Status-Live_Demo-22C55E?style=for-the-badge)]()
[![Validated](https://img.shields.io/badge/Backtested-16_Months-FF6B35?style=for-the-badge)]()

*Trades EUR/USD · GBP/USD · USD/JPY — London Open & London Close only*

</div>

---

## ⚠️ Risk Disclaimer

> **Trading involves substantial risk of loss. This bot does NOT guarantee profits. Never trade with money you cannot afford to lose. Always test on a demo account first.**

---

## 📸 Dashboard Preview

<div align="center">

### Command Center — Live View
![Dashboard Dark Mode](https://github.com/user-attachments/assets/245eb0e9-8e6e-429f-ad14-71a3c2106bba)

*Real-time equity curve, AI brain performance tracking, daily guardrails, and trade notifications — all in one view.*

</div>

---

## 📖 What Is This?

This is a battle-tested, fully automated trading bot built on **ICT (Inner Circle Trader) Smart Money Concepts**. It doesn't just follow rules — it has been scientifically validated across **16 months of M5 data** across multiple currency pairs, with each parameter proven through rigorous backtesting passes.

The bot is enhanced with a **trained ML brain** (XGBoost entry classifier) that filters low-probability signals in real time, improving the Profit Factor from 1.23 to 1.40 on unseen out-of-sample data.

---

## 🧠 What Makes This Different

Most bots are built on opinions. This one is built on evidence.

| What others do | What this bot does |
|---|---|
| Hardcode rules and hope | 16 passes of rigorous backtesting |
| Use all setups | Disabled every setup that bleeds |
| Trade all directions | Direction filters per pair (data-proven) |
| Fixed exits | Giveback guard tuned to 0.5R/15% |
| Generic confidence scores | XGBoost ML model trained on 1,123 real trades |
| Manual parameter guessing | 12-combo guard matrix tested exhaustively |

---

## 🎯 Active Trading Configuration

The system was locked after 16 validation passes. Only proven components are active:

### Active Setups
| Setup | What It Does | PF (16 months) |
|-------|-------------|----------------|
| **CHOCH** | Change of Character — detects market structure shifts | 1.15 |
| **LSR** | Liquidity Sweep Reversal — fades stop hunts at key levels | 1.17 |

### Active Pairs & Direction Filters
| Pair | Direction | Why |
|------|-----------|-----|
| **EUR/USD** | Both | Balanced performance both directions |
| **GBP/USD** | SELL only | BUY direction bleeds -454p over 16 months |
| **USD/JPY** | BUY only | SELL direction bleeds -492p over 16 months |

### Active Sessions
| Session | UTC Time | Gaborone Time |
|---------|----------|---------------|
| **London Open** | 06:00 – 09:00 | 08:00 – 11:00 |
| **London Close** | 15:00 – 17:00 | 17:00 – 19:00 |

*NY Open is excluded — bleeds -384p across 16 months of data.*

---

## 🤖 The ML Brain

The bot includes a trained XGBoost entry classifier that predicts win probability before every trade:

```
Signal fires → Brain checks win probability
  ≥ 50% → Trade opens normally  
  < 50% → Signal skipped silently
```

**Validated results on 6 months of unseen data (Sep 2025 – Feb 2026):**

| Metric | Without Brain | With Brain |
|--------|--------------|------------|
| Profit Factor | 1.23 | **1.40** |
| Win Rate | 64.7% | **66.8%** |
| $/week at $5K | $80 | **$86** |
| $/week at $25K | $395 | **$670** |

Top features the brain learned (independently confirmed our manual findings):
- `direction_aligned` — pair+direction combo quality
- `is_lo_early` — early London Open hour
- `is_monday` — Monday session bias
- `is_gbpusd_sell` — our strongest combo
- `is_lsr` — LSR setup quality

---

## 🏗️ System Architecture

```
ict_trading_bot/
│
├── 📁 01_LIVE_BOT/               ← The running bot (core engine)
│   ├── bot_engine.py             ← Master loop — scans pairs every 10s
│   ├── ict_strategy.py           ← Signal detection + Brain Gate integration
│   ├── ict_advanced_setups.py    ← CHOCH + LSR setup library
│   ├── risk_manager.py           ← Position sizing, daily limits, DD protection
│   ├── loss_analyzer.py          ← Adaptive learning layer
│   ├── brain_gate.py             ← ML entry filter (XGBoost, loads once)
│   └── trade_manager.py          ← Giveback guard, trailing, partial closes
│
├── 📁 02_BACKTESTER/             ← Historical simulation engine
│   ├── backtester.py             ← Core simulation (16 passes run here)
│   └── run_pass*.py              ← Individual validation pass scripts
│
├── 📁 03_BACKTEST_RESULTS/       ← All 16 passes of validated results
│   ├── pass_13/ through pass_16/ ← Organized by pass number
│   └── README.txt                ← What each pass tested and found
│
├── 📁 04_BRAIN/                  ← ML learning system
│   ├── models/
│   │   ├── entry_model.pkl       ← Trained XGBoost classifier
│   │   └── entry_model_features.json
│   ├── training_data/
│   │   └── features_clean.csv   ← 1,123 trades, zero leakage
│   ├── step1_extract_features.py
│   ├── step2_train_entry_model.py
│   └── run_full_brain_pipeline.py
│
├── 📁 05_DATA/                   ← 16 months M5 market data (5 pairs)
├── 📁 06_CONFIG/                 ← Settings files
├── 📁 07_LOGS/                   ← Daily activity logs
├── 📁 08_DOCS/                   ← Plain English guides
│
├── START_BOT.py                  ← One click to start
├── STOP_BOT.py                   ← One click to stop
└── CHECK_PERFORMANCE.py          ← Print today's results
```

---

## 🔄 System Workflow

```
Every 10 seconds:
┌─────────────────────────────────────────────────────────────┐
│  1. CHECK KILL ZONE                                         │
│     Is it London Open or London Close? If not → sleep      │
│                          ↓                                  │
│  2. SCAN SETUPS (CHOCH + LSR)                               │
│     ict_advanced_setups.scan_all_setups()                   │
│                          ↓                                  │
│  3. DIRECTION FILTER                                        │
│     GBPUSD SELL only · USDJPY BUY only · EURUSD both        │
│                          ↓                                  │
│  4. BRAIN GATE (ML Filter)                                  │
│     XGBoost predicts win probability                        │
│     < 50% → skip   ≥ 50% → proceed                         │
│                          ↓                                  │
│  5. RISK CHECK                                              │
│     Daily loss < 3.5%? Open trades < 3?                    │
│                          ↓                                  │
│  6. ENTER TRADE                                             │
│     1% risk · hard SL · TP based on setup type             │
│                          ↓                                  │
│  7. MANAGE TRADE                                            │
│     CHOCH → Giveback guard at 0.5R/15%                     │
│     LSR   → Hard TP target (Pass 17 upcoming)              │
│                          ↓                                  │
│  8. EXIT + LOG                                              │
│     Record to CSV · Update brain training data             │
└─────────────────────────────────────────────────────────────┘
```

---

## 📊 Validated Performance (16 Months)

*All results from Nov 2024 – Feb 2026 on XM demo M5 data*

| Config | Trades/wk | Win Rate | Profit Factor | $/week ($5K) |
|--------|-----------|----------|---------------|--------------|
| Baseline (all setups, all pairs) | 13.4 | 64.7% | 1.06 | +$22 |
| + Direction filters | 8.9 | 64.2% | 1.16 | +$33 |
| + FVG London Close only | 8.9 | 64.2% | 1.16 | +$33 |
| + Guard tuning (0.5R/15%) | 8.9 | 64.2% | 1.18 | +$37 |
| + Brain gate (live system) | ~5.6 | 66.8% | **1.40** | **$86** |

**At $10K funded account with 1% risk:**
- Conservative: ~$119/week
- With 1.5% risk: ~$178/week

---

## 🛡️ Risk Management

```
✅ Risk per trade      →  1% of balance ($100 on $10K account)
✅ Max risk per trade  →  1.5% for A+ setups ($150)
✅ Daily loss limit    →  3.5% ($350) — bot stops for the day
✅ Daily profit lock   →  3.0% ($300) — locks in good days
✅ Max total drawdown  →  8.0% ($800) — account protection
✅ Consecutive losses  →  Stop after 3 in a row, 2hr pause
✅ Max open trades     →  3 simultaneous positions
✅ Direction filter    →  Per-pair bias (data-proven)
✅ Brain gate          →  ML skips <50% probability signals
✅ Kill zone gate      →  London Open + London Close only
```

---

## ⚡ Quick Start

### Prerequisites
- Python 3.10+
- MetaTrader 5 with a broker account (demo recommended)

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
copy config\settings.example.json config\settings.json
```

Fill in your MT5 credentials:
```json
{
  "mt5": {
    "login":    12345678,
    "password": "your_password",
    "server":   "YourBroker-Demo"
  }
}
```

### 4. Train the brain (optional — pre-trained model included)
```bash
python 04_BRAIN/run_full_brain_pipeline.py
```

### 5. Start
```bash
python START_BOT.py
```

### 6. Check performance
```bash
python CHECK_PERFORMANCE.py
```

---

## 🔬 The 16-Pass Validation System

This bot wasn't built and shipped — it was validated. Every component was tested in isolation:

| Pass | What Was Tested | Finding |
|------|----------------|---------|
| 1–12 | Core strategy, datetime bugs, XM data | Foundation established |
| 13A | All setups across 5 pairs, 16 months | FVG/OB = dead code discovered |
| 14A | FVG + ORDER_BLOCK wired in | Both confirmed bleeders |
| 15 | Direction filters + FVG LC + guard matrix | PF 1.16 → 1.18 |
| 16 | Hard TP vs guard/trail (no guard) | LSR = hard TP, CHOCH = guard |
| Brain | ML entry classifier on unseen data | PF 1.23 → 1.40 confirmed |

---

## 🗺️ Roadmap

- [x] 16-pass backtesting validation
- [x] Direction filters per pair
- [x] Giveback guard tuning
- [x] ML brain entry classifier
- [x] Brain gate wired into live bot
- [x] $10K prop account configuration
- [ ] Pass 17 — Hybrid exit (LSR hard TP + CHOCH guard)
- [ ] Pass 18 — Macro news circuit breaker
- [ ] Monthly brain retraining pipeline
- [ ] Multiple funded account scaling

---

## 🔧 Troubleshooting

| Problem | Solution |
|---------|---------|
| `MT5 connection failed` | Check login, password, server in settings.json |
| `No trades being placed` | Confirm it's London Open or London Close hours (UTC) |
| `Brain gate blocks everything` | Check `04_BRAIN/models/entry_model.pkl` exists |
| `USDJPY 0 trades` | Brain was trained on BUY-only data — USDJPY SELL is filtered |
| `Bot stops mid-day` | Daily loss limit hit — check `07_LOGS/` for details |

---

## 📜 License

[MIT License](LICENSE) — free to use, modify, and distribute.

---

<div align="center">

**Built with precision. Validated with data. Trading ICT Smart Money Concepts.**

*16 months · 6,000+ backtested trades · XGBoost ML brain · Proven edge*

*Not financial advice. Trade responsibly.*

</div>
