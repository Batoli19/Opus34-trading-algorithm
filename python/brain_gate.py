import json, logging, numpy as np
from pathlib import Path

logger = logging.getLogger(__name__)

_HERE       = Path(__file__).parent
_PROJECT    = _HERE.parent
_MODEL_PATH = _PROJECT / "04_BRAIN" / "models" / "entry_model.pkl"
_FEATS_PATH = _PROJECT / "04_BRAIN" / "models" / "entry_model_features.json"
WIN_PROB_THRESHOLD = 0.50

_model = None
_features = None
_enabled = True

def _load():
    global _model, _features, _enabled
    if not _MODEL_PATH.exists() or not _FEATS_PATH.exists():
        logger.warning("Brain gate: model files not found. Taking all trades.")
        _enabled = False
        return
    try:
        import joblib
        _model = joblib.load(_MODEL_PATH)
        _features = json.load(open(_FEATS_PATH))
        logger.info(f"Brain gate loaded. Features: {len(_features)}, threshold: {WIN_PROB_THRESHOLD}")
    except Exception as e:
        logger.warning(f"Brain gate load failed ({e}). Taking all trades.")
        _enabled = False

def _vec(symbol, direction, setup_type, kill_zone, hour_utc, day_of_week):
    sym = str(symbol).upper().strip()
    d   = str(direction).upper().strip()
    st  = str(setup_type).upper().strip()
    kz  = str(kill_zone).upper().strip()
    h   = int(hour_utc)
    dow = int(day_of_week)
    raw = {
        "hour_utc": h, "day_of_week": dow, "week_of_month": 1,
        "is_monday": int(dow==0), "is_friday": int(dow==4), "is_month_end": 0,
        "is_lo_early": int(kz=="LONDON_OPEN" and h<=7),
        "is_lc_early": int(kz=="LONDON_CLOSE" and h==15),
        "is_usdjpy_buy":  int(sym=="USDJPY" and d=="BUY"),
        "is_usdjpy_sell": int(sym=="USDJPY" and d=="SELL"),
        "is_gbpusd_buy":  int(sym=="GBPUSD" and d=="BUY"),
        "is_gbpusd_sell": int(sym=="GBPUSD" and d=="SELL"),
        "is_eurusd_buy":  int(sym=="EURUSD" and d=="BUY"),
        "is_eurusd_sell": int(sym=="EURUSD" and d=="SELL"),
        "direction_aligned": int(
            (sym=="USDJPY" and d=="BUY") or (sym=="GBPUSD" and d=="SELL") or
            (sym=="EURUSD" and d=="BUY") or (sym=="EURUSD" and d=="SELL")
        ),
        "is_choch": int(st=="CHOCH"),
        "is_lsr":   int(st=="LIQUIDITY_SWEEP_REVERSAL"),
        "is_fvg":   int(st=="FVG_ENTRY"),
        "sym_EURUSD": int(sym=="EURUSD"), "sym_GBPUSD": int(sym=="GBPUSD"),
        "sym_USDJPY": int(sym=="USDJPY"),
        "dir_BUY": int(d=="BUY"), "dir_SELL": int(d=="SELL"),
        "setup_CHOCH": int(st=="CHOCH"),
        "setup_LIQUIDITY_SWEEP_REVERSAL": int(st=="LIQUIDITY_SWEEP_REVERSAL"),
        "setup_FVG_ENTRY": int(st=="FVG_ENTRY"),
        "kz_LONDON_OPEN": int(kz=="LONDON_OPEN"),
        "kz_LONDON_CLOSE": int(kz=="LONDON_CLOSE"),
        "kz_NY_OPEN": int(kz=="NY_OPEN"),
    }
    return np.array([raw.get(f, 0) for f in _features], dtype=float).reshape(1, -1)

def get_win_probability(symbol, direction, setup_type, kill_zone, hour_utc, day_of_week):
    global _model, _features, _enabled
    if _model is None and _enabled:
        _load()
    if not _enabled or _model is None:
        return 0.5
    try:
        return float(_model.predict_proba(_vec(symbol, direction, setup_type, kill_zone, hour_utc, day_of_week))[0][1])
    except Exception:
        return 0.5

def should_take_trade(symbol, direction, setup_type, kill_zone, hour_utc, day_of_week):
    global _model, _enabled
    if _model is None and _enabled:
        _load()
    if not _enabled or _model is None:
        return True
    try:
        prob = get_win_probability(symbol, direction, setup_type, kill_zone, hour_utc, day_of_week)
        decision = prob >= WIN_PROB_THRESHOLD
        logger.debug(f"Brain gate: {symbol} {direction} {setup_type} prob={prob:.3f} -> {'TAKE' if decision else 'SKIP'}")
        return decision
    except Exception as e:
        logger.warning(f"Brain gate error ({e}). Taking trade.")
        return True

if __name__ == "__main__":
    print("Brain gate self-test")
    print("=" * 55)
    _load()
    if not _enabled:
        print("Model not loaded — check 04_BRAIN/models/")
    else:
        print(f"Model loaded. {len(_features)} features.")
        tests = [
            ("USDJPY","BUY","CHOCH","LONDON_OPEN",8,1),
            ("USDJPY","SELL","CHOCH","LONDON_OPEN",8,1),
            ("GBPUSD","SELL","LIQUIDITY_SWEEP_REVERSAL","LONDON_CLOSE",15,3),
            ("GBPUSD","BUY","CHOCH","LONDON_OPEN",7,0),
            ("EURUSD","SELL","CHOCH","LONDON_CLOSE",16,2),
            ("EURUSD","BUY","LIQUIDITY_SWEEP_REVERSAL","LONDON_OPEN",8,4),
        ]
        print(f"\n  {'Symbol':<8} {'Dir':<5} {'Setup':<30} {'KZ':<14} {'Prob':>6} {'Decision':>8}")
        print(f"  {'-'*76}")
        for sym,d,st,kz,h,dow in tests:
            prob = get_win_probability(sym,d,st,kz,h,dow)
            take = should_take_trade(sym,d,st,kz,h,dow)
            print(f"  {sym:<8} {d:<5} {st:<30} {kz:<14} {prob:>5.1%} {'TAKE' if take else 'SKIP':>8}")
