# Training Data: Synthetic Cold-Start Dataset

## Why synthetic data

CognOS has no real usage logs yet at this stage of the project (Day 5).
Rather than delay the ML pipeline until enough real data accumulates,
a synthetic dataset is generated with **documented, defensible labeling
heuristics** — this is a standard cold-start technique, and being
explicit about it here (rather than presenting synthetic data as if it
were real) is the honest way to use it.

## Generation process

`scripts/generate_training_data.py` simulates 40 work sessions of 60
events each (2,400 rows total), using a fixed random seed for
reproducibility. Each event's features are computed by the *same*
`FeatureExtractor` used in production — so the training distribution
matches the live-inference feature distribution by construction, not
by coincidence.

## Labeling heuristic

A soft-probability model, not a hard rule, so the resulting dataset
isn't linearly separable (which would make any classifier trivially
"perfect" and tell us nothing about generalization):

| Signal | Probability contribution |
|---|---|
| Base rate | 0.05 |
| First time seeing this app today | +0.25 |
| ≥3 window switches in the last 5 min ("thrashing") | +0.30 |
| >300s since last LLM call AND app changed | +0.15 |
| App is an IDE or terminal | +0.10 |

Capped at 0.9 (never a certainty), then a Bernoulli draw determines the
actual label. This keeps the resulting positive rate realistic
(~10-20%, verified by `test_positive_rate_is_realistic_not_extreme`)
and avoids a dataset where the "obvious" heuristics get scored 100%
correct even by a trivial classifier.

## Known limitation

This is a stand-in, not ground truth. The heuristics encode *assumptions*
about what's worth flagging (novelty, thrashing, quiet-then-change),
not observed human judgment. Day 8 adds a `cognos train` retraining
path that uses **real** logged + user-labeled data (was a suggestion
actually acted on, dismissed, or ignored) to replace this synthetic
foundation once enough real usage exists. Model metrics reported
before Day 8 (see `models/metrics.json`) should be read as "does the
model learn the encoded heuristics," not "does it match real user
judgment" — that claim only becomes valid after retraining on real data.