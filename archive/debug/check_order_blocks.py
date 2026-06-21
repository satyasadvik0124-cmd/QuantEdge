import pandas as pd

df = pd.read_csv("../outputs/order_blocks_v1.csv")

print("===== ORDER BLOCKS =====\n")

print(df)

print("\nTotal OBs:", len(df))

print("\nType Counts:")
print(df["type"].value_counts())