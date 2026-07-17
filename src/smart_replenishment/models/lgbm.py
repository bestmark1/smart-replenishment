import lightgbm as lgb
import numpy as np


def train_lgbm(df_train, feature_cols, target_col="demand", cat_cols=None):
    """
    Train a global LightGBM Regressor.
    """
    print(f"Training LightGBM model on {len(df_train)} rows...")

    # Simple LGBM Regressor
    model = lgb.LGBMRegressor(
        n_estimators=100,
        learning_rate=0.08,
        num_leaves=31,
        random_state=42,
        n_jobs=-1,
        importance_type="gain"
    )

    X_train = df_train[feature_cols]
    y_train = df_train[target_col]

    # LightGBM handles categories natively if they are of 'category' type
    model.fit(X_train, y_train, categorical_feature=cat_cols)
    return model

def predict_lgbm(model, df_test, feature_cols):
    """
    Generate non-negative predictions.
    """
    X_test = df_test[feature_cols]
    preds = model.predict(X_test)
    # Ensure forecasts are non-negative
    return np.clip(preds, 0.0, None)
