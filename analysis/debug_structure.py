import pandas as pd

df = pd.read_csv("../outputs/market_structure_v4.csv")

print("\n===== LABEL COUNTS =====\n")
print(df["label"].value_counts())