# Smart Replenishment

Система прогнозирования спроса и поддержки решений о пополнении запасов в ритейле на наборе данных M5 Forecasting Accuracy.

---

## 1. О проекте

Проект реализует полный Data Science-цикл: подготавливает витрину ежедневных продаж на уровне `магазин × товар`, прогнозирует спрос на следующие 28 дней и оценивает сценарный риск дефицита. Результат предназначен для менеджера пополнения запасов: он видит прогноз, фактический спрос на тестовом периоде и позиции с наибольшим приоритетом.

Это учебный проект на обезличенных данных M5, а не производственная система Walmart. В датасете отсутствуют фактические остатки и закупочная себестоимость, поэтому блок пополнения — прозрачная симуляция с настраиваемыми допущениями, а не утверждение об «оптимальном заказе» для реального бизнеса.

### Ключевые результаты

- **Финальная модель:** LightGBM; WMAPE **62,99%**, средний RMSSE **0,9268** на отложенном 28-дневном тестовом горизонте.
- **Лучший baseline:** SBA (Syntetos–Boylan Approximation); WMAPE **69,70%**, средний RMSSE **0,9806**.
- **Статистическое сравнение:** парный критерий Уилкоксона дал `p ≈ 8,07 × 10⁻⁷⁴`; bootstrap 95% CI улучшения WMAPE: `[5,27; 6,46]` п.п.
- **Сценарий пополнения:** service level **85,04%** для 5 748 товарных позиций в выбранном scope Калифорнии. Это результат симулятора, не измерение реальных складских остатков.

---

## 2. Архитектура и путь данных

```text
M5 CSV (зеркало Zenodo)
   └── data/raw/m5
        └── quality.py: аудит качества → reports/data_quality.json
             └── mart.py: подготовка DuckDB-витрины → data/processed/smart_replenishment.db
                  └── build.py: создание lag- и rolling-признаков
                       └── backtest.py: rolling validation на трёх временных fold
                            └── statistics.py: bootstrap и критерий Уилкоксона
                                 └── inventory.py: симулятор политики пополнения
                                      ├── FastAPI
                                      └── Streamlit dashboard
```

---

## 3. Структура репозитория

```text
smart-replenishment/
  README.md
  pyproject.toml              # зависимости и настройки Ruff
  Makefile                    # короткие команды для пайплайна
  configs/base.yaml           # параметры пайплайна
  src/smart_replenishment/
    data/                     # загрузка, аудит и DuckDB-витрина
    features/                 # lag- и rolling-признаки
    models/                   # naive, Croston/SBA, LightGBM, CatBoost
    evaluation/               # метрики, backtest, bootstrap, Wilcoxon
    simulation/               # политика пополнения
    api/                      # FastAPI endpoints
    dashboard/                # Streamlit UI
  notebooks/                  # EDA и анализ моделей
  tests/                      # pytest unit-тесты
  docs/                       # методология, словарь данных и доказательства по рубрике
```

---

## 4. Установка и подготовка данных

### Локальное окружение

```bash
git clone https://github.com/bestmark1/smart-replenishment.git
cd smart-replenishment
python3 -m venv .venv
source .venv/bin/activate
make setup
```

### Полный пайплайн

Исходные M5-файлы скачиваются в `data/raw/m5/` и не попадают в Git. Чтобы выполнить загрузку, проверку качества и создание DuckDB-витрины:

```bash
make pipeline
python -m smart_replenishment.cli train
python -m smart_replenishment.cli evaluate
python -m smart_replenishment.cli simulate
```

Альтернативно можно запустить весь цикл одной командой:

```bash
python -m smart_replenishment.cli run-all
```

---

## 5. API и дашборд

### FastAPI

```bash
make run-api
```

- Healthcheck: `curl http://localhost:8000/health`
- Приоритеты пополнения: `curl 'http://localhost:8000/priorities?store_id=CA_1&limit=5'`
- Прогноз ряда: `curl http://localhost:8000/forecast/FOODS_3_120_CA_1`

### Streamlit dashboard

```bash
make run-app
```

Откройте `http://localhost:8501`: интерфейс показывает метрики, приоритеты пополнения и прогноз выбранного товара.

### Локальный запуск в Docker

```bash
make compose-up
```

Docker-контейнеры получают готовые прогнозы через read-only mount `data/processed/`; они не запускают обучение модели.

---

## 6. Проверки качества

```bash
make test
ruff check .
ruff format --check .
```

Тесты покрывают baseline-модели, WMAPE/RMSSE и health endpoint API. Методология, ограничения, словарь данных и соответствие критериям оценки находятся в [`docs/`](docs/).

---

## 7. Деплой на VPS

Для VPS с ограниченной RAM обучение выполняется локально; сервер получает только Docker-образ и два готовых Parquet-артефакта. Демо доступно по HTTPS: [smart-replenishment.185.79.138.118.nip.io](https://smart-replenishment.185.79.138.118.nip.io). Отдельный домен не требуется: используется `nip.io`. Полный сценарий описан в [`docs/deployment.md`](docs/deployment.md).
