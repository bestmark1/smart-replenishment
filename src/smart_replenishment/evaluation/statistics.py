import json
import os
import pickle

import numpy as np
import pandas as pd
import scipy.stats as stats

from smart_replenishment.config import Config
from smart_replenishment.evaluation.metrics import (
    calculate_rmsse,
    calculate_rmsse_denominators,
    calculate_wmape,
)
from smart_replenishment.models.baselines import predict_baseline_for_df
from smart_replenishment.models.lgbm import predict_lgbm, train_lgbm


def run_statistical_comparison(df_train_val, df_test, feature_cols, cat_cols, config=None):
    if config is None:
        config = Config()

    print("\n=== Stage 4: Statistical Model Comparison (Validation Fold 3) ===")

    # We will use Fold 3 (the last validation origin) to run statistical tests.
    df_train_val["date"] = pd.to_datetime(df_train_val["date"])
    unique_dates = sorted(df_train_val["date"].unique())

    val_len = 28
    val_dates = unique_dates[-val_len:]
    train_dates = unique_dates[:-val_len]

    df_tr = df_train_val[df_train_val["date"].isin(train_dates)].copy()
    df_val = df_train_val[df_train_val["date"].isin(val_dates)].copy()

    scale_df = calculate_rmsse_denominators(df_tr)

    # 1. Best baseline (SBA)
    print("Fitting SBA baseline...")
    sba_preds = predict_baseline_for_df(df_val, df_tr, baseline_type="sba", horizon=val_len)
    df_val_sba = df_val.copy()
    df_val_sba["forecast"] = sba_preds
    rmsse_sba = calculate_rmsse(df_val_sba, scale_df)

    # 2. LightGBM
    print("Fitting LightGBM...")
    lgbm_model = train_lgbm(df_tr, feature_cols, cat_cols=cat_cols)
    lgbm_preds = predict_lgbm(lgbm_model, df_val, feature_cols)
    df_val_lgbm = df_val.copy()
    df_val_lgbm["forecast"] = lgbm_preds
    rmsse_lgbm = calculate_rmsse(df_val_lgbm, scale_df)

    # Merge errors to align per-series
    comparison_df = pd.merge(
        rmsse_sba[["item_id", "store_id", "rmsse"]].rename(columns={"rmsse": "rmsse_sba"}),
        rmsse_lgbm[["item_id", "store_id", "rmsse"]].rename(columns={"rmsse": "rmsse_lgbm"}),
        on=["item_id", "store_id"],
        how="inner"
    )

    # Calculate difference: sba - lgbm (positive means LGBM is better / has smaller error)
    comparison_df["diff"] = comparison_df["rmsse_sba"] - comparison_df["rmsse_lgbm"]

    # Wilcoxon signed-rank test
    # H0: median of differences is zero
    # H1: median of differences is non-zero
    diff_values = comparison_df["diff"].values

    # Exclude exact zeros for Wilcoxon
    non_zeros = diff_values[diff_values != 0]
    if len(non_zeros) > 0:
        wilc_stat, wilc_p = stats.wilcoxon(non_zeros, alternative="two-sided")
        # Effect size r = Z / sqrt(N)
        # For simplicity, calculate z-score from normal approximation
        # rank sum = min(W+, W-)
        n_samples = len(non_zeros)
        mean_w = n_samples * (n_samples + 1) / 4
        std_w = np.sqrt(n_samples * (n_samples + 1) * (2 * n_samples + 1) / 24)
        z_val = (wilc_stat - mean_w) / std_w
        effect_size = abs(z_val) / np.sqrt(n_samples)
    else:
        wilc_stat, wilc_p, effect_size = 0.0, 1.0, 0.0

    print("\nPaired Wilcoxon test on per-series RMSSE (SBA vs LightGBM):")
    print(f"Wilcoxon statistic: {wilc_stat:.4f}")
    print(f"p-value: {wilc_p:.6e}")
    print(f"Effect size (r): {effect_size:.4f}")

    # Block Bootstrap for 95% Confidence Interval
    # We sample series with replacement
    print("\nRunning paired bootstrap on series blocks (1000 iterations)...")
    np.random.seed(config.seed)
    bootstrap_means = []
    n_series = len(comparison_df)

    for _ in range(1000):
        boot_idx = np.random.choice(n_series, size=n_series, replace=True)
        boot_diff = diff_values[boot_idx]
        bootstrap_means.append(np.mean(boot_diff))

    ci_lower = np.percentile(bootstrap_means, 2.5)
    ci_upper = np.percentile(bootstrap_means, 97.5)
    print(f"95% Bootstrap CI for RMSSE Difference (SBA - LGBM): [{ci_lower:.4f}, {ci_upper:.4f}]")

    # 3. Final model selection
    # Choose LGBM as champion if it statistically improves over baseline, else SBA baseline
    if wilc_p < 0.05 and ci_lower > 0:
        print("\nLightGBM is statistically significantly better than SBA baseline. Selecting LightGBM.")
        champion_type = "lgbm"
    else:
        print("\nNo statistically significant improvement. Selecting SBA baseline as champion.")
        champion_type = "sba"

    # 4. Final Evaluation on Untouched Test Horizon
    print("\n=== Stage 5: Final Evaluation on Untouched Test Horizon ===")

    # Recalculate scale denominator on the full train_val set
    final_scale_df = calculate_rmsse_denominators(df_train_val)

    # Generate test forecasts
    if champion_type == "lgbm":
        print("Training final LightGBM model on full train_val set...")
        final_model = train_lgbm(df_train_val, feature_cols, cat_cols=cat_cols)

        # Save model
        os.makedirs("models", exist_ok=True)
        with open("models/champion_model.pkl", "wb") as f:
            pickle.dump(final_model, f)

        test_preds = predict_lgbm(final_model, df_test, feature_cols)
    else:
        print("Using SBA baseline for final test set...")
        test_preds = predict_baseline_for_df(df_test, df_train_val, baseline_type="sba", horizon=val_len)
        final_model = None

    # Build evaluation df
    df_eval_test = df_test.copy()
    df_eval_test["forecast"] = test_preds

    # Save final forecast to a Parquet file for API/Dashboard
    os.makedirs("data/processed", exist_ok=True)
    df_eval_test.to_parquet("data/processed/final_test_forecast.parquet")

    # Compute test metrics
    wmape_test = calculate_wmape(df_eval_test["demand"].values, df_eval_test["forecast"].values)
    rmsse_test_df = calculate_rmsse(df_eval_test, final_scale_df)
    mean_rmsse_test = float(rmsse_test_df["rmsse"].mean())

    # SBA Baseline test metrics for comparison
    test_sba_preds = predict_baseline_for_df(df_test, df_train_val, baseline_type="sba", horizon=val_len)
    df_eval_sba_test = df_test.copy()
    df_eval_sba_test["forecast"] = test_sba_preds
    wmape_sba_test = calculate_wmape(df_eval_sba_test["demand"].values, df_eval_sba_test["forecast"].values)
    rmsse_sba_test_df = calculate_rmsse(df_eval_sba_test, final_scale_df)
    mean_rmsse_sba_test = float(rmsse_sba_test_df["rmsse"].mean())

    metrics = {
        "champion_model": champion_type,
        "test_horizon": "28 days",
        "champion": {
            "wmape": wmape_test,
            "rmsse": mean_rmsse_test
        },
        "baseline_sba": {
            "wmape": wmape_sba_test,
            "rmsse": mean_rmsse_sba_test
        },
        "wilcoxon": {
            "statistic": float(wilc_stat),
            "p_value": float(wilc_p),
            "effect_size": float(effect_size)
        },
        "bootstrap_ci": {
            "lower": float(ci_lower),
            "upper": float(ci_upper)
        }
    }

    metrics_path = "reports/metrics.json"
    with open(metrics_path, "w", encoding="utf-8") as f:
        json.dump(metrics, f, indent=4)

    print(f"\nFinal Test Metrics written to {metrics_path}:")
    print(json.dumps(metrics, indent=4))

    return metrics

if __name__ == "__main__":
    import pickle
    # Let's load the data from backtest run
    with open("reports/val_metrics.pkl", "rb") as f:
        val_metrics = pickle.load(f)

    # We can run the statistics on standard call if we load data
    # (The pipeline cli will call this function with the correct arguments)
