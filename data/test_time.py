import MetaTrader5 as mt5
import pandas as pd
from datetime import datetime, UTC

# -------------------------------------------------
# Initialize MT5
# -------------------------------------------------

if not mt5.initialize():
    print("❌ Failed to initialize MT5")
    print(mt5.last_error())
    quit()

symbol = "EURUSD"

print("=" * 70)
print("QUANTEDGE MT5 TIMEZONE TEST")
print("=" * 70)

# -------------------------------------------------
# Current Tick Information
# -------------------------------------------------

tick = mt5.symbol_info_tick(symbol)

server_time = datetime.fromtimestamp(tick.time)
utc_time = datetime.fromtimestamp(tick.time, UTC)

print("\nCURRENT TIMES")
print("-" * 70)

print(f"Raw Tick Timestamp : {tick.time}")
print(f"Local PC Time      : {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
print(f"UTC Now            : {datetime.now(UTC).strftime('%Y-%m-%d %H:%M:%S %Z')}")
print(f"Broker Server Time : {server_time}")
print(f"Broker Time (UTC)  : {utc_time}")

# -------------------------------------------------
# Fetch Latest Candles
# -------------------------------------------------

bars = 5

rates = mt5.copy_rates_from_pos(
    symbol,
    mt5.TIMEFRAME_M15,
    0,
    bars
)

if rates is None:
    print("❌ Failed to retrieve candles")
    mt5.shutdown()
    quit()

df = pd.DataFrame(rates)

print("\n")
print("=" * 70)
print("RAW CANDLE TIMESTAMPS")
print("=" * 70)

for i in range(len(df)):

    raw = int(df.loc[i, "time"])

    broker = datetime.fromtimestamp(raw)
    utc = datetime.fromtimestamp(raw, UTC)

    print(f"\nCandle {i+1}")
    print("-" * 40)
    print(f"Raw Timestamp : {raw}")
    print(f"Broker Time   : {broker}")
    print(f"UTC Time      : {utc}")

# -------------------------------------------------
# DataFrame Conversion
# -------------------------------------------------

print("\n")
print("=" * 70)
print("DATAFRAME (BROKER TIME)")
print("=" * 70)

broker_df = df.copy()
broker_df["time"] = pd.to_datetime(
    broker_df["time"],
    unit="s"
)

print(broker_df[["time", "open", "high", "low", "close"]])

print("\n")
print("=" * 70)
print("DATAFRAME (UTC)")
print("=" * 70)

utc_df = df.copy()
utc_df["time"] = pd.to_datetime(
    utc_df["time"],
    unit="s",
    utc=True
)

print(utc_df[["time", "open", "high", "low", "close"]])

# -------------------------------------------------
# Summary
# -------------------------------------------------

print("\n")
print("=" * 70)
print("SUMMARY")
print("=" * 70)

print(f"Current Broker Time : {server_time}")
print(f"Current UTC Time    : {utc_time}")
print("\n✔ MT5 stores timestamps as Unix epoch.")
print("✔ UTC conversion is timezone-aware.")
print("✔ Broker server time should be used for QuantEdge analysis.")
print("✔ UTC can be used for exports or external integrations.")

mt5.shutdown()

print("\n")
print("=" * 70)
print("TEST COMPLETED")
print("=" * 70)