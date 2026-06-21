from pathlib import Path
import pandas as pd

ROOT = Path(__file__).parent.parent
DATA_FILE = ROOT / "data" / "EURUSD_M15_2Y.csv"

df = pd.read_csv(DATA_FILE)

print("Rows:", len(df))

print("\nMissing Values:")
print(df.isnull().sum())

print("\nDuplicate Rows:")
print(df.duplicated().sum())

print("\nDate Range:")
print(df["time"].min())
print(df["time"].max())