import pandas as pd
import sys
import os


# =========================================================
# PROJECT PATH
# =========================================================

sys.path.append(
    os.path.dirname(
        os.path.dirname(
            os.path.abspath(__file__)
        )
    )
)


# =========================================================
# CONFIG
# =========================================================

from config import PAIR


# =========================================================
# HISTORICAL DATA
# =========================================================
#
# IMPORTANT:
# Explicitly use the 5-year dataset.
#
# Example:
# XAUUSD_M15_5Y.csv
#
# =========================================================

HISTORICAL_FILE = (
    f"../data/{PAIR}_M15_5Y.csv"
)


# =========================================================
# LOAD DATA
# =========================================================

print("\n")
print("=" * 60)
print("BOS V4")
print("=" * 60)

print(
    f"Loading file:\n{HISTORICAL_FILE}"
)


df = pd.read_csv(
    HISTORICAL_FILE
)


# =========================================================
# TIME CONVERSION
# =========================================================

df["time"] = pd.to_datetime(
    df["time"]
)


# =========================================================
# SORT DATA
# =========================================================

df = (
    df
    .sort_values(
        "time"
    )
    .reset_index(
        drop=True
    )
)


# =========================================================
# INPUT DATA REPORT
# =========================================================

print("\n")
print("=" * 60)
print("BOS INPUT DATA")
print("=" * 60)

print(
    f"Rows  : {len(df):,}"
)

print(
    f"Start : {df['time'].min()}"
)

print(
    f"End   : {df['time'].max()}"
)

print("\nData by year:")

print(
    df["time"]
    .dt.year
    .value_counts()
    .sort_index()
)


# =========================================================
# CHECK REQUIRED COLUMNS
# =========================================================

required_columns = [
    "time",
    "open",
    "high",
    "low",
    "close"
]


missing_columns = [
    col
    for col in required_columns
    if col not in df.columns
]


if missing_columns:

    raise ValueError(
        "\nMissing required columns:\n"
        + str(missing_columns)
    )


# =========================================================
# XAUUSD DISTANCE FILTER
# =========================================================

if PAIR == "XAUUSD":

    MIN_DISTANCE = 5.0

else:

    MIN_DISTANCE = 0.0010


print(
    f"\nMinimum swing distance: "
    f"{MIN_DISTANCE}"
)


# =========================================================
# SWING DETECTOR V3
# =========================================================

print("\n")
print("=" * 60)
print("SWING DETECTOR V3")
print("=" * 60)


swings = []


for i in range(
    3,
    len(df) - 3
):

    # =====================================================
    # SWING HIGH
    # =====================================================

    if (
        df["high"].iloc[i]
        > df["high"].iloc[i - 1]

        and

        df["high"].iloc[i]
        > df["high"].iloc[i - 2]

        and

        df["high"].iloc[i]
        > df["high"].iloc[i - 3]

        and

        df["high"].iloc[i]
        > df["high"].iloc[i + 1]

        and

        df["high"].iloc[i]
        > df["high"].iloc[i + 2]

        and

        df["high"].iloc[i]
        > df["high"].iloc[i + 3]
    ):

        swings.append({

            "index": i,

            "time":
                df["time"].iloc[i],

            "price":
                df["high"].iloc[i],

            "type":
                "SH"
        })


    # =====================================================
    # SWING LOW
    # =====================================================

    if (
        df["low"].iloc[i]
        < df["low"].iloc[i - 1]

        and

        df["low"].iloc[i]
        < df["low"].iloc[i - 2]

        and

        df["low"].iloc[i]
        < df["low"].iloc[i - 3]

        and

        df["low"].iloc[i]
        < df["low"].iloc[i + 1]

        and

        df["low"].iloc[i]
        < df["low"].iloc[i + 2]

        and

        df["low"].iloc[i]
        < df["low"].iloc[i + 3]
    ):

        swings.append({

            "index": i,

            "time":
                df["time"].iloc[i],

            "price":
                df["low"].iloc[i],

            "type":
                "SL"
        })


print(
    f"\nRaw swings: {len(swings):,}"
)


# =========================================================
# SORT SWINGS
# =========================================================

swings.sort(
    key=lambda x: x["index"]
)


# =========================================================
# CLEAN SAME-TYPE SWINGS
# =========================================================

cleaned = []


for swing in swings:

    if not cleaned:

        cleaned.append(
            swing
        )

        continue


    last = cleaned[-1]


    if (
        swing["type"]
        == last["type"]
    ):

        # -----------------------------------------------
        # Swing High
        # -----------------------------------------------

        if swing["type"] == "SH":

            if (
                swing["price"]
                > last["price"]
            ):

                cleaned[-1] = swing


        # -----------------------------------------------
        # Swing Low
        # -----------------------------------------------

        else:

            if (
                swing["price"]
                < last["price"]
            ):

                cleaned[-1] = swing


    else:

        cleaned.append(
            swing
        )


print(
    f"After same-type cleaning: "
    f"{len(cleaned):,}"
)


# =========================================================
# DISTANCE FILTER
# =========================================================

filtered = []


for swing in cleaned:

    if not filtered:

        filtered.append(
            swing
        )

        continue


    last = filtered[-1]


    distance = abs(
        swing["price"]
        - last["price"]
    )


    if (
        distance
        >= MIN_DISTANCE
    ):

        filtered.append(
            swing
        )


print(
    f"After distance filter: "
    f"{len(filtered):,}"
)


# =========================================================
# LABEL MARKET STRUCTURE
# =========================================================

last_high = None
last_low = None

structure = []


for swing in filtered:

    # =====================================================
    # HIGH
    # =====================================================

    if swing["type"] == "SH":

        if last_high is None:

            label = "SH"

        elif (
            swing["price"]
            > last_high
        ):

            label = "HH"

        else:

            label = "LH"


        last_high = swing["price"]


    # =====================================================
    # LOW
    # =====================================================

    else:

        if last_low is None:

            label = "SL"

        elif (
            swing["price"]
            > last_low
        ):

            label = "HL"

        else:

            label = "LL"


        last_low = swing["price"]


    swing["label"] = label

    structure.append(
        swing
    )


# =========================================================
# STRUCTURE REPORT
# =========================================================

structure_df = pd.DataFrame(
    structure
)


if not structure_df.empty:

    structure_df["time"] = pd.to_datetime(
        structure_df["time"]
    )


print("\n")
print("=" * 60)
print("STRUCTURE DATE CHECK")
print("=" * 60)


if structure_df.empty:

    print(
        "WARNING: No structure generated."
    )

else:

    print(
        f"Structure rows : "
        f"{len(structure_df):,}"
    )

    print(
        f"Structure start: "
        f"{structure_df['time'].min()}"
    )

    print(
        f"Structure end  : "
        f"{structure_df['time'].max()}"
    )


    print(
        "\nStructure by year:"
    )


    structure_years = (
        structure_df
        .groupby(
            structure_df["time"].dt.year
        )["label"]
        .value_counts()
    )


    print(
        structure_years
    )


# =========================================================
# STRUCTURE COUNTS
# =========================================================

print("\n")
print("=" * 60)
print("STRUCTURE LABEL COUNTS")
print("=" * 60)

if not structure_df.empty:

    print(
        structure_df["label"]
        .value_counts()
    )


# =========================================================
# BOS V4
# =========================================================

print("\n")
print("=" * 60)
print("BOS V4")
print("=" * 60)


bos_events = []

bullish_bos_count = 0

bearish_bos_count = 0


# =========================================================
# PROCESS STRUCTURE
# =========================================================

for swing in structure:

    # =====================================================
    # BULLISH BOS
    # =====================================================

    if swing["label"] == "HH":

        level = swing["price"]


        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if (
                df["close"].iloc[j]
                > level
            ):

                bos_events.append({

                    "time":
                        df["time"].iloc[j],

                    "type":
                        "Bullish BOS",

                    "level":
                        level
                })


                bullish_bos_count += 1

                break


    # =====================================================
    # BEARISH BOS
    # =====================================================

    elif swing["label"] == "LL":

        level = swing["price"]


        for j in range(
            swing["index"] + 1,
            len(df)
        ):

            if (
                df["close"].iloc[j]
                < level
            ):

                bos_events.append({

                    "time":
                        df["time"].iloc[j],

                    "type":
                        "Bearish BOS",

                    "level":
                        level
                })


                bearish_bos_count += 1

                break


# =========================================================
# BOS DATAFRAME
# =========================================================

bos_df = pd.DataFrame(
    bos_events
)


# =========================================================
# BOS DATE CHECK
# =========================================================

print("\n")
print("=" * 60)
print("BOS DATE CHECK")
print("=" * 60)


if bos_df.empty:

    print(
        "WARNING: No BOS events generated."
    )

else:

    bos_df["time"] = pd.to_datetime(
        bos_df["time"]
    )


    print(
        f"BOS rows  : "
        f"{len(bos_df):,}"
    )

    print(
        f"BOS start : "
        f"{bos_df['time'].min()}"
    )

    print(
        f"BOS end   : "
        f"{bos_df['time'].max()}"
    )


    print(
        "\nBOS by year:"
    )


    print(
        bos_df["time"]
        .dt.year
        .value_counts()
        .sort_index()
    )


# =========================================================
# SAVE BOS
# =========================================================

OUTPUT_FILE = (
    "../outputs/bos_events_v4.csv"
)


bos_df.to_csv(
    OUTPUT_FILE,
    index=False
)


# =========================================================
# FINAL REPORT
# =========================================================

print("\n")
print("=" * 60)
print("BOS REPORT")
print("=" * 60)


print(
    f"Input Candles      : "
    f"{len(df):,}"
)


print(
    f"Filtered Structure : "
    f"{len(structure):,}"
)


print(
    f"Bullish BOS        : "
    f"{bullish_bos_count:,}"
)


print(
    f"Bearish BOS        : "
    f"{bearish_bos_count:,}"
)


total_bos = (
    bullish_bos_count
    + bearish_bos_count
)


print(
    f"Total BOS          : "
    f"{total_bos:,}"
)


if len(structure) > 0:

    print(
        f"BOS Ratio          : "
        f"{(total_bos / len(structure)) * 100:.2f}%"
    )

else:

    print(
        "BOS Ratio          : 0.00%"
    )


print(
    f"\nSaved: {OUTPUT_FILE}"
)


print("\n")
print("=" * 60)
print("BOS V4 COMPLETE")
print("=" * 60)