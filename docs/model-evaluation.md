# Model / Evaluation Information

Surfaced in three places, all reading the same underlying data so they
can never disagree:

1. **Frontend Models page** (`frontend/src/pages/Models.tsx`) — table of
   every `ModelRun`.
2. **Analysis Overview tab** — `detector_backend` and `tracker_name` for
   that specific run.
3. **PDF report, section H** — detector, tracker, facial model, classifier
   version, and accuracy/precision/recall/F1.

## No invented metrics (spec section 57)

`ModelRun.accuracy/precision/recall/f1_score` are nullable columns.
`ModelRun.to_dict()` renders a `None` value as the literal string
`"Not available"` rather than `0` or an empty string — `0` would be a
plausible-looking but false metric value, so the API deliberately returns
a string in that field rather than a number when there is nothing real to
report.
