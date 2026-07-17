import numpy as np


class SeasonalNaive:
    def __init__(self, lag=7):
        self.lag = lag

    def predict(self, history, horizon=28):
        """
        history: numpy array or pandas Series of demand values
        horizon: number of steps to predict
        """
        history = np.array(history)
        n = len(history)
        if n < self.lag:
            # fallback if history is too short
            return np.zeros(horizon)

        preds = []
        for i in range(horizon):
            idx = n - self.lag + (i % self.lag)
            # If the index goes beyond or we have recursive needs
            preds.append(history[idx])
        return np.array(preds)

class CrostonSBA:
    def __init__(self, alpha=0.1, method="sba"):
        """
        method: "croston" or "sba"
        """
        self.alpha = alpha
        self.method = method.lower()

    def fit_predict(self, series, horizon=28):
        """
        Fits Croston/SBA on a single series and returns a constant forecast of length 'horizon'.
        """
        series = np.array(series, dtype=float)
        n = len(series)

        # Find indices of non-zero demands
        nz_indices = np.where(series > 0)[0]

        if len(nz_indices) == 0:
            return np.zeros(horizon)

        # Initial values
        # Demand size (level)
        y = series[nz_indices[0]]
        # Inter-arrival time (interval)
        p = float(nz_indices[0] + 1)

        last_nz_idx = nz_indices[0]

        # Exponential smoothing
        for idx in nz_indices[1:]:
            q = float(idx - last_nz_idx)
            y = self.alpha * series[idx] + (1.0 - self.alpha) * y
            p = self.alpha * q + (1.0 - self.alpha) * p
            last_nz_idx = idx

        # Also smooth the last interval up to the end of the series if the last demand was long ago
        if last_nz_idx < n - 1:
            # We don't update size, only interval
            q = float(n - 1 - last_nz_idx)
            p = self.alpha * q + (1.0 - self.alpha) * p

        if p == 0:
            p = 1.0

        forecast = y / p

        if self.method == "sba":
            # Apply Syntetos-Boylan Approximation correction factor
            forecast = (1.0 - self.alpha / 2.0) * forecast

        return np.full(horizon, max(0.0, forecast))

def predict_baseline_for_df(df_test, df_train, baseline_type="seasonal_naive_7", horizon=28):
    """
    Generate baseline forecasts for a test set based on train history.
    """
    preds_dict = {}

    # Group train by item/store to get histories
    train_groups = df_train.groupby(["item_id", "store_id"])

    unique_keys = df_test[["item_id", "store_id"]].drop_duplicates()

    for _, row in unique_keys.iterrows():
        item_id = row["item_id"]
        store_id = row["store_id"]
        key = (item_id, store_id)

        if key in train_groups.groups:
            group_df = train_groups.get_group(key)
            history = group_df["demand"].values
        else:
            history = np.zeros(horizon)

        if baseline_type == "seasonal_naive_7":
            model = SeasonalNaive(lag=7)
            preds = model.predict(history, horizon=horizon)
        elif baseline_type == "seasonal_naive_28":
            model = SeasonalNaive(lag=28)
            preds = model.predict(history, horizon=horizon)
        elif baseline_type == "croston":
            model = CrostonSBA(method="croston")
            preds = model.fit_predict(history, horizon=horizon)
        elif baseline_type == "sba":
            model = CrostonSBA(method="sba")
            preds = model.fit_predict(history, horizon=horizon)
        else:
            raise ValueError(f"Unknown baseline: {baseline_type}")

        preds_dict[key] = preds

    # Map predictions back to test rows
    # Assign date rank to match forecast horizon index
    df_test = df_test.sort_values(by=["item_id", "store_id", "date"]).copy()
    df_test["horizon_idx"] = df_test.groupby(["item_id", "store_id"]).cumcount()

    def get_pred(row):
        key = (row["item_id"], row["store_id"])
        h_idx = int(row["horizon_idx"])
        if key in preds_dict and h_idx < len(preds_dict[key]):
            return preds_dict[key][h_idx]
        return 0.0

    df_test["forecast"] = df_test.apply(get_pred, axis=1)
    return df_test["forecast"].values
