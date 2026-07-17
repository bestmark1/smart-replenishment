import numpy as np
from catboost import CatBoostRegressor


def train_catboost(df_train, feature_cols, target_col="demand", cat_cols=None):
    """
    Train a global CatBoost Regressor.
    """
    print(f"Training CatBoost model on {len(df_train)} rows...")

    # We specify categorical features index or names
    model = CatBoostRegressor(
        iterations=100,
        learning_rate=0.1,
        depth=6,
        random_seed=42,
        thread_count=-1,
        verbose=10
    )

    X_train = df_train[feature_cols]
    y_train = df_train[target_col]

    # Convert categorical cols to string/object representation if needed,
    # but Pandas category dtype is supported if we pass cat_features
    # Let's ensure cat_cols are passed as names
    model.fit(X_train, y_train, cat_features=cat_cols)
    return model

def predict_catboost(model, df_test, feature_cols):
    """
    Generate non-negative predictions.
    """
    X_test = df_test[feature_cols]
    preds = model.predict(X_test)
    return np.clip(preds, 0.0, None)
