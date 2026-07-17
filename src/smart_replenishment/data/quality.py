import json
import os

import pandas as pd

from smart_replenishment.config import Config


def check_data_quality(config=None):
    if config is None:
        config = Config()

    calendar_path = os.path.join(config.raw_dir, "calendar.csv")
    sales_path = os.path.join(config.raw_dir, "sales_train_validation.csv")
    prices_path = os.path.join(config.raw_dir, "sell_prices.csv")

    # Check that files exist
    for p in [calendar_path, sales_path, prices_path]:
        if not os.path.exists(p):
            raise FileNotFoundError(f"Required raw file not found: {p}")

    print("Reading data for quality check...")
    df_cal = pd.read_csv(calendar_path)
    df_sales = pd.read_csv(sales_path)
    # Since prices can be large, read a sample or just check prices directly
    df_prices = pd.read_csv(prices_path)

    report = {}

    # 1. Duplicates check
    report["sales_duplicates"] = int(df_sales.duplicated(subset=["item_id", "store_id"]).sum())

    # 2. Missing values check
    report["calendar_nulls"] = int(df_cal.isnull().sum().sum())
    report["sales_nulls"] = int(df_sales.isnull().sum().sum())
    report["prices_nulls"] = int(df_prices.isnull().sum().sum())

    # 3. Negative sales/prices checks
    d_cols = [c for c in df_sales.columns if c.startswith("d_")]
    negative_sales_count = int((df_sales[d_cols] < 0).sum().sum())
    negative_prices_count = int((df_prices["sell_price"] < 0).sum().sum())

    report["negative_sales_count"] = negative_sales_count
    report["negative_prices_count"] = negative_prices_count

    # 4. Temporal continuity of calendar
    df_cal["date_dt"] = pd.to_datetime(df_cal["date"])
    date_diffs = df_cal["date_dt"].sort_values().diff().dropna()
    missing_days = int((date_diffs != pd.Timedelta(days=1)).sum())
    report["calendar_missing_days"] = missing_days

    # 5. Share of zero-demand entries (intermittency)
    # Check for a sample subset of rows to save memory
    sample_sales = df_sales[d_cols].sample(n=min(1000, len(df_sales)), random_state=config.seed)
    total_elements = sample_sales.size
    zero_elements = (sample_sales == 0).sum().sum()
    report["zero_sales_fraction"] = float(zero_elements / total_elements)

    # 6. Join check (basic sample verification)
    # Join sales, calendar, prices for a single item-store to check alignment
    sample_item = df_sales.iloc[0]
    item_id = sample_item["item_id"]
    store_id = sample_item["store_id"]

    # Get price data
    item_prices = df_prices[(df_prices["item_id"] == item_id) & (df_prices["store_id"] == store_id)]

    report["prices_records_for_sample_sku"] = len(item_prices)
    report["status"] = "PASSED" if (negative_sales_count == 0 and negative_prices_count == 0 and missing_days == 0) else "FAILED"

    # Write quality report
    reports_dir = "reports"
    os.makedirs(reports_dir, exist_ok=True)
    report_path = os.path.join(reports_dir, "data_quality.json")

    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(report, f, indent=4)

    print(f"Data Quality report written to {report_path}:")
    print(json.dumps(report, indent=4))

    if report["status"] == "FAILED":
        raise ValueError("Data quality check failed!")

    return report

if __name__ == "__main__":
    check_data_quality()
