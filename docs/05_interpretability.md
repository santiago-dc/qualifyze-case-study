# Phase 5: Interpretability

## Plan

| Step | Status |
|------|--------|
| SHAP global feature importance | Done |
| SHAP beeswarm (impact direction) | Done |
| SHAP waterfall — True Positive (why we flagged it) | Done |
| SHAP waterfall — False Negative (why we missed it) | Done |
| SHAP dependence plots (feature relationships) | Done |
| Supplier Risk Report example | Done |
| Stakeholder communication guidelines | Done |

## What is SHAP

SHAP (SHapley Additive exPlanations) decomposes each prediction into per-feature contributions. For every facility:

```
Base risk (average OAI rate) = 4.7%
  + last_classification_oai = 1     → +50%
  + n_prior_oai = 2                 → +20%
  - n_prior_nai = 5                 → -8%
  + ...
  ────────────────────────────────
  = Final risk score: 72.3%
```

Every feature adds or subtracts from the baseline. Fully transparent.

## Visualizations produced

| Plot | Question it answers | File |
|---|---|---|
| SHAP bar chart | What features matter most globally? | `fig_shap_global_importance.png` |
| SHAP beeswarm | In what direction does each feature push? | `fig_shap_beeswarm.png` |
| Waterfall (TP) | Why was this specific facility flagged? | `fig_shap_true_positive.png` |
| Waterfall (FN) | Why did we miss this facility? | `fig_shap_false_negative.png` |
| Dependence plots | What's the shape of feature → risk relationship? | `fig_shap_dependence.png` |

## Supplier Risk Report (production mockup)

The notebook generates a sample report showing how predictions would be communicated:

```
RANK #1 | Risk Score: 95.2% | Actual Outcome: OAI
  FEI Number:     3007058211
  Product Type:   Veterinary
  Country:        France
  Risk Drivers:
    ↑ last_classification_oai = 1 (impact: +2.000)
    ↑ n_prior_oai = 2             (impact: +0.535)
    ↑ days_since_last_inspection  (impact: +0.209)
```

## Key messages for stakeholders

1. **Every prediction is explainable** — no black box decisions
2. **Risk score is a signal, not a verdict** — triggers human review
3. **Model cannot predict first-time offenders** — this is where Qualifyze's private audit data adds value
4. **Audit trail**: model version, features, threshold, all loggable for regulatory compliance

## Limitations acknowledged

- The model is strongest for repeat offenders (prior OAI history)
- First-time OAI facilities with no prior history are the hardest to catch
- Public data is incomplete (FDA database caveat)
- Entity matching introduces noise for warning letters/enforcement signals
