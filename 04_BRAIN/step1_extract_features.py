import pandas as pd
from pathlib import Path

PROJECT_ROOT = Path(__file__).parent.parent
OUTPUT_DIR   = PROJECT_ROOT / "04_BRAIN" / "training_data"
OUTPUT_CSV   = OUTPUT_DIR / "features_clean.csv"
SUMMARY_FILE = OUTPUT_DIR / "feature_summary_clean.txt"
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

SOURCE_FILES = ["pass14a_A.csv", "pass15_C_dir_fvg_lc.csv"]
FORBIDDEN    = ["exit_reason","exit_time","partial_taken","peak_r",
                "sniper_passed","sniper_skip_reason","htf_bias"]

def find(name):
    if (PROJECT_ROOT / name).exists(): return PROJECT_ROOT / name
    hits = list(PROJECT_ROOT.rglob(name))
    return hits[0] if hits else None

def main():
    print("="*60)
    print("  STEP 1 — CLEAN FEATURE EXTRACTION v2")
    print("="*60)
    frames = []
    for name in SOURCE_FILES:
        p = find(name)
        if p is None: print(f"  MISSING: {name}"); continue
        df = pd.read_csv(p); df["src"] = name
        frames.append(df); print(f"  Loaded {name}: {len(df)} trades")
    if not frames: raise FileNotFoundError("No source files found")
    raw = pd.concat(frames, ignore_index=True)
    print(f"  Total: {len(raw)} trades\n")

    leaked = [c for c in FORBIDDEN if c in raw.columns]
    if leaked:
        print("  Dropping leaked columns:"); [print(f"    x {c}") for c in leaked]
        raw = raw.drop(columns=leaked)

    times = pd.to_datetime(raw["entry_time"], utc=True, errors="coerce")
    print(f"  Date range: {times.min().date()} to {times.max().date()}")

    out = pd.DataFrame()
    out["hour_utc"]      = times.dt.hour
    out["day_of_week"]   = times.dt.dayofweek
    out["week_of_month"] = (times.dt.day - 1) // 7 + 1
    out["month"]         = times.dt.month
    out["year"]          = times.dt.year
    out["is_monday"]     = (out["day_of_week"]==0).astype(int)
    out["is_friday"]     = (out["day_of_week"]==4).astype(int)
    out["is_month_end"]  = (times.dt.day>=25).astype(int)

    sym = raw["symbol"].str.upper()
    d   = raw["direction"].str.upper()
    kz  = raw["kill_zone"].str.upper()
    st  = raw["setup_type"].str.upper()

    out["is_usdjpy_buy"]     = ((sym=="USDJPY")&(d=="BUY")).astype(int)
    out["is_usdjpy_sell"]    = ((sym=="USDJPY")&(d=="SELL")).astype(int)
    out["is_gbpusd_buy"]     = ((sym=="GBPUSD")&(d=="BUY")).astype(int)
    out["is_gbpusd_sell"]    = ((sym=="GBPUSD")&(d=="SELL")).astype(int)
    out["is_eurusd_buy"]     = ((sym=="EURUSD")&(d=="BUY")).astype(int)
    out["is_eurusd_sell"]    = ((sym=="EURUSD")&(d=="SELL")).astype(int)
    out["direction_aligned"] = (out["is_usdjpy_buy"]|out["is_gbpusd_sell"]|
                                out["is_eurusd_buy"]|out["is_eurusd_sell"]).astype(int)
    out["is_choch"]          = (st=="CHOCH").astype(int)
    out["is_lsr"]            = (st=="LIQUIDITY_SWEEP_REVERSAL").astype(int)
    out["is_lo_early"]       = ((kz=="LONDON_OPEN")&(out["hour_utc"]<=7)).astype(int)
    out["is_lc_early"]       = ((kz=="LONDON_CLOSE")&(out["hour_utc"]==15)).astype(int)

    for col, pre, vals in [
        (sym,"sym",["EURUSD","GBPUSD","USDJPY"]),
        (d,"dir",["BUY","SELL"]),
        (st,"setup",["CHOCH","LIQUIDITY_SWEEP_REVERSAL","FVG_ENTRY"]),
        (kz,"kz",["LONDON_OPEN","LONDON_CLOSE","NY_OPEN"]),
    ]:
        for v in vals:
            out[f"{pre}_{v}"] = (col==v).astype(int)

    pnl = pd.to_numeric(raw["pnl_pips"], errors="coerce").fillna(0)
    out["TARGET_win"]  = (pnl>0).astype(int)
    out["TARGET_pips"] = pnl.round(2)
    out["year"]        = out["year"]
    out["month"]       = out["month"]

    ym = out["year"]*100 + out["month"]
    train = ym <= 202508
    test  = ym >= 202509

    print(f"\n  TRAIN: {train.sum()} trades | WR {out.loc[train,'TARGET_win'].mean()*100:.1f}%")
    if test.sum()>0:
        print(f"  TEST:  {test.sum()} trades | WR {out.loc[test,'TARGET_win'].mean()*100:.1f}%")
    else:
        print(f"  TEST:  0 trades")
        print(f"  Year/month distribution:")
        print(out.groupby(["year","month"]).size().to_string())

    out["split"] = "TRAIN"
    out.loc[test,"split"]  = "TEST"

    out.to_csv(OUTPUT_CSV, index=False)
    print(f"\n  Saved {OUTPUT_CSV}")
    print(f"  Shape: {out.shape}")
    input_cols = [c for c in out.columns if not c.startswith("TARGET_")
                  and c not in ("split","year","month")]
    print(f"  Input features: {len(input_cols)}")
    print("="*60)
    if test.sum()>=50:
        print("  Step 1 DONE. Run step2 next.")
    else:
        print("  Paste this output — test set needs debugging.")
    print("="*60)

if __name__=="__main__":
    main()
