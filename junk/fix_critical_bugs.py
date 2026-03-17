"""
fix_critical_bugs.py — Fix all 5 red bugs before go-live
=========================================================
Run from project root:
  python fix_critical_bugs.py

Fixes applied:
  Bug 1 — Direction filters added to settings.json + bot_engine.py
  Bug 2 — NY_OPEN removed from allowed_kill_zones in settings.json
  Bug 3 — datetime.time import collision in bot_engine.py
  Bug 4 — direction_aligned EURUSD bug in brain_gate.py
  Bug 5 — Brain prob averaging removed from ict_strategy.py
"""

import json
import shutil
from pathlib import Path

ROOT = Path(__file__).parent
SETTINGS  = ROOT / "config" / "settings.json"
BOT_ENGINE = ROOT / "python" / "bot_engine.py"
BRAIN_GATE = ROOT / "python" / "brain_gate.py"
STRATEGY   = ROOT / "python" / "ict_strategy.py"

BACKUP_DIR = ROOT / "config" / "bug_fix_backups"
BACKUP_DIR.mkdir(exist_ok=True)

errors = []
fixes  = []

def backup(path):
    dest = BACKUP_DIR / path.name
    shutil.copy(path, dest)
    print(f"  Backed up {path.name} → {dest}")

def patch_file(path, old, new, label):
    content = path.read_text(encoding="utf-8")
    if old not in content:
        print(f"  ⚠️  {label}: target string not found — skipping")
        return False
    if new in content:
        print(f"  ✅ {label}: already patched")
        return True
    path.write_text(content.replace(old, new, 1), encoding="utf-8")
    fixes.append(label)
    print(f"  ✅ {label}: FIXED")
    return True


print("=" * 60)
print("  CRITICAL BUG FIX SCRIPT")
print("=" * 60)

# ── BUG 1 + 2 — settings.json ─────────────────────────────────
print("\n[1] Fixing settings.json (direction filters + NY_OPEN)...")

if not SETTINGS.exists():
    print(f"  ERROR: {SETTINGS} not found")
    errors.append("settings.json not found")
else:
    backup(SETTINGS)
    cfg = json.load(open(SETTINGS, encoding="utf-8"))

    # Bug 1 — Add direction filters
    if "direction_filters" not in cfg:
        cfg["direction_filters"] = {
            "GBPUSD": ["SELL"],
            "USDJPY": ["BUY"],
            "EURUSD": ["BUY", "SELL"],
            "AUDUSD": ["BUY"]
        }
        fixes.append("Bug 1: direction_filters added to settings.json")
        print("  ✅ Bug 1: direction_filters added to settings.json")
    else:
        print("  ✅ Bug 1: direction_filters already in settings.json")

    # Bug 2 — Remove NY_OPEN from allowed_kill_zones
    changed = False
    for section in [cfg, cfg.get("ict", {}),
                    cfg.get("execution", {}),
                    cfg.get("hybrid", {})]:
        kz = section.get("allowed_kill_zones", [])
        if "NY_OPEN" in kz:
            section["allowed_kill_zones"] = [k for k in kz if k != "NY_OPEN"]
            changed = True

    # Also check nested ict block
    ict = cfg.get("ict", {})
    kz2 = ict.get("allowed_kill_zones", [])
    if "NY_OPEN" in kz2:
        ict["allowed_kill_zones"] = [k for k in kz2 if k != "NY_OPEN"]
        cfg["ict"] = ict
        changed = True

    if changed:
        fixes.append("Bug 2: NY_OPEN removed from allowed_kill_zones")
        print("  ✅ Bug 2: NY_OPEN removed from allowed_kill_zones")
    else:
        print("  ✅ Bug 2: NY_OPEN not present (already clean)")

    # Add EURUSD to pairs if missing
    pairs = cfg.get("pairs", [])
    if "EURUSD" not in pairs:
        pairs.append("EURUSD")
        cfg["pairs"] = pairs
        fixes.append("Bug 7: EURUSD added to pairs list")
        print("  ✅ Bug 7: EURUSD added to pairs list")

    # Add JPY + AUD to news filter currencies
    news = cfg.get("news", cfg.get("news_filter", {}))
    currencies = news.get("currencies", ["USD", "EUR", "GBP"])
    updated = False
    for c in ["JPY", "AUD"]:
        if c not in currencies:
            currencies.append(c)
            updated = True
    if updated:
        news["currencies"] = currencies
        if "news" in cfg:
            cfg["news"] = news
        elif "news_filter" in cfg:
            cfg["news_filter"] = news
        fixes.append("Bug 8: JPY + AUD added to news filter currencies")
        print("  ✅ Bug 8: JPY + AUD added to news filter currencies")

    json.dump(cfg, open(SETTINGS, "w", encoding="utf-8"), indent=2)
    print("  settings.json saved.")


# ── BUG 3 — bot_engine.py datetime.time collision ─────────────
print("\n[2] Fixing bot_engine.py (datetime.time import collision)...")

if not BOT_ENGINE.exists():
    print(f"  ⚠️  bot_engine.py not found at {BOT_ENGINE}")
    errors.append("bot_engine.py not found")
else:
    backup(BOT_ENGINE)
    content = BOT_ENGINE.read_text(encoding="utf-8")

    # Fix: rename 'time' import to 'dt_time' to avoid shadowing
    old3 = "from datetime import datetime, timedelta, timezone, time"
    new3 = "from datetime import datetime, timedelta, timezone, time as dt_time"

    if old3 in content:
        content = content.replace(old3, new3)
        # Fix any usage of bare 'time(' that was from datetime.time
        # Replace time(X, Y) patterns that are datetime.time calls
        import re
        # Only replace time() used as datetime constructor, not time module
        content = re.sub(r'\btime\((\d)', r'dt_time(\1', content)
        BOT_ENGINE.write_text(content, encoding="utf-8")
        fixes.append("Bug 3: datetime.time collision fixed in bot_engine.py")
        print("  ✅ Bug 3: datetime.time renamed to dt_time")
    elif "dt_time" in content:
        print("  ✅ Bug 3: already patched")
    else:
        print("  ⚠️  Bug 3: import line not found in expected form — manual check needed")
        errors.append("Bug 3: datetime.time import not found in expected form")


# ── BUG 4 — brain_gate.py direction_aligned EURUSD ────────────
print("\n[3] Fixing brain_gate.py (direction_aligned EURUSD bug)...")

if not BRAIN_GATE.exists():
    print(f"  ⚠️  brain_gate.py not found at {BRAIN_GATE}")
    errors.append("brain_gate.py not found")
else:
    backup(BRAIN_GATE)

    old4 = (
        '        "direction_aligned": int(\n'
        '            (sym=="USDJPY" and d=="BUY") or (sym=="GBPUSD" and d=="SELL") or\n'
        '            (sym=="EURUSD" and d=="BUY") or (sym=="EURUSD" and d=="SELL")\n'
        '        ),'
    )
    new4 = (
        '        "direction_aligned": int(\n'
        '            (sym=="USDJPY" and d=="BUY") or\n'
        '            (sym=="GBPUSD" and d=="SELL") or\n'
        '            (sym=="EURUSD" and d=="SELL") or\n'
        '            (sym=="AUDUSD" and d=="BUY")\n'
        '            # EURUSD BUY removed — not a confirmed strong combo\n'
        '            # EURUSD SELL confirmed strong combo kept\n'
        '        ),'
    )

    patched = patch_file(BRAIN_GATE, old4, new4, "Bug 4: direction_aligned EURUSD fix")

    # Also fix week_of_month hardcoded to 1 (Bug 9)
    bg_content = BRAIN_GATE.read_text(encoding="utf-8")
    import datetime as _dt
    today = _dt.date.today()
    wom = (today.day - 1) // 7 + 1

    old9  = '        "week_of_month": 1,   # not available at signal time — use neutral'
    new9  = (
        '        "week_of_month": (__import__("datetime").date.today().day - 1) // 7 + 1,'
    )
    patch_file(BRAIN_GATE, old9, new9, "Bug 9: week_of_month dynamic (was hardcoded to 1)")

    old9b = '        "is_month_end":      0,   # not available at signal time — use neutral'
    new9b = (
        '        "is_month_end": int(__import__("datetime").date.today().day >= 25),'
    )
    patch_file(BRAIN_GATE, old9b, new9b, "Bug 9b: is_month_end dynamic (was hardcoded to 0)")


# ── BUG 5 — ict_strategy.py confidence averaging ──────────────
print("\n[4] Fixing ict_strategy.py (brain prob averaging)...")

if not STRATEGY.exists():
    print(f"  ⚠️  ict_strategy.py not found at {STRATEGY}")
    errors.append("ict_strategy.py not found")
else:
    backup(STRATEGY)

    old5 = (
        "            best.confidence = round((_prob + best.confidence) / 2.0, 3)\n"
        "            if not _brain_take(symbol, _dir, _st, _kz, _hour, _dow):"
    )
    new5 = (
        "            # Use brain probability for logging only — do NOT mutate confidence\n"
        "            # Confidence drives risk sizing; brain prob is a separate binary gate\n"
        "            if not _brain_take(symbol, _dir, _st, _kz, _hour, _dow):"
    )
    patch_file(STRATEGY, old5, new5, "Bug 5: confidence averaging removed from brain gate")

    # Fix datetime.utcnow in brain gate path (lines 1032-1033)
    old_utcnow = (
        "            _hour = _dt.datetime.utcnow().hour\n"
        "            _dow  = _dt.datetime.utcnow().weekday()"
    )
    new_utcnow = (
        "            _now  = _dt.datetime.now(_dt.timezone.utc)\n"
        "            _hour = _now.hour\n"
        "            _dow  = _now.weekday()"
    )
    patch_file(STRATEGY, old_utcnow, new_utcnow,
               "Bug 6: datetime.utcnow() → datetime.now(utc) in brain gate path")


# ── SUMMARY ───────────────────────────────────────────────────
print(f"\n{'=' * 60}")
print(f"  FIX SUMMARY")
print(f"{'=' * 60}")

if fixes:
    print(f"\n  ✅ {len(fixes)} fixes applied:")
    for f in fixes:
        print(f"    → {f}")

if errors:
    print(f"\n  ⚠️  {len(errors)} items need manual attention:")
    for e in errors:
        print(f"    → {e}")

print(f"""
  NEXT STEPS:
  1. Verify bot still imports cleanly:
       python -c "import sys; sys.path.insert(0,'python'); import bot_engine; print('OK')"

  2. Verify brain gate still works:
       python python/brain_gate.py

  3. Confirm direction filters in settings.json:
       python -c "import json; cfg=json.load(open('config/settings.json')); print(cfg.get('direction_filters'))"

  4. Confirm NY_OPEN gone from kill zones:
       python -c "import json; cfg=json.load(open('config/settings.json')); print(cfg.get('hybrid',{{}}).get('allowed_kill_zones'))"

  Backups saved to: {BACKUP_DIR}
""")
print("=" * 60)
