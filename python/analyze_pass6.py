import pandas as pd
import numpy as np

# Load Pass 6 Results
df = pd.read_csv("run_pass6_results.csv")
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
    wr = len(win) / len(df) * 100
    avg_win = win["pnl_pips"].mean() if len(win) > 0 else 0
    loss = df[df["pnl_pips"] <= 0]
    avg_loss = loss["pnl_pips"].mean() if len(loss) > 0 else 0
    gross_prof = win["pnl_pips"].sum()
    gross_loss = abs(loss["pnl_pips"].sum())
    pf = gross_prof / gross_loss if gross_loss > 0 else float("inf")
    tot_pips = df["pnl_pips"].sum()
    exp = df["pnl_pips"].mean()
    print(f"WR: {wr:.1f}%, PF: {pf:.2f}, Total Pips: {tot_pips:.1f}, Exp: {exp:.2f}")

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
    )
    for month, row in monthly.iterrows():
        wr_m = row["wins"] / row["trades"] * 100 if row["trades"] > 0 else 0
        pf_m = row["gross_prof"] / row["gross_loss"] if row["gross_loss"] > 0 else float("inf")
        marker = "✅" if pf_m >= 1.0 else "❌"
        if row["trades"] == 0: marker = "➖"
        print(f"{month} | {row['trades']} trades | WR: {wr_m:.1f}% | Pips: {row['tot_pips']:.1f} | PF: {pf_m:.2f} | AvgW: {row['avg_w']:.1f} | AvgL: {row['avg_l']:.1f} {marker}")

    # Per Pair
    print("\nPer Pair:")
    for pair in df["symbol"].unique():
        pdf = df[df["symbol"] == pair]
        pw = pdf[pdf["pnl_pips"]>0]
        pl = pdf[pdf["pnl_pips"]<=0]
        pf_p = pw["pnl_pips"].sum() / abs(pl["pnl_pips"].sum()) if abs(pl["pnl_pips"].sum()) > 0 else float("inf")
        ptr = pdf["partial_taken"].sum() / len(pdf) * 100 if len(pdf) > 0 else 0
        print(f"{pair}: {len(pdf)} trades | WR: {len(pw)/len(pdf)*100:.1f}% | PF: {pf_p:.2f} | Pips: {pdf['pnl_pips'].sum():.1f} | AvgW: {pw['pnl_pips'].mean():.1f} | AvgL: {pl['pnl_pips'].mean():.1f} | PartialRate: {ptr:.1f}%")

    # Exit Reasons
    print("\nExits:")
    print(df["exit_reason"].value_counts(normalize=True).mul(100).round(1).astype(str) + "%")

    # KZ
    print("\nKillzones:")
    for kz in df["killzone"].unique():
        kdf = df[df["killzone"]==kz]
        print(f"{kz}: {len(kdf)} trades | PnL: {kdf['pnl_pips'].sum():.1f}")
