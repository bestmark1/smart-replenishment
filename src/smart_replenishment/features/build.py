import duckdb

from smart_replenishment.config import Config


def build_features(df=None, config=None):
    """
    Build features on the provided dataframe or load it from DuckDB.
    Ensures zero future data leakage.
    """
    if config is None:
        config = Config()

    if df is None:
        print("Loading data from DuckDB feature_mart...")
        con = duckdb.connect(config.db_path)
        # Select all columns from feature_mart
        df = con.execute("SELECT * FROM feature_mart").df()
        con.close()

    # Ensure sorted by group and time for correct shift/rolling operations
    print("Sorting dataframe...")
    df = df.sort_values(by=["item_id", "store_id", "date"]).reset_index(drop=True)

    print("Calculating demand lags and rolling statistics...")
    # Lags
    # lag_1 is the demand on the previous day. Shift(1) is correct because we forecast for the next 28 days recursively or directly.
    # To forecast t+1..t+28 at time t, we only have demand up to time t.
    # Note: If we do direct forecasting or rolling backtest, we shift by 1 to get yesterday's demand.
    # Let's create lags 1, 7, 14, 28.
    df["lag_1"] = df.groupby(["item_id", "store_id"])["demand"].shift(1)
    df["lag_7"] = df.groupby(["item_id", "store_id"])["demand"].shift(7)
    df["lag_14"] = df.groupby(["item_id", "store_id"])["demand"].shift(14)
    df["lag_28"] = df.groupby(["item_id", "store_id"])["demand"].shift(28)

    # Rolling features are calculated on lag_1 to prevent future leakage
    grouped_lag = df.groupby(["item_id", "store_id"])["lag_1"]

    df["rolling_mean_7"] = grouped_lag.transform(lambda x: x.rolling(7).mean())
    df["rolling_std_7"] = grouped_lag.transform(lambda x: x.rolling(7).std())
    df["rolling_mean_28"] = grouped_lag.transform(lambda x: x.rolling(28).mean())
    df["rolling_std_28"] = grouped_lag.transform(lambda x: x.rolling(28).std())

    print("Calculating price and calendar features...")
    # Price changes
    df["price_lag_1"] = df.groupby(["item_id", "store_id"])["sell_price"].shift(1)
    df["price_change_7"] = df["sell_price"] / df["price_lag_1"].groupby(df["item_id"] + df["store_id"]).shift(6) - 1
    df["price_change_7"] = df["price_change_7"].fillna(0.0)

    # Calendar events
    df["event_name_1"] = df["event_name_1"].fillna("none")
    df["event_type_1"] = df["event_type_1"].fillna("none")

    # Convert categories to category type for GBDT
    cat_cols = ["item_id", "store_id", "dept_id", "event_name_1", "event_type_1", "weekday"]
    for col in cat_cols:
        df[col] = df[col].astype("category")

    # Drop rows that have NaN in the 28-day rolling features
    print("Dropping initial rows with NaN features...")
    # Since we need lag_28 and rolling_28, the first 28 days of each series will have NaNs.
    # Let's drop them to clean up the dataset.
    df = df.dropna(subset=["rolling_mean_28"]).reset_index(drop=True)

    return df

if __name__ == "__main__":
    df_features = build_features()
    print(f"Features created. Shape: {df_features.shape}")
