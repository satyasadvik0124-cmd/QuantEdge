import pandas as pd

STARTING_BALANCE = 10000
RISK_PER_TRADE = 100

df = pd.read_csv("../outputs/backtest_results_v1.csv")

equity = STARTING_BALANCE

curve = []

for i, row in df.iterrows():

    equity += row["rr"] * RISK_PER_TRADE

    curve.append({
        "trade_no": i + 1,
        "equity": round(equity, 2)
    })

curve_df = pd.DataFrame(curve)

curve_df.to_csv(
    "../outputs/equity_curve.csv",
    index=False
)

print("✅ Equity curve generated")
print(curve_df.tail())