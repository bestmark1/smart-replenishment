# Methodology Report

## 1. Time-Series Forecasting Strategy

We formulated the problem as a global tabular regression task using historical sales, price features, calendar events, and SNAP flags.

### GBDT Models
We implemented and compared two leading gradient boosting frameworks:
* **LightGBM:** Fast, memory-efficient, and optimized for large datasets. It uses histogram-based split finding and handles categorical variables natively.
* **CatBoost:** Built-in support for symmetric trees and ordered boosting to prevent overfitting. Exceeds at handling high-cardinality categorical variables.

### Baseline Models
To prove ML model value, we benchmarked them against:
* **Seasonal Naive (lag 7 / lag 28):** Evaluates weekly patterns by projecting sales from exactly 7 or 28 days prior.
* **Croston's Method & Syntetos-Boylan Approximation (SBA):** Tailored baseline for zero-inflated / intermittent demand that separates demand size and interval.

---

## 2. Validation & Backtesting

We used a **3-fold rolling-origin backtesting** structure on 28-day validation folds:
* **Fold 3 (Last):** Val = $[T_{max} - 27 \text{ days}, T_{max}]$, Train = $[ \text{start}, T_{max} - 28 \text{ days} ]$
* **Fold 2:** Val = $[T_{max} - 55 \text{ days}, T_{max} - 28 \text{ days}]$, Train = $[ \text{start}, T_{max} - 56 \text{ days} ]$
* **Fold 1:** Val = $[T_{max} - 83 \text{ days}, T_{max} - 56 \text{ days}]$, Train = $[ \text{start}, T_{max} - 84 \text{ days} ]$

---

## 3. Statistical Model Selection

To select the final champion model:
1. **Paired Wilcoxon Signed-Rank Test:** Performed on the per-series RMSSE errors to verify if the median difference in errors between the GBDT model and the best baseline is significantly different from zero.
2. **Paired Block Bootstrap:** Resampled series with replacement 1000 times to construct a **95% Confidence Interval** for the mean RMSSE difference. If the entire interval is above 0, the improvement is statistically significant.

---

## 4. Inventory Replenishment Simulation

We implemented a **daily periodic review replenishment simulator** with:
* **Lead Time ($L$):** 7 days fixed.
* **Review Period ($R$):** 1 day.
* **Target Stock Level ($S$):** Calculated based on the forecasted demand sum over the lead time and review period plus a 50% safety stock buffer:
  $$S_t = \sum_{k=0}^{L+R-1} \hat{Y}_{t+k} + SafetyStock$$
* **Replenishment Order ($Order_t$):** Places an order of size $\max(0, S_t - IP_t)$, where $IP_t$ is the current inventory position (Stock + On-Order).
* **Financial Metrics:**
  * Holding Cost = $EndingStock_t \times Price \times 0.05$
  * Stockout Penalty = $LostDemand_t \times Price \times 1.5$
* **Replenishment Priorities:** SKU × store groups are ranked by total lost demand value.
