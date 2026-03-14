"""
Step 5: Brain Validation.
Compares the performance with and without the ML components.
"""
import pandas as pd
import numpy as np
import joblib
import json
from pathlib import Path

def validate_brain():
    MODELS_DIR = Path("04_BRAIN") / "models"
    TRAIN_DIR = Path("04_BRAIN") / "training_data"
    REPORTS_DIR = Path("04_BRAIN") / "reports"
    
    try:
        df = pd.read_csv(TRAIN_DIR / "features.csv")
        entry_model_data = joblib.load(MODELS_DIR / "entry_model.pkl")
        entry_model = entry_model_data['model']
        features_list = entry_model_data['features']
        
        with open(MODELS_DIR / "best_parameters.json", 'r') as f:
            best_params = json.load(f)
    except Exception as e:
        print(f"Validation failed pre-requisites: {e}")
        return

    print("Validating Brain improvements...")
    
    # Pre-process for Entry Model prediction
    cat_cols = ['setup_type', 'kill_zone']
    df_encoded = pd.get_dummies(df, columns=cat_cols)
    
    # Align features
    X = pd.DataFrame(index=df.index)
    for feat in features_list:
        if feat in df_encoded.columns:
            X[feat] = df_encoded[feat].astype(int)
        else:
            X[feat] = 0
            
    # Entry Model Filter (only trades with prob > 60%)
    probs = entry_model.predict_proba(X)[:, 1]
    ml_filter = probs > 0.60
    
    baseline_pips = df['outcome_pips'].sum()
    ml_filtered_pips = df.loc[ml_filter, 'outcome_pips'].sum()
    
    baseline_win_rate = (df['outcome_binary']).mean() * 100
    ml_win_rate = (df.loc[ml_filter, 'outcome_binary']).mean() * 100
    
    # Calculate Profit Factor
    def calc_pf(series):
        wins = series[series > 0].sum()
        losses = abs(series[series < 0].sum())
        return wins / losses if losses > 0 else wins

    baseline_pf = calc_pf(df['outcome_pips'])
    ml_pf = calc_pf(df.loc[ml_filter, 'outcome_pips'])
    
    improvement = ((ml_pf - baseline_pf) / baseline_pf) * 100 if baseline_pf > 0 else 0
    
    report = (
        f"BRAIN VALIDATION REPORT\n"
        f"=======================\n\n"
        f"METRIC            | BASELINE      | WITH BRAIN (ML)\n"
        f"------------------|---------------|----------------\n"
        f"Total Trades      | {len(df):<13} | {ml_filter.sum():<13}\n"
        f"Win Rate          | {baseline_win_rate:<13.2f}% | {ml_win_rate:<13.2f}%\n"
        f"Total Pips        | {baseline_pips:<13.2f} | {ml_filtered_pips:<13.2f}\n"
        f"Profit Factor     | {baseline_pf:<13.2f} | {ml_pf:<13.2f}\n\n"
        f"CONCLUSION:\n"
        f"The Brain upgrade has resulted in a {improvement:.2f}% improvement in Profit Factor.\n"
        f"It filtered out {len(df) - ml_filter.sum()} low-probability trades.\n"
    )
    
    print("\n" + report)
    (REPORTS_DIR / "brain_validation_report.txt").write_text(report)
    print("Validation report generated.")

if __name__ == "__main__":
    validate_brain()
