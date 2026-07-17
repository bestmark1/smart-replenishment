# Data Dictionary

## 1. Raw M5 Files

### `calendar.csv`
* **date:** The calendar date (`YYYY-MM-DD`).
* **wm_yr_wk:** Walmart week ID (11101 to 11621).
* **weekday:** Day of the week (Monday, Tuesday, etc.).
* **wday:** Day of the week index (1 = Saturday, 2 = Sunday, ..., 7 = Friday).
* **month:** Month index (1 to 12).
* **year:** Year (2011 to 2016).
* **d:** Day ID string (`d_1` to `d_1969`).
* **event_name_1:** Optional first event name (SuperBowl, Thanksgiving, etc.).
* **event_type_1:** Type of event (Sporting, National, Cultural, Religious).
* **snap_CA:** SNAP flag (1 if SNAP purchases are active on this day in California, 0 otherwise).

### `sales_train_validation.csv`
* **id:** Primary series key string (`[item_id]_[store_id]_validation`).
* **item_id:** Unique SKU ID.
* **dept_id:** Department ID (FOODS_1, FOODS_2, FOODS_3).
* **cat_id:** Category ID (FOODS).
* **store_id:** Walmart store ID (CA_1, CA_2, CA_3, CA_4).
* **state_id:** State ID (CA).
* **d_1 to d_1913:** Historical demand units for each day.

### `sell_prices.csv`
* **store_id:** Store ID.
* **item_id:** SKU ID.
* **wm_yr_wk:** Walmart week ID.
* **sell_price:** Retail price for the week.

---

## 2. Analytic Mart Table (`feature_mart` in DuckDB)

* **id:** Unique series key.
* **item_id:** Unique SKU ID (Pandas category).
* **dept_id:** Department ID (Pandas category).
* **cat_id:** Category ID (FOODS).
* **store_id:** Store ID (Pandas category).
* **state_id:** State ID (CA).
* **demand:** Daily demand (units sold).
* **date:** Calendar date.
* **wm_yr_wk:** Walmart week ID.
* **weekday:** Day of week name (Pandas category).
* **wday:** Day of week index (1 to 7).
* **month:** Month index (1 to 12).
* **year:** Year.
* **event_name_1:** Calendar event name.
* **event_type_1:** Calendar event type.
* **snap:** SNAP flag for California (0 or 1).
* **sell_price:** Retail price (0.0 if inactive).
* **lag_1, lag_7, lag_14, lag_28:** Lags of demand.
* **rolling_mean_7, rolling_std_7:** 7-day rolling aggregates of demand.
* **rolling_mean_28, rolling_std_28:** 28-day rolling aggregates of demand.
* **price_change_7:** 7-day relative price change.
