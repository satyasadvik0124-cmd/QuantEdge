import pandas as pd

print("\n================ VALIDATED SWEEPS ================\n")
print(pd.read_csv("../outputs/validated_sweeps_v1.csv"))

print("\n================ ORDER BLOCKS ================\n")
print(pd.read_csv("../outputs/order_blocks_v1.csv"))

print("\n================ FVGs ================\n")
print(pd.read_csv("../outputs/fvg_v2.csv").head(20))