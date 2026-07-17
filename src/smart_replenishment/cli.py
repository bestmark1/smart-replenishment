import argparse
import os
import pickle
import sys

import pandas as pd

from smart_replenishment.config import Config
from smart_replenishment.data.ingest import download_and_extract
from smart_replenishment.data.mart import create_feature_mart
from smart_replenishment.data.quality import check_data_quality
from smart_replenishment.evaluation.backtest import run_backtest
from smart_replenishment.evaluation.statistics import run_statistical_comparison
from smart_replenishment.features.build import build_features
from smart_replenishment.simulation.inventory import (
    calculate_replenishment_priorities,
    simulate_inventory_policy,
)


def main():
    parser = argparse.ArgumentParser(
        description="Smart Replenishment: Demand forecasting and inventory replenishment support system"
    )

    subparsers = parser.add_subparsers(dest="command", help="Subcommand to run")

    # Data commands
    subparsers.add_parser("download", help="Download and extract M5 dataset")
    subparsers.add_parser("quality", help="Run data quality contract audits")
    subparsers.add_parser("mart", help="Build analytic feature mart in DuckDB")
    subparsers.add_parser("pipeline", help="Run download, quality check, and feature mart sequentially")

    # Modeling commands
    subparsers.add_parser("train", help="Run 3-fold rolling-origin backtesting and model training")
    subparsers.add_parser("evaluate", help="Run statistical significance checks and final test horizon evaluation")

    # Simulation commands
    subparsers.add_parser("simulate", help="Run daily inventory replenishment simulation on test horizon forecasts")

    # Run all
    subparsers.add_parser("run-all", help="Run the entire pipeline from end-to-end")

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        sys.exit(1)

    config = Config()

    try:
        if args.command == "download":
            download_and_extract(config)
        elif args.command == "quality":
            check_data_quality(config)
        elif args.command == "mart":
            create_feature_mart(config)
        elif args.command == "pipeline":
            print("--- Step 1: Downloading M5 Dataset ---")
            download_and_extract(config)
            print("\n--- Step 2: Running Data Quality Audit ---")
            check_data_quality(config)
            print("\n--- Step 3: Building DuckDB Feature Mart ---")
            create_feature_mart(config)
            print("\nPipeline data preparation complete.")

        elif args.command == "train":
            print("--- Running Backtesting and Model Training ---")
            df_features = build_features(config=config)
            fold_metrics, df_train_val, df_test, feature_cols, cat_cols = run_backtest(df_features, config)

            # Save temporary files for evaluate step
            os.makedirs("data/processed", exist_ok=True)
            df_train_val.to_parquet("data/processed/df_train_val.parquet")
            df_test.to_parquet("data/processed/df_test.parquet")
            with open("data/processed/features_cols.pkl", "wb") as f:
                pickle.dump((feature_cols, cat_cols), f)
            print("\nTraining and backtesting completed successfully.")

        elif args.command == "evaluate":
            print("--- Running Statistical Comparison and Test Evaluation ---")
            # Load temporary files
            if (not os.path.exists("data/processed/df_train_val.parquet") or
                not os.path.exists("data/processed/df_test.parquet")):
                print("Error: Train/Test files not found. Please run 'train' command first.", file=sys.stderr)
                sys.exit(1)

            df_train_val = pd.read_parquet("data/processed/df_train_val.parquet")
            df_test = pd.read_parquet("data/processed/df_test.parquet")
            with open("data/processed/features_cols.pkl", "rb") as f:
                feature_cols, cat_cols = pickle.load(f)

            run_statistical_comparison(df_train_val, df_test, feature_cols, cat_cols, config)
            print("\nStatistical comparison and test evaluation completed successfully.")

        elif args.command == "simulate":
            print("--- Running Inventory Replenishment Simulation ---")
            if not os.path.exists("data/processed/final_test_forecast.parquet"):
                print("Error: Final test forecast file not found. Please run 'evaluate' command first.", file=sys.stderr)
                sys.exit(1)

            df_forecast = pd.read_parquet("data/processed/final_test_forecast.parquet")
            df_sim = simulate_inventory_policy(df_forecast, config)

            # Save simulation results
            df_sim.to_parquet("data/processed/sim_results.parquet")

            # Priorities
            df_priorities = calculate_replenishment_priorities(df_sim)
            df_priorities.to_parquet("data/processed/priority_results.parquet")

            print("\nTop 5 replenishment priorities:")
            print(df_priorities.head())
            print("\nInventory replenishment simulation completed successfully.")

        elif args.command == "run-all":
            print("=== STARTING FULL PIPELINE ===")
            download_and_extract(config)
            check_data_quality(config)
            create_feature_mart(config)

            df_features = build_features(config=config)
            fold_metrics, df_train_val, df_test, feature_cols, cat_cols = run_backtest(df_features, config)

            run_statistical_comparison(df_train_val, df_test, feature_cols, cat_cols, config)

            df_forecast = pd.read_parquet("data/processed/final_test_forecast.parquet")
            df_sim = simulate_inventory_policy(df_forecast, config)
            df_sim.to_parquet("data/processed/sim_results.parquet")

            df_priorities = calculate_replenishment_priorities(df_sim)
            df_priorities.to_parquet("data/processed/priority_results.parquet")
            print("=== FULL PIPELINE RUN COMPLETED SUCCESSFULLY ===")

    except Exception as e:
        print(f"Error executing command '{args.command}': {e}", file=sys.stderr)
        import traceback
        traceback.print_exc()
        sys.exit(1)

if __name__ == "__main__":
    main()
