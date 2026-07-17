# Smart Replenishment

Demand forecasting and inventory replenishment support system in retail using the M5 Forecasting Accuracy dataset.

---

## 1. Project Overview

This project implements an end-to-end Data Science pipeline that predicts daily sales demand at the `store × item` level for the next 28 days and estimates optimal replenishment orders. It helps supply chain managers minimize lost sales and holding costs under realistic constraints.

### Key Results
* **Champion Model:** LightGBM (WMAPE: **62.99%**, Mean RMSSE: **0.9268**) on the final untouched test horizon.
* **Baseline (SBA):** WMAPE: **69.70%**, Mean RMSSE: **0.9806**.
* **Statistical Significance:** Paired Wilcoxon signed-rank test $p-value \approx 8.06 \times 10^{-74}$, proving LightGBM significantly outperforms baseline.
* **Replenishment Impact:** Generated a simulated service level of **85.04%** across 5,748 items in California.

---

## 2. Architecture & Pipeline Flow

```text
M5 CSV (Zenodo mirror)
   └── data/raw/m5
        └── quality.py (Data Quality Audit) -> reports/data_quality.json
             └── mart.py (Reshaping & Ingestion) -> data/processed/smart_replenishment.db (DuckDB)
                  └── build.py (Feature Engineering)
                       └── backtest.py (3-Fold Rolling Validation)
                            └── statistics.py (Bootstrap & Wilcoxon Tests)
                                 └── inventory.py (Replenishment Simulation)
                                      ├── api/main.py (FastAPI Server)
                                      └── dashboard/app.py (Streamlit UI)
```

---

## 3. Repository Structure

```text
smart-replenishment/
  README.md
  pyproject.toml              # Dependencies and Ruff config
  Makefile                    # CLI runner shortcuts
  .gitignore
  configs/base.yaml           # Pipeline settings
  src/smart_replenishment/
    cli.py                    # Entrypoint CLI
    config.py                 # Configuration loader
    data/                     # Ingestion, quality, and DuckDB mart
    features/                 # Lag and rolling feature building
    models/                   # Naive, Croston/SBA, LGBM, CatBoost
    evaluation/               # Metrics, Backtest, Wilcoxon/Bootstrap stats
    simulation/               # Replenishment policy simulation
    api/                      # FastAPI endpoints
    dashboard/                # Streamlit app
  notebooks/                  # Jupyter notebooks for EDA and model analysis
  tests/                      # pytest unit tests
  docs/                       # Decisions, data dictionary, deployment, rubric
```

---

## 4. Setup & Ingestion

### Local Environment Setup
1. Clone the repository and navigate into it:
   ```bash
   cd smart-replenishment
   ```
2. Create and activate a virtual environment:
   ```bash
   python3 -m venv .venv
   source .venv/bin/activate
   ```
3. Install package and dependencies:
   ```bash
   make setup
   ```

### Running the End-to-End Pipeline
To download the dataset, run quality checks, create the DuckDB database, train models, select the champion, and run the inventory simulation, execute:
```bash
make pipeline
python -m smart_replenishment.cli train
python -m smart_replenishment.cli evaluate
python -m smart_replenishment.cli simulate
```
Alternatively, run everything with a single command:
```bash
python -m smart_replenishment.cli run-all
```

---

## 5. API & Dashboard Services

### Run FastAPI Server
Start the API locally:
```bash
make run-api
```
Query endpoints:
* **Health:** `curl http://localhost:8000/health`
* **Replenishment Priorities:** `curl http://localhost:8000/priorities?store_id=CA_1&limit=5`
* **Series Forecast:** `curl http://localhost:8000/forecast/FOODS_3_120_CA_1`

### Run Streamlit App
Start the UI:
```bash
make run-app
```
*Open `http://localhost:8501` to view metrics, priority tables, and forecasts.*

### Containerized Run (Docker Compose)
If the Docker daemon is active on your host:
```bash
make compose-up
```

---

## 6. Running Tests & Linters
* **Unit Tests:** `make test`
* **Code Style check:** `ruff check` and `ruff format`
