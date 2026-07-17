import numpy as np
import pandas as pd


def calculate_rmsse_denominators(df_train):
    """
    Calculate the scale (denominator) for each series (item_id, store_id) based on train history.
    Denominator is the mean squared difference of one-day naive forecast.
    """
    print("Calculating RMSSE scale denominators for each series...")
    # Sort to ensure difference is calculated in temporal order
    df_sorted = df_train.sort_values(by=["item_id", "store_id", "date"])

    # Calculate difference
    df_sorted["diff_sq"] = df_sorted.groupby(["item_id", "store_id"])["demand"].diff() ** 2

    # Calculate mean difference
    scale = df_sorted.groupby(["item_id", "store_id"])["diff_sq"].agg(lambda x: x.dropna().mean()).reset_index()
    scale = scale.rename(columns={"diff_sq": "scale"})

    # Protect against scale = 0 (e.g. constant series). Set to a small epsilon or 1.0.
    scale["scale"] = scale["scale"].replace(0.0, 1.0).fillna(1.0)
    return scale

def calculate_rmsse(df_eval, scale_df):
    """
    Calculate Root Mean Squared Scaled Error (RMSSE) per series.
    df_eval must contain columns: item_id, store_id, demand, forecast
    """
    df_eval = df_eval.copy()
    df_eval["err_sq"] = (df_eval["demand"] - df_eval["forecast"]) ** 2

    # Mean squared error per series
    mse_df = df_eval.groupby(["item_id", "store_id"])["err_sq"].mean().reset_index()

    # Merge scale
    merged = pd.merge(mse_df, scale_df, on=["item_id", "store_id"], how="left")
    # Fill missing scales with default 1.0
    merged["scale"] = merged["scale"].fillna(1.0)

    merged["rmsse"] = np.sqrt(merged["err_sq"] / merged["scale"])
    return merged

def calculate_wmape(y_true, y_pred):
    """
    Calculate Weighted Mean Absolute Percentage Error (WMAPE).
    """
    sum_actuals = np.sum(y_true)
    if sum_actuals == 0:
        return 0.0
    return float(np.sum(np.abs(y_true - y_pred)) / sum_actuals)

def calculate_wmape_per_series(df_eval):
    """
    Calculate WMAPE per series.
    """
    df_eval = df_eval.copy()
    df_eval["abs_err"] = np.abs(df_eval["demand"] - df_eval["forecast"])

    grouped = df_eval.groupby(["item_id", "store_id"]).agg(
        sum_abs_err=("abs_err", "sum"),
        sum_demand=("demand", "sum")
    ).reset_index()

    grouped["wmape"] = grouped["sum_abs_err"] / grouped["sum_demand"].replace(0.0, np.nan)
    # Fill nan (where demand is 0) with 0.0 or nan depending on interpretation
    grouped["wmape"] = grouped["wmape"].fillna(0.0)
    return grouped
