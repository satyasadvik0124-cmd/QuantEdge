import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime
from pathlib import Path
import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)
from config import PAIR

# -----------------------------
# CONFIG
# -----------------------------

MT5_TIMEFRAME = mt5.TIMEFRAME_M15

START_DATE = datetime(2024, 1, 1)
END_DATE = datetime.now()

OUTPUT_FILE = f"data/{PAIR}_M15_2Y.csv"

# -----------------------------
# MT5 CONNECTION
# -----------------------------

if not mt5.initialize():
    print("❌ MT5 initialization failed")
    quit()

print("✅ Connected to MT5")
print(f"📊 Downloading: {PAIR}")

# -----------------------------
# DOWNLOAD DATA
# -----------------------------

rates = mt5.copy_rates_range(
    PAIR,
    MT5_TIMEFRAME,
    START_DATE,
    END_DATE
)

if rates is None:
    print("❌ No data returned")
    mt5.shutdown()
    quit()

df = pd.DataFrame(rates)

df["time"] = pd.to_datetime(
    df["time"],
    unit="s"
)

# -----------------------------
# SAVE CSV
# -----------------------------

Path("data").mkdir(exist_ok=True)

df.to_csv(
    OUTPUT_FILE,
    index=False
)

print(f"✅ Downloaded {len(df):,} candles")
print(f"✅ Saved to {OUTPUT_FILE}")

print("\nDate Range:")
print(df["time"].min())
print(df["time"].max())

mt5.shutdown()