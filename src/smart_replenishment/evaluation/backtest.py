import os
import pickle

import numpy as np
import pandas as pd

from smart_replenishment.config import Config
from smart_replenishment.evaluation.metrics import (
    calculate_rmsse,
    calculate_rmsse_denominators,
    calculate_wmape,
)
from smart_replenishment.features.build import build_features
from smart_replenishment.models.baselines import predict_baseline_for_df
from smart_replenishment.models.catboost import predict_catboost, train_catboost
from smart_replenishment.models.lgbm import predict_lgbm, train_lgbm


def run_backtest(df_features=None, config=None):
    if config is None:
        config = Config()

    if df_features is None:
        df_features = build_features(config=config)

    # Ensure date is datetime
    df_features["date"] = pd.to_datetime(df_features["date"])

    # Identify unique dates
    unique_dates = sorted(df_features["date"].unique())
    print(f"Total unique dates in features: {len(unique_dates)}")

    # Split Test set: final 28 days
    test_days = 28
    test_dates = unique_dates[-test_days:]
    train_val_dates = unique_dates[:-test_days]

    print(f"Test dates: {test_dates[0].date()} to {test_dates[-1].date()}")
    print(f"Train/Val dates: {train_val_dates[0].date()} to {train_val_dates[-1].date()}")

    df_train_val = df_features[df_features["date"].isin(train_val_dates)].copy()
    df_test = df_features[df_features["date"].isin(test_dates)].copy()

    # Set up rolling origins
    # Folds:
    # Fold 3: validation = last 28 days of train_val
    # Fold 2: validation = next last 28 days of train_val
    # Fold 1: validation = next next last 28 days of train_val

    folds = []
    val_len = 28

    for fold_idx in range(config.val_folds):
        # Calculate indices from the end of train_val_dates
        end_idx = len(train_val_dates) - (fold_idx * val_len)
        start_idx = end_idx - val_len

        val_dates = train_val_dates[start_idx:end_idx]
        train_dates = train_val_dates[:start_idx]

        folds.append((train_dates, val_dates))

    # Features & Targets
    cat_cols = ["item_id", "store_id", "dept_id", "event_name_1", "event_type_1", "weekday"]
    exclude_cols = ["id", "cat_id", "state_id", "d", "demand", "date", "wm_yr_wk", "d_num"]
    feature_cols = [c for c in df_features.columns if c not in exclude_cols]

    print(f"Feature columns: {feature_cols}")
    print(f"Categorical columns: {cat_cols}")

    # We will evaluate 5 models:
    # 1. Seasonal Naive 7
    # 2. Seasonal Naive 28
    # 3. SBA
    # 4. LightGBM
    # 5. CatBoost

    models_to_test = ["seasonal_naive_7", "seasonal_naive_28", "sba", "lgbm", "catboost"]

    fold_metrics = {model: [] for model in models_to_test}

    for i, (train_d, val_d) in enumerate(reversed(folds)):
        fold_num = i + 1
        print(f"\n--- Running Fold {fold_num} ---")

        df_tr = df_train_val[df_train_val["date"].isin(train_d)].copy()
        df_val = df_train_val[df_train_val["date"].isin(val_d)].copy()

        print(f"Train size: {len(df_tr)}, Val size: {len(df_val)}")

        # Denominator for RMSSE calculated on Train
        scale_df = calculate_rmsse_denominators(df_tr)

        # 1. Evaluate Baselines
        for b_name in ["seasonal_naive_7", "seasonal_naive_28", "sba"]:
            print(f"Evaluating baseline: {b_name}...")
            val_preds = predict_baseline_for_df(df_val, df_tr, baseline_type=b_name, horizon=val_len)

            # Save predictions
            df_val_b = df_val.copy()
            df_val_b["forecast"] = val_preds

            # Compute metrics
            wmape = calculate_wmape(df_val_b["demand"].values, df_val_b["forecast"].values)
            rmsse_df = calculate_rmsse(df_val_b, scale_df)
            mean_rmsse = float(rmsse_df["rmsse"].mean())

            fold_metrics[b_name].append({"wmape": wmape, "rmsse": mean_rmsse})
            print(f"[{b_name}] WMAPE: {wmape:.4f}, Mean RMSSE: {mean_rmsse:.4f}")

        # 2. Evaluate GBDT models
        # LightGBM
        print("Training LightGBM...")
        lgbm_model = train_lgbm(df_tr, feature_cols, cat_cols=cat_cols)
        lgbm_preds = predict_lgbm(lgbm_model, df_val, feature_cols)

        df_val_l = df_val.copy()
        df_val_l["forecast"] = lgbm_preds
        wmape_l = calculate_wmape(df_val_l["demand"].values, df_val_l["forecast"].values)
        rmsse_df_l = calculate_rmsse(df_val_l, scale_df)
        mean_rmsse_l = float(rmsse_df_l["rmsse"].mean())

        fold_metrics["lgbm"].append({"wmape": wmape_l, "rmsse": mean_rmsse_l})
        print(f"[LightGBM] WMAPE: {wmape_l:.4f}, Mean RMSSE: {mean_rmsse_l:.4f}")

        # CatBoost
        print("Training CatBoost...")
        cb_model = train_catboost(df_tr, feature_cols, cat_cols=cat_cols)
        cb_preds = predict_catboost(cb_model, df_val, feature_cols)

        df_val_c = df_val.copy()
        df_val_c["forecast"] = cb_preds
        wmape_c = calculate_wmape(df_val_c["demand"].values, df_val_c["forecast"].values)
        rmsse_df_c = calculate_rmsse(df_val_c, scale_df)
        mean_rmsse_c = float(rmsse_df_c["rmsse"].mean())

        fold_metrics["catboost"].append({"wmape": wmape_c, "rmsse": mean_rmsse_c})
        print(f"[CatBoost] WMAPE: {wmape_c:.4f}, Mean RMSSE: {mean_rmsse_c:.4f}")

    print("\n=== Validation Backtesting Summary ===")
    for model_name, metrics in fold_metrics.items():
        avg_wmape = np.mean([m["wmape"] for m in metrics])
        avg_rmsse = np.mean([m["rmsse"] for m in metrics])
        print(f"{model_name:<20} | Average WMAPE: {avg_wmape:.4f} | Average RMSSE: {avg_rmsse:.4f}")

    # Save the backtest metrics to local files for registry
    os.makedirs("reports", exist_ok=True)
    with open("reports/val_metrics.pkl", "wb") as f:
        pickle.dump(fold_metrics, f)

    return fold_metrics, df_train_val, df_test, feature_cols, cat_cols

if __name__ == "__main__":
    run_backtest()
