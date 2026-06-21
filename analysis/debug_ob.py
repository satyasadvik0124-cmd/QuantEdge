import pandas as pd

df = pd.read_csv("../outputs/validated_sweeps_v2.csv")

print(df.head())
print()
print(df.columns.tolist())