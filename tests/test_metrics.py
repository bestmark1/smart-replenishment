import numpy as np
import pandas as pd

from smart_replenishment.evaluation.metrics import calculate_rmsse, calculate_wmape


def test_wmape():
    y_true = np.array([10, 20, 30])
    y_pred = np.array([12, 18, 33])

    # Absolute errors: [2, 2, 3]. Sum absolute errors = 7. Sum actuals = 60.
    # WMAPE = 7 / 60 = 0.1167
    wmape = calculate_wmape(y_true, y_pred)
    assert np.isclose(wmape, 7/60)

def test_rmsse():
    # Evaluate dataframe
    df_eval = pd.DataFrame({
        "item_id": ["item1", "item1", "item2", "item2"],
        "store_id": ["store1", "store1", "store1", "store1"],
        "demand": [2, 4, 1, 3],
        "forecast": [3, 3, 1, 2]
    })

    # Scale df
    scale_df = pd.DataFrame({
        "item_id": ["item1", "item2"],
        "store_id": ["store1", "store1"],
        "scale": [1.0, 2.0]
    })

    rmsse_df = calculate_rmsse(df_eval, scale_df)

    # For item1: errors = [1, 1], mean sq error = (1+1)/2 = 1.0. Scale = 1.0 -> RMSSE = sqrt(1.0/1.0) = 1.0
    # For item2: errors = [0, 1], mean sq error = (0+1)/2 = 0.5. Scale = 2.0 -> RMSSE = sqrt(0.5/2.0) = 0.5

    assert rmsse_df.loc[rmsse_df["item_id"] == "item1", "rmsse"].values[0] == 1.0
    assert rmsse_df.loc[rmsse_df["item_id"] == "item2", "rmsse"].values[0] == 0.5
