import os

import duckdb
import pandas as pd

from smart_replenishment.config import Config


def create_feature_mart(config=None):
    if config is None:
        config = Config()

    os.makedirs(os.path.dirname(config.db_path), exist_ok=True)

    calendar_path = os.path.join(config.raw_dir, "calendar.csv")
    sales_path = os.path.join(config.raw_dir, "sales_train_validation.csv")
    prices_path = os.path.join(config.raw_dir, "sell_prices.csv")

    # 1. Load data
    print("Loading datasets for feature mart...")
    df_sales = pd.read_csv(sales_path)
    df_cal = pd.read_csv(calendar_path)
    df_prices = pd.read_csv(prices_path)

    # 2. Filter scope
    print(f"Filtering sales to state={config.state_id} and category={config.cat_id}...")
    df_sales_filtered = df_sales[
        (df_sales["state_id"] == config.state_id) &
        (df_sales["cat_id"] == config.cat_id)
    ].copy()

    print(f"Number of series in scope: {len(df_sales_filtered)}")

    # 3. Melt to long format
    print("Melting wide sales dataframe to long format...")
    d_cols = [c for c in df_sales_filtered.columns if c.startswith("d_")]

    df_long = pd.melt(
        df_sales_filtered,
        id_vars=["id", "item_id", "dept_id", "cat_id", "store_id", "state_id"],
        value_vars=d_cols,
        var_name="d",
        value_name="demand"
    )

    # 4. Clean keys for joining
    # Extract numeric part of 'd' (e.g., 'd_1' -> 1)
    df_long["d_num"] = df_long["d"].str.replace("d_", "").astype(int)
    df_cal["d_num"] = df_cal["d"].str.replace("d_", "").astype(int)

    # 5. Join calendar features
    print("Joining calendar features...")
    snap_col = f"snap_{config.state_id}"
    cal_cols = [
        "d_num", "date", "wm_yr_wk", "weekday", "wday", "month", "year",
        "event_name_1", "event_type_1", snap_col
    ]
    df_cal_sub = df_cal[cal_cols].rename(columns={snap_col: "snap"})

    df_mart = pd.merge(df_long, df_cal_sub, on="d_num", how="left")

    # 6. Join prices
    print("Joining price features...")
    # Clean price records to only keep records in the filtered scope stores/items to save memory
    in_scope_items = set(df_sales_filtered["item_id"])
    in_scope_stores = set(df_sales_filtered["store_id"])
    df_prices_filtered = df_prices[
        df_prices["item_id"].isin(in_scope_items) &
        df_prices["store_id"].isin(in_scope_stores)
    ]

    df_mart = pd.merge(
        df_mart,
        df_prices_filtered,
        on=["store_id", "item_id", "wm_yr_wk"],
        how="left"
    )

    # Set default price to 0 if missing (some products might not be active in early weeks)
    df_mart["sell_price"] = df_mart["sell_price"].fillna(0.0)

    # 7. Write to DuckDB
    print(f"Writing analytic mart to DuckDB at {config.db_path}...")
    con = duckdb.connect(config.db_path)

    # Drop table if exists to support clean re-runs
    con.execute("DROP TABLE IF EXISTS feature_mart")

    # Write dataframe to table
    con.register("df_mart_temp", df_mart)
    con.execute("CREATE TABLE feature_mart AS SELECT * FROM df_mart_temp")

    # Create indexes for fast queries
    con.execute("CREATE INDEX idx_mart_keys ON feature_mart (item_id, store_id, date)")

    con.close()
    print("Analytic mart successfully created in DuckDB.")

if __name__ == "__main__":
    create_feature_mart()
