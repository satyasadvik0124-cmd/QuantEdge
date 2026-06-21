import sys
import os

sys.path.append(
    os.path.dirname(
        os.path.dirname(__file__)
    )
)

from config import PAIR, TIMEFRAME

print(PAIR)
print(TIMEFRAME)