import numpy as np

from smart_replenishment.models.baselines import CrostonSBA, SeasonalNaive


def test_seasonal_naive():
    # History with weekly seasonality: [1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7]
    history = np.array([1, 2, 3, 4, 5, 6, 7, 1, 2, 3, 4, 5, 6, 7])
    model = SeasonalNaive(lag=7)
    preds = model.predict(history, horizon=7)

    # Forecasts for next 7 days should match the last 7 days: [1, 2, 3, 4, 5, 6, 7]
    assert np.array_equal(preds, np.array([1, 2, 3, 4, 5, 6, 7]))

def test_croston_sba():
    # Simple intermittent series: demand occurs every 3 days
    series = np.array([0, 0, 3, 0, 0, 3, 0, 0, 3])

    # Croston
    model_c = CrostonSBA(alpha=0.1, method="croston")
    preds_c = model_c.fit_predict(series, horizon=5)

    # Demand size y = 3, interval p = 3 -> forecast should be around 3/3 = 1.0
    assert len(preds_c) == 5
    assert np.allclose(preds_c, 1.0, atol=0.2)

    # SBA
    model_s = CrostonSBA(alpha=0.1, method="sba")
    preds_s = model_s.fit_predict(series, horizon=5)

    # SBA applies a correction: (1 - 0.1/2) * (3/3) = 0.95
    assert np.allclose(preds_s, 0.95, atol=0.2)
