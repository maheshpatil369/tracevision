# Hyperparameter Optimization

Implemented via scikit-learn's `GridSearchCV` (default) or
`RandomizedSearchCV` (`"search": "random"` in the train request) inside
`FaceClassifier.train()` — see `app/ml/classifier.py:CLASSIFIER_REGISTRY`
for the exact parameter grid per algorithm:

| Algorithm | Grid |
|---|---|
| `random_forest` | `n_estimators`: [100, 200, 400], `max_depth`: [None, 8, 16] |
| `svm` | `C`: [0.1, 1, 10], `kernel`: [rbf, linear] |
| `logistic_regression` | `C`: [0.1, 1, 10] |

Cross-validation uses `StratifiedKFold` with `n_splits = min(requested
cv_folds, smallest class count)`, so a small/imbalanced training set never
crashes with a scikit-learn fold-size error — it automatically uses as many
folds as the data actually supports (minimum 2).

## What is stored (`ModelRun`)

- `best_params` — the exact hyperparameter combination selected
- `cv_folds` — the fold count actually used (post-adjustment)
- `metrics` — accuracy/precision/recall/f1, computed on a held-out test
  split, not the CV score
- `training_samples`, `dataset_description`, `trained_at`

Optuna is listed as an optional dependency in the original spec's
recommended stack but is **not** currently wired in — `GridSearchCV`/
`RandomizedSearchCV` cover the requirement as written. See
`docs/implementation-checklist.md`.
