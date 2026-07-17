import os
from typing import Optional

import pandas as pd
from fastapi import FastAPI, HTTPException, Query

app = FastAPI(
    title="Smart Replenishment API",
    description="API for demand forecasting and inventory replenishment support",
    version="0.1.0"
)

# Paths to processed artifacts
FORECAST_PATH = "data/processed/final_test_forecast.parquet"
PRIORITY_PATH = "data/processed/priority_results.parquet"

# Global data containers to load on startup
df_forecast = None
df_priorities = None

@app.on_event("startup")
def load_data():
    global df_forecast, df_priorities

    if os.path.exists(FORECAST_PATH):
        df_forecast = pd.read_parquet(FORECAST_PATH)
        df_forecast["date"] = df_forecast["date"].astype(str)
        # Add dept_id dynamically
        df_forecast["dept_id"] = df_forecast["item_id"].apply(lambda x: "_".join(x.split("_")[:2]))
    else:
        print(f"Warning: Forecast file not found at {FORECAST_PATH}")

    if os.path.exists(PRIORITY_PATH):
        df_priorities = pd.read_parquet(PRIORITY_PATH)
        # Add dept_id dynamically
        df_priorities["dept_id"] = df_priorities["item_id"].apply(lambda x: "_".join(x.split("_")[:2]))
    else:
        print(f"Warning: Priorities file not found at {PRIORITY_PATH}")

@app.get("/health")
def health_check():
    return {
        "status": "ok",
        "champion_model": "lgbm",
        "forecast_data_loaded": df_forecast is not None,
        "priorities_data_loaded": df_priorities is not None
    }

@app.get("/forecast/{series_id}")
def get_forecast(series_id: str):
    """
    Returns the test horizon forecast and actuals for a specific series.
    series_id format: item_id_store_id (e.g. FOODS_3_120_CA_1)
    """
    if df_forecast is None:
        raise HTTPException(status_code=503, detail="Forecast data is not loaded.")

    # Parse series_id
    # Split from right on last '_' to separate store_id parts
    # M5 store_id is like 'CA_1', item_id is like 'FOODS_3_120'
    # So 'FOODS_3_120_CA_1' split right:
    # 1. split on last '_' -> 'FOODS_3_120_CA', '1'
    # To be safe, look for CA_1, CA_2, CA_3, etc.
    # Standard format has CA_1, CA_2, CA_3, CA_4, TX_1, etc.
    parts = series_id.split("_")
    if len(parts) < 3:
        raise HTTPException(status_code=400, detail="Invalid series_id format. Expected: item_id_store_id")

    store_id = f"{parts[-2]}_{parts[-1]}"
    item_id = "_".join(parts[:-2])

    subset = df_forecast[(df_forecast["item_id"] == item_id) & (df_forecast["store_id"] == store_id)]
    if subset.empty:
        raise HTTPException(status_code=404, detail=f"Series not found: item_id={item_id}, store_id={store_id}")

    records = subset.sort_values("date")[["date", "demand", "forecast", "sell_price"]].to_dict(orient="records")
    return {
        "series_id": series_id,
        "item_id": item_id,
        "store_id": store_id,
        "forecasts": records
    }

@app.get("/priorities")
def get_priorities(
    store_id: Optional[str] = Query(None, description="Filter by store_id (e.g., CA_1)"),
    dept_id: Optional[str] = Query(None, description="Filter by department (e.g., FOODS_3)"),
    limit: int = Query(10, description="Limit results to top N priorities")
):
    """
    Returns the top replenishment priorities based on simulation lost sales value.
    """
    if df_priorities is None:
        raise HTTPException(status_code=503, detail="Priorities data is not loaded.")

    subset = df_priorities.copy()

    if store_id:
        subset = subset[subset["store_id"] == store_id]

    if dept_id:
        subset = subset[subset["dept_id"] == dept_id]

    results = subset.head(limit).to_dict(orient="records")
    return {
        "filters": {
            "store_id": store_id,
            "dept_id": dept_id,
            "limit": limit
        },
        "priorities": results
    }
