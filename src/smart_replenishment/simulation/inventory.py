import numpy as np
import pandas as pd

from smart_replenishment.config import Config


def simulate_inventory_policy(df_forecast, config=None):
    """
    Runs a daily inventory simulation on the forecast/actual test horizon dataset.
    df_forecast: pandas DataFrame with columns [date, item_id, store_id, demand, forecast, sell_price]
    """
    if config is None:
        config = Config()

    print("Running inventory replenishment simulation...")

    # Ensure sorted by time
    df_eval = df_forecast.sort_values(by=["item_id", "store_id", "date"]).copy()

    lead_time = config.lead_time
    review_period = config.review_period
    holding_cost_rate = config.holding_cost
    stockout_penalty_rate = config.stockout_penalty
    initial_stock = config.initial_stock

    # Group by series
    groups = df_eval.groupby(["item_id", "store_id"])

    sim_records = []

    for (item_id, store_id), group_df in groups:
        dates = group_df["date"].values
        demands = group_df["demand"].values
        forecasts = group_df["forecast"].values
        prices = group_df["sell_price"].values

        n_days = len(group_df)

        # Simulation arrays
        stock = np.zeros(n_days)
        orders = np.zeros(n_days)
        receipts = np.zeros(n_days + lead_time + 1)
        lost_demand = np.zeros(n_days)
        holding_costs = np.zeros(n_days)
        stockout_penalties = np.zeros(n_days)

        # Initial state
        current_stock = initial_stock

        for t in range(n_days):
            # 1. Receive order at start of day
            current_stock += receipts[t]
            stock[t] = current_stock

            # 2. Daily review and ordering decision
            # Inventory position IP = stock + OnOrder
            # OnOrder is sum of orders placed but not yet received
            current_on_order = sum(receipts[t+1:t+lead_time+1])
            ip = current_stock + current_on_order

            # Calculate target stock level S based on forecasted demand during (lead_time + review_period)
            # Lead time is 7, review period is 1, so we look at 8 days of forecast
            forecast_horizon = lead_time + review_period
            future_forecast = forecasts[t : min(t + forecast_horizon, n_days)]

            # If we run near the end, fill remaining forecast with average
            if len(future_forecast) < forecast_horizon:
                avg_f = np.mean(forecasts) if len(forecasts) > 0 else 0.0
                needed = forecast_horizon - len(future_forecast)
                future_forecast = np.append(future_forecast, np.full(needed, avg_f))

            # Base stock target S = mean forecast + safety stock buffer (e.g. 1.0 standard deviation of forecast)
            forecast_sum = np.sum(future_forecast)
            safety_stock = 0.5 * forecast_sum  # 50% safety stock buffer
            S = forecast_sum + safety_stock

            # Order amount
            order_qty = max(0.0, S - ip)
            orders[t] = order_qty

            # Schedule receipt in t + lead_time
            receipts[t + lead_time] = order_qty

            # 3. Customer demand occurs
            day_demand = demands[t]
            if current_stock >= day_demand:
                current_stock -= day_demand
                lost_demand[t] = 0.0
            else:
                lost_demand[t] = day_demand - current_stock
                current_stock = 0.0  # stock goes to 0, no backorders in Walmart retail scenario

            # 4. Financial costs
            price = prices[t]
            holding_costs[t] = current_stock * price * holding_cost_rate
            stockout_penalties[t] = lost_demand[t] * price * stockout_penalty_rate

        # Compile records
        for t in range(n_days):
            sim_records.append({
                "date": dates[t],
                "item_id": item_id,
                "store_id": store_id,
                "demand": demands[t],
                "forecast": forecasts[t],
                "sell_price": prices[t],
                "stock": stock[t],
                "order": orders[t],
                "lost_demand": lost_demand[t],
                "holding_cost": holding_costs[t],
                "stockout_penalty": stockout_penalties[t]
            })

    df_sim = pd.DataFrame(sim_records)

    # Compute summary metrics
    total_demand = df_sim["demand"].sum()
    total_lost = df_sim["lost_demand"].sum()
    service_level = (total_demand - total_lost) / total_demand if total_demand > 0 else 1.0

    print(f"Simulation completed. Overall Service Level: {service_level*100:.2f}%")
    return df_sim

def calculate_replenishment_priorities(df_sim):
    """
    Groups by item/store to calculate stockout risk and priority score.
    Priority Score is based on total lost demand during the simulation.
    """
    priority = df_sim.groupby(["item_id", "store_id"]).agg(
        total_demand=("demand", "sum"),
        total_lost_demand=("lost_demand", "sum"),
        avg_stock=("stock", "mean"),
        total_holding_cost=("holding_cost", "sum"),
        total_penalty=("stockout_penalty", "sum"),
        sell_price=("sell_price", "mean")
    ).reset_index()

    priority["service_level"] = (priority["total_demand"] - priority["total_lost_demand"]) / priority["total_demand"]
    priority["service_level"] = priority["service_level"].fillna(1.0)

    # Priority rank: higher lost demand value = higher priority for order attention
    priority["priority_value"] = priority["total_lost_demand"] * priority["sell_price"]
    priority = priority.sort_values(by="priority_value", ascending=False).reset_index(drop=True)

    return priority
