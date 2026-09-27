# Facial Comparison

`POST /api/models/compare` (`app/services/model_service.py:compare_faces`)
produces a `FacialComparison` row with two independent, clearly-labeled
signals — neither is presented as proof of identity (spec section 24):

1. **Cosine similarity** (`app/ml/classifier.py:cosine_similarity`) between
   the subject face's feature vector and a `reference_face_id`'s vector, if
   one is supplied. Deterministic, bounded to `[-1, 1]`, `0.0` for a
   zero-norm vector (never `NaN`).
2. **Classifier prediction**: if a model has been trained
   (`ModelNotTrainedError` otherwise, in which case `classifier_prediction`
   stays `null` and the UI/report render "No facial comparison available."
   — never a guessed label), the current `LATEST` classifier predicts a
   label + class probabilities for the subject's feature vector.

## What's NOT done

No face-comparison result is ever converted into a certainty statement.
The API/UI/PDF report all render comparisons as "similarity score" and
"classifier result," with the disclaimer text (spec section 29.J) appearing
on every generated report: *"The output is intended as investigative/
decision-support evidence and is not an automatic legal determination."*
