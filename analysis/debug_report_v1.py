import pandas as pd

choch = pd.read_csv("../outputs/choch_events.csv")

print("\nCHOCH FILE")
print(choch.head())

print("\nRows:", len(choch))
print("\nColumns:", list(choch.columns))