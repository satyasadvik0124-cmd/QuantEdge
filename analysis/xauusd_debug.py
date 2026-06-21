import pandas as pd

df = pd.read_csv("../outputs/market_structure_v4.csv")

print(df["label"].value_counts())