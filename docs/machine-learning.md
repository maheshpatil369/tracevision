# Machine Learning (Facial Classifier)

`app/ml/classifier.py`'s `FaceClassifier` wraps a scikit-learn
`Pipeline(StandardScaler, <algorithm>)`. Supported algorithms: `random_forest`,
`svm`, `logistic_regression` (spec section 22's list; XGBoost is in
`requirements.txt` but not yet wired into `CLASSIFIER_REGISTRY` — see
`docs/implementation-checklist.md`).

## Training request

```
POST /api/models/train
{
  "algorithm": "random_forest",
  "cv_folds": 5,
  "search": "grid",
  "dataset_description": "internal labeled face set, 2026-09",
  "samples": [
    {"feature_vector": [0.12, 0.34, ...], "label": "subject_a"},
    {"feature_vector": [0.55, 0.21, ...], "label": "subject_b"},
    ...
  ]
}
```
`feature_vector` should come from `Face.geometric_features.vector` for
faces the analyst has manually labeled. At least 4 samples across >= 2
classes are required (`INSUFFICIENT_SAMPLES` otherwise).

## What happens

1. Data is split into train/test (stratified 75/25).
2. `GridSearchCV` (or `RandomizedSearchCV` if `"search": "random"`) searches
   the algorithm's parameter grid with stratified k-fold CV
   (`app/ml/classifier.py:CLASSIFIER_REGISTRY`).
3. The best pipeline is evaluated once on the held-out test split — those
   numbers (accuracy/precision/recall/f1) are what gets stored, not the CV
   score, so the reported metric reflects genuinely unseen data.
4. The trained pipeline is persisted via `joblib` under
   `models/classifiers/<version>.joblib` + a `.json` metadata sidecar, and
   a `LATEST` pointer file is updated.
5. A `ModelRun` row is written with real metrics — a metric is `null`
   ("Not available") only if it genuinely could not be computed, never a
   fabricated placeholder.

## Training is separate from per-video analysis (spec section 23)

Nothing in `AnalysisOrchestrator` calls `.train()`. Training only happens
via the explicit `/api/models/train` endpoint, so a routine video-analysis
run never triggers an expensive hyperparameter search.
