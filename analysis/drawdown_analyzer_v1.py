import pandas as pd

df = pd.read_csv("../outputs/equity_curve.csv")

peak = df["equity"].iloc[0]

max_drawdown = 0

for equity in df["equity"]:

    peak = max(peak, equity)

    drawdown = peak - equity

    max_drawdown = max(max_drawdown, drawdown)

print("\n===== DRAWDOWN REPORT =====")
print(f"Maximum Drawdown: ${max_drawdown:.2f}")