import pandas as pd
import numpy as np

# Load Results
df = pd.read_csv("../backtest_results.csv")
df["entry_time"] = pd.to_datetime(df["entry_time"])

# Ensure needed columns exist
for col in ["pnl_pips", "rr_achieved"]:
    if col not in df.columns:
        df[col] = 0.0
for col in ["partial_taken"]:
    if col not in df.columns:
        df[col] = False
for col in ["killzone", "htf_bias", "setup_type", "direction", "exit_reason"]:
    if col not in df.columns:
        df[col] = ""

print(f"Total trades: {len(df)}")
if len(df) > 0:
    win = df[df["pnl_pips"] > 0]
    wr = len(win) / len(df)
    wr_pct = wr * 100
    avg_win = win["pnl_pips"].mean() if len(win) > 0 else 0
    loss = df[df["pnl_pips"] <= 0]
    avg_loss = loss["pnl_pips"].mean() if len(loss) > 0 else 0
    gross_prof = win["pnl_pips"].sum()
    gross_loss = abs(loss["pnl_pips"].sum())
    pf = gross_prof / gross_loss if gross_loss > 0 else float("inf")
    tot_pips = df["pnl_pips"].sum()
    exp = df["pnl_pips"].mean()
    trades_pw = len(df) / 52.0
    
    n = len(df)
    ci_lower = wr - 1.96 * np.sqrt((wr * (1 - wr)) / n)
    ci_lower_pct = ci_lower * 100
    ci_status = "above 50%" if ci_lower_pct > 50 else "below 50%"

    print(f"WR: {wr_pct:.1f}%, PF: {pf:.2f}, Total Pips: {tot_pips:.1f}, Exp: {exp:.2f}, Trades/wk: {trades_pw:.2f}")
    print(f"95% WR CI lower bound: {ci_lower_pct:.1f}% ({ci_status})")

    # Monthly
    df["month"] = df["entry_time"].dt.to_period("M")
    print("\nMonthly Breakdown:")
    monthly = df.groupby("month").agg(
        trades=("pnl_pips", "count"),
        wins=("pnl_pips", lambda x: (x > 0).sum()),
        tot_pips=("pnl_pips", "sum"),
        gross_prof=("pnl_pips", lambda x: x[x > 0].sum()),
        gross_loss=("pnl_pips", lambda x: abs(x[x <= 0].sum())),
        avg_w=("pnl_pips", lambda x: x[x > 0].mean() if (x > 0).sum() > 0 else 0),
        avg_l=("pnl_pips", lambda x: x[x <= 0].mean() if (x <= 0).sum() > 0 else 0)
    ).reindex(pd.period_range(start="2025-01", end="2025-12", freq="M"), fill_value=0)
    
    prof_months = 0
    valid_months = 0
    for month, row in monthly.iterrows():
        wr_m = row["wins"] / row["trades"] * 100 if row["trades"] > 0 else 0
        pf_m = row["gross_prof"] / row["gross_loss"] if row["gross_loss"] > 0 else float("inf")
        marker = "➖"
        if row["trades"] > 0:
            if pf_m >= 1.0: 
                marker = "✅"
            else: 
                marker = "❌"
        
        if row["trades"] >= 2:
            valid_months += 1
            if pf_m >= 1.0: prof_months += 1
                
        print(f"{month} | {row['trades']} trades | WR: {wr_m:.1f}% | Pips: {row['tot_pips']:.1f} | PF: {pf_m:.2f} | AvgW: {row['avg_w']:.1f} | AvgL: {row['avg_l']:.1f} {marker}")

    print(f"\nRegime score: {prof_months} out of {valid_months} profitable months (months with >= 2 trades).")

    # Per Pair
    print("\nPer Pair:")
    for pair in df["symbol"].unique():
        pdf = df[df["symbol"] == pair]
        pw = pdf[pdf["pnl_pips"]>0]
        pl = pdf[pdf["pnl_pips"]<=0]
        pf_p = pw["pnl_pips"].sum() / abs(pl["pnl_pips"].sum()) if abs(pl["pnl_pips"].sum()) > 0 else float("inf")
        ptr = pdf["partial_taken"].sum() / len(pdf) * 100 if len(pdf) > 0 else 0
        print(f"{pair} | {len(pdf)} trades | WR: {len(pw)/len(pdf)*100:.1f}% | PF: {pf_p:.2f} | Pips: {pdf['pnl_pips'].sum():.1f} | AvgW: {pw['pnl_pips'].mean():.1f} | AvgL: {pl['pnl_pips'].mean():.1f} | PartialRate: {ptr:.1f}%")

    # Exit Reasons
    print("\nExits:")
    v = df["exit_reason"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%"
    for reason in df["exit_reason"].unique():
        rdf = df[df["exit_reason"]==reason]
        pct = len(rdf)/len(df)*100
        print(f"{reason}: {len(rdf)} trades ({pct:.1f}%) | Avg Pips: {rdf['pnl_pips'].mean():.1f}")

    # KZ
    print("\nKillzones:")
    for kz in df["killzone"].unique():
        kdf = df[df["killzone"]==kz]
        pw = kdf[kdf["pnl_pips"]>0]
        pl = kdf[kdf["pnl_pips"]<=0]
        pf_kz = pw["pnl_pips"].sum() / abs(pl["pnl_pips"].sum()) if abs(pl["pnl_pips"].sum()) > 0 else float("inf")
        print(f"{kz}: {len(kdf)} trades | WR: {len(pw)/len(kdf)*100:.1f}% | PF: {pf_kz:.2f} | PnL: {kdf['pnl_pips'].sum():.1f}")
