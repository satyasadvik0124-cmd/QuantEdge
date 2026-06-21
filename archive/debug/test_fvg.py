import pandas as pd

fvg = pd.read_csv("../outputs/fvg_v2.csv")

print(fvg["type"].value_counts())

print("\nBullish FVGs:")
print(
    fvg[
        fvg["type"] == "BULLISH_FVG"
    ][["time", "type"]]
)