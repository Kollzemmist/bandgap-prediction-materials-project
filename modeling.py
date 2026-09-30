"""
Model definitions, metrics, and split helpers for band-gap prediction.

Mirrors the logic in notebooks/04_modeling.ipynb and
notebooks/05_model_comparison.ipynb -- see those notebooks for the full
grouped-CV / held-out-test protocol, the leakage review, and the bootstrap
uncertainty analysis this module's output was evaluated with.

Hyperparameters below are the fixed, untuned values used throughout this
project (see the main README's "Limitations" section for why tuning was
deliberately left as future work rather than done here).
"""

import numpy as np
from sklearn.dummy import DummyRegressor
from sklearn.linear_model import Ridge
from sklearn.ensemble import RandomForestRegressor, ExtraTreesRegressor, HistGradientBoostingRegressor
from sklearn.pipeline import make_pipeline
from sklearn.preprocessing import StandardScaler
from sklearn.model_selection import GroupShuffleSplit, GroupKFold
from sklearn.metrics import mean_absolute_error, mean_squared_error, r2_score, median_absolute_error

RANDOM_SEED = 42
N_TREES = 100

# NaN handling: only HistGradientBoosting accepts missing feature values natively.
# The others must be fit on complete-case rows only (see notebooks/04_modeling.ipynb,
# "Missing values and how each model handles them").
MODEL_FACTORIES = {
    "Dummy (mean)": lambda: DummyRegressor(strategy="mean"),
    "Ridge": lambda: make_pipeline(StandardScaler(), Ridge(alpha=1.0)),
    "RandomForest": lambda: RandomForestRegressor(
        n_estimators=N_TREES, min_samples_leaf=3, n_jobs=-1, random_state=RANDOM_SEED),
    "ExtraTrees": lambda: ExtraTreesRegressor(
        n_estimators=N_TREES, min_samples_leaf=3, n_jobs=-1, random_state=RANDOM_SEED),
    "HistGradientBoosting": lambda: HistGradientBoostingRegressor(
        max_iter=300, learning_rate=0.1, early_stopping=False, random_state=RANDOM_SEED),
}
NAN_OK = {"Dummy (mean)": False, "Ridge": False, "RandomForest": False,
          "ExtraTrees": False, "HistGradientBoosting": True}


def regression_metrics(y_true, y_pred) -> dict:
    """MAE, RMSE, R2, and median absolute error -- the same four metrics
    reported at every stage of this project (never R2 alone)."""
    return {
        "MAE": float(mean_absolute_error(y_true, y_pred)),
        "RMSE": float(np.sqrt(mean_squared_error(y_true, y_pred))),
        "R2": float(r2_score(y_true, y_pred)),
        "MedAE": float(median_absolute_error(y_true, y_pred)),
    }


def grouped_train_test_split(X, y, groups, test_size=0.20, random_state=RANDOM_SEED):
    """Formula-grouped split: every row sharing a `groups` value (e.g. the same
    formula_pretty) lands entirely on one side, preventing identical-composition
    leakage between polymorphs. See notebooks/04_modeling.ipynb for a documented
    comparison against a naive random split (41.6% formula overlap in this
    project's data -- i.e. why this function exists)."""
    gss = GroupShuffleSplit(n_splits=1, test_size=test_size, random_state=random_state)
    train_idx, test_idx = next(gss.split(X, y, groups))
    assert set(np.asarray(groups)[train_idx]).isdisjoint(set(np.asarray(groups)[test_idx])), \
        "Formula overlap between grouped train and test -- this should be impossible."
    return train_idx, test_idx


def grouped_cross_validate(model_name, X, y, groups, train_idx, n_splits=5):
    """Grouped k-fold CV on the training portion only. Returns a list of
    per-fold metric dicts (aggregate as needed by the caller)."""
    gkf = GroupKFold(n_splits=n_splits)
    fold_metrics = []
    for tr_rel, va_rel in gkf.split(train_idx, y[train_idx], np.asarray(groups)[train_idx]):
        tr, va = train_idx[tr_rel], train_idx[va_rel]
        assert set(np.asarray(groups)[tr]).isdisjoint(set(np.asarray(groups)[va]))
        model = MODEL_FACTORIES[model_name]()
        model.fit(X[tr], y[tr])
        fold_metrics.append(regression_metrics(y[va], model.predict(X[va])))
    return fold_metrics
