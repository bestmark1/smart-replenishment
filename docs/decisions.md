# Architectural Decisions & Assumptions

## Business Problem & Context
The goal is to build an end-to-end demand forecasting and inventory replenishment support system for Walmart stores based on the M5 Forecasting Accuracy dataset.
* **Objective:** Predict unit demand at the `store_id × item_id` level for a 28-day future horizon.
* **Replenishment Policy:** Estimate stock level and order requirements based on predicted demand, lead times, holding costs, and stockout penalties.
* **Target Audience:** Inventory replenishing managers who make inventory replenishment decisions.

## Scope & Constraints
To ensure the pipeline is lightweight and runs efficiently on local resources:
* **Scope:** We filter the data to `state_id = CA` and `cat_id = FOODS`.
* **Reasoning:** A full-scale roll-out of all 30k rows results in tens of millions of rows, requiring extensive compute resources and distributed pipelines. Limiting scope lets us build, validate, and demonstrate a production-like pipeline in a local environment.

## Metrics
* **Statistical Performance:** Scoped weighted Root Mean Squared Scaled Error (RMSSE) is the primary metric. Weighted Mean Absolute Percentage Error (WMAPE) is the secondary business-friendly metric.
* **Business Performance:** Service Level (SL) and total holding vs. stockout costs proxies estimated via simulation.

## Inventory Policy Assumptions
* Periodic inventory review performed daily.
* Lead time is fixed at **7 days** (time between order placement and receipt).
* Starting stock, holding cost, and stockout penalty factors are defined in the config.
* The system is a simulation scenario / proxy and not a claim of actual Walmart store policies or stock levels.

## Modeling Choices
* **Why GBDTs (LightGBM/CatBoost)?** Tabular time-series tasks with calendar events, SNAP flags, and product characteristics are solved most efficiently using gradient boosted decision trees. They are computationally efficient, interpretable, and scale well.
* **Why not Deep Learning / LLMs?** Deep learning models require significant training times, large GPU resources, and complex tuning. LLMs / RAG are unsuitable for numerical forecasting. Simple baselines and GBDTs provide high accuracy with minimal resource footprint.

## Risks
* **Intermittent Demand:** Many items have zero sales on multiple days (zero-inflation / intermittent demand). We use SBA/Croston baselines as benchmarks to address this.
* **Data Leakage:** Rolling predictions must not look into the future. We enforce target leakage checks during backtesting.
