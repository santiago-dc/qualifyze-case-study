# Phase 4: Modeling

## Plan

| Step | Status |
|------|--------|
| Logistic Regression baseline (no weights) | Done |
| Logistic Regression with balanced class weights | Done |
| XGBoost baseline (no weights) | Done |
| XGBoost with scale_pos_weight | Done |
| Hyperparameter tuning (RandomizedSearchCV, PR-AUC) | Done |
| ROC and PR curve comparison | Done |
| Threshold analysis | Done |
| Business interpretation of threshold | Done |
| Feature importance | Done |

## Results

### Model comparison

| Model | ROC-AUC | PR-AUC | F1@0.5 |
|---|---|---|---|
| LogReg (no weights) | 0.715 | 0.249 | 0.189 |
| LogReg (balanced) | 0.734 | 0.246 | 0.170 |
| XGBoost (no weights) | 0.869 | 0.366 | 0.142 |
| XGBoost (weighted) | 0.875 | 0.366 | 0.246 |
| **XGBoost (tuned)** | **0.874** | **0.366** | **0.202** |

### Hyperparameter search
- Method: RandomizedSearchCV, 30 iterations
- CV: TimeSeriesSplit (3 folds) — respects temporal ordering
- Scoring: `average_precision` (PR-AUC)
- Best CV score: 0.3008
- Best params: max_depth=5, n_estimators=408, learning_rate=0.039, scale_pos_weight=34.2, subsample=0.93, colsample_bytree=0.78, gamma=1.67, min_child_weight=6

### Threshold choice (for production use)
- Threshold = 0.046 (for XGBoost no-weights) or 0.603 (for tuned model)
- Recall = 80%, Precision = 14%
- Rationale: asymmetric costs — missing a risky supplier is more costly than a false alarm

### Top features (tuned model)
1. `last_classification_oai` (49%) — dominant predictor
2. `n_prior_oai` (11%)
3. `n_prior_nai` (7%)
4. `project_area` (5.5%)
5. `product_type` (5.2%)
6. `recent_oai_rate` (3.1%)
7. `avg_citations_per_inspection` (2.3%)

## Design decisions

### Why not SMOTE / oversampling
- 7,200 positive cases is sufficient for learning
- Dominant feature is binary (`last_classification_oai`) — can't meaningfully interpolate
- SMOTE with temporal data risks creating unrealistic combinations
- Class weights achieve the same effect without manipulating data

### Why PR-AUC for optimization (not recall, precision, or F1)
- Optimizing recall alone → model predicts everything positive
- Optimizing precision alone → model only flags obvious cases
- Optimizing F1 → ties you to a fixed threshold (usually 0.5)
- PR-AUC improves ranking quality across ALL thresholds — any operating point benefits

### Why temporal split (not random)
- We're predicting the future, not interpolating
- Random split leaks future information (a 2026 inspection in train helps predict 2024 test)
- TimeSeriesSplit in CV also respects this within training

## Key insight

The model essentially says: **"the best predictor of a future OAI is a recent OAI."** This makes business sense — facilities with systemic quality issues don't fix them overnight. The additional features (citations, recalls, warning letters) provide complementary signals that help when prior classification is ambiguous.
