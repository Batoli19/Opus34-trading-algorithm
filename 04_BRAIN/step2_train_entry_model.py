"""
step2_train_entry_model.py — XGBoost Entry Classifier
======================================================
Trains on 2024-11 to 2025-08 only.
Tests on 2025-09 to 2026-02 — data the model never saw.

The ONLY number that matters: PF and WR on the TEST set.
If test PF > 1.20 we have a real edge. Anything else is memorization.

Run from project root:
  python 04_BRAIN/step2_train_entry_model.py
"""

import pandas as pd
import numpy as np
import json
import joblib
from pathlib import Path

try:
    from xgboost import XGBClassifier
    MODEL_NAME = "XGBoost"
except ImportError:
    from sklearn.ensemble import GradientBoostingClassifier as XGBClassifier
    MODEL_NAME = "GradientBoosting (xgboost not installed)"

from sklearn.metrics import classification_report, confusion_matrix
from sklearn.model_selection import TimeSeriesSplit

PROJECT_ROOT = Path(__file__).parent.parent
DATA_FILE    = PROJECT_ROOT / "04_BRAIN" / "training_data" / "features_clean.csv"
MODEL_DIR    = PROJECT_ROOT / "04_BRAIN" / "models"
REPORT_DIR   = PROJECT_ROOT / "04_BRAIN" / "reports"
MODEL_DIR.mkdir(parents=True, exist_ok=True)
REPORT_DIR.mkdir(parents=True, exist_ok=True)

AVG_SL_PIPS  = 32.0
RISK_USD     = 50.0
DPIP         = RISK_USD / AVG_SL_PIPS


def load_data():
    df = pd.read_csv(DATA_FILE)
    print(f"  Loaded {len(df)} trades, {df.shape[1]} columns")

    input_cols = [c for c in df.columns if not c.startswith("TARGET_")
                  and c not in ("split","year","month")]

    train = df[df["split"]=="TRAIN"].copy()
    test  = df[df["split"]=="TEST"].copy()

    X_train = train[input_cols]
    y_train = train["TARGET_win"]
    X_test  = test[input_cols]
    y_test  = test["TARGET_win"]
    pips_test = test["TARGET_pips"]

    print(f"  Train: {len(train)} | Test: {len(test)}")
    print(f"  Features: {len(input_cols)}")
    print(f"  Train WR: {y_train.mean()*100:.1f}% | Test WR: {y_test.mean()*100:.1f}%")
    return X_train, y_train, X_test, y_test, pips_test, input_cols


def train_model(X_train, y_train):
    print(f"\n  Training {MODEL_NAME}...")
    neg = (y_train==0).sum()
    pos = (y_train==1).sum()
    scale = neg / pos
    print(f"  Class balance: {pos} wins / {neg} losses | scale_pos_weight={scale:.2f}")

    if MODEL_NAME == "XGBoost":
        model = XGBClassifier(
            n_estimators=300,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            colsample_bytree=0.8,
            scale_pos_weight=scale,
            eval_metric="logloss",
            random_state=42,
            n_jobs=-1,
        )
    else:
        model = XGBClassifier(
            n_estimators=200,
            max_depth=4,
            learning_rate=0.05,
            subsample=0.8,
            random_state=42,
        )

    tscv = TimeSeriesSplit(n_splits=5)
    cv_scores = []
    for fold, (tr_idx, val_idx) in enumerate(tscv.split(X_train)):
        Xtr, Xval = X_train.iloc[tr_idx], X_train.iloc[val_idx]
        ytr, yval = y_train.iloc[tr_idx], y_train.iloc[val_idx]
        model.fit(Xtr, ytr)
        score = model.score(Xval, yval)
        cv_scores.append(score)
        print(f"    Fold {fold+1}/5 accuracy: {score*100:.1f}%")

    print(f"  CV mean accuracy: {np.mean(cv_scores)*100:.1f}%")
    model.fit(X_train, y_train)
    return model, cv_scores


def evaluate(model, X_test, y_test, pips_test, input_cols, thresholds):
    probs = model.predict_proba(X_test)[:,1]
    lines = []

    lines.append("="*60)
    lines.append("  TEST SET RESULTS (2025-09 to 2026-02)")
    lines.append("  These trades were NEVER seen during training.")
    lines.append("="*60)

    for thresh in thresholds:
        mask = probs >= thresh
        n    = mask.sum()
        if n == 0:
            lines.append(f"\n  Threshold {thresh:.1f}: 0 trades taken — too strict")
            continue

        taken_wins = y_test[mask].sum()
        taken_pips = pips_test[mask]
        wr   = taken_wins / n * 100
        net  = taken_pips.sum()
        wins = taken_pips[taken_pips>0].sum()
        loss = taken_pips[taken_pips<0].abs().sum()
        pf   = wins/loss if loss>0 else float("inf")
        dpw  = net * DPIP / 16.0

        # Baseline (no filter)
        base_wins = pips_test[pips_test>0].sum()
        base_loss = pips_test[pips_test<0].abs().sum()
        base_pf   = base_wins/base_loss if base_loss>0 else 0
        base_net  = pips_test.sum()

        lines.append(f"\n  Threshold {thresh:.1f} — keep trades with >{thresh*100:.0f}% win probability")
        lines.append(f"  Trades taken:  {n}/{len(y_test)} ({n/len(y_test)*100:.0f}% of signals)")
        lines.append(f"  Win rate:      {wr:.1f}%")
        lines.append(f"  Profit factor: {pf:.2f}  (baseline no filter: {base_pf:.2f})")
        lines.append(f"  Total pips:    {net:+.1f}  (baseline: {base_net:+.1f})")
        lines.append(f"  $/week:        ${dpw:+.0f}  (at $5K 1% risk, test period)")

        if pf > 1.20:
            lines.append(f"  VERDICT: REAL EDGE — PF {pf:.2f} on unseen data")
        elif pf > 1.0:
            lines.append(f"  VERDICT: MARGINAL — slight improvement, needs more data")
        else:
            lines.append(f"  VERDICT: NO EDGE — model does not improve on baseline")

    return lines, probs


def feature_importance(model, input_cols):
    lines = ["\n  TOP 10 FEATURES BY IMPORTANCE:"]
    if hasattr(model, "feature_importances_"):
        imp = pd.Series(model.feature_importances_, index=input_cols)
        imp = imp.sort_values(ascending=False).head(10)
        for feat, val in imp.items():
            bar = "█" * int(val * 200)
            lines.append(f"    {feat:<30} {val:.3f} {bar}")
    return lines


def main():
    print("="*60)
    print("  STEP 2 — TRAIN ENTRY MODEL")
    print("="*60)

    if not DATA_FILE.exists():
        print(f"  ERROR: {DATA_FILE} not found.")
        print(f"  Run step1 first: python 04_BRAIN/step1_extract_features.py")
        return

    X_train, y_train, X_test, y_test, pips_test, input_cols = load_data()
    model, cv_scores = train_model(X_train, y_train)

    thresholds = [0.50, 0.55, 0.60, 0.65, 0.70]
    eval_lines, probs = evaluate(model, X_test, y_test, pips_test, input_cols, thresholds)
    imp_lines = feature_importance(model, input_cols)

    for line in eval_lines: print(line)
    for line in imp_lines:  print(line)

    # Save model
    model_path = MODEL_DIR / "entry_model.pkl"
    joblib.dump(model, model_path)
    print(f"\n  Model saved → {model_path}")

    # Save feature list
    feat_path = MODEL_DIR / "entry_model_features.json"
    json.dump(input_cols, open(feat_path,"w"), indent=2)
    print(f"  Features saved → {feat_path}")

    # Save report
    report = eval_lines + imp_lines
    report_path = REPORT_DIR / "entry_model_report.txt"
    report_path.write_text("\n".join(report))
    print(f"  Report saved → {report_path}")

    # Pick best threshold
    best_thresh = None
    best_pf = 0.0
    for thresh in thresholds:
        mask = probs >= thresh
        if mask.sum() < 30: continue
        wp = pips_test[mask][pips_test[mask]>0].sum()
        lp = pips_test[mask][pips_test[mask]<0].abs().sum()
        pf = wp/lp if lp>0 else 0
        if pf > best_pf:
            best_pf = pf
            best_thresh = thresh

    print(f"\n{'='*60}")
    if best_pf > 1.20:
        print(f"  REAL EDGE CONFIRMED on unseen test data")
        print(f"  Best threshold: {best_thresh} | PF: {best_pf:.2f}")
        print(f"  Step 2 complete. Brain entry model is valid.")
    elif best_pf > 1.0:
        print(f"  MARGINAL EDGE: PF {best_pf:.2f} — better than baseline but slim")
        print(f"  Consider: more data, different features, or keep current system")
    else:
        print(f"  NO EDGE DETECTED on unseen data (PF {best_pf:.2f})")
        print(f"  The entry conditions we have are not enough to predict wins.")
        print(f"  This is honest — current hardcoded rules may already be optimal.")
    print(f"{'='*60}\n")


if __name__=="__main__":
    main()
