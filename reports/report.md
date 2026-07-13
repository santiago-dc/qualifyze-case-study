# Qualifyze AI Data Scientist — Case Study Report

## Executive Summary

We built a predictive model to assess supplier non-compliance risk using publicly available FDA data. The model achieves a **ROC-AUC of 0.87** and can identify 80% of facilities that will receive an Official Action Indicated (OAI) classification on their next inspection, making it a viable screening tool for supply chain risk management.

Key results:
- **5 data sources** integrated (inspections, citations, warning letters, enforcement actions, Form 483s)
- **165,010 inspections** processed across drugs, devices, biologics, veterinary, and cosmetics sectors
- **22 engineered features** capturing facility history, citation patterns, warning letters, and recalls
- **Best model**: XGBoost with class weighting — ROC-AUC 0.87, PR-AUC 0.37
- **Full explainability**: every prediction decomposed via SHAP values

---

## 1. Data Processing & Feature Engineering

### 1a. Data import and standardization strategy

We ingested data from 4 of the 5 sources provided in the case brief:

| Source | Method | Records | Key fields |
|---|---|---|---|
| Warning Letters (FDA.gov) | Paginated API scraping | 3,608 | Company, date, violation type |
| Inspection Classifications (FDA Dashboard) | Manual download (Qlik Sense) | 337,519 | FEI, classification (NAI/VAI/OAI), date |
| Citations (FDA Dashboard) | Manual download | 277,463 | Inspection ID, CFR code, description |
| Enforcement/Recalls (openFDA) | Bulk JSON download | 86,419 | Firm, class (I/II/III), product, reason |
| Published 483s (FDA Dashboard) | Manual download | 1,973 | FEI, date, PDF link |

The ingestion scripts (`src/data/`) are designed for repeated execution and can be orchestrated via Airflow DAGs for production use.

### 1b. Linking public and private data

The **FEI Number** (Facility Establishment Identifier) serves as the primary key across inspections, citations, and Form 483s.

For warning letters and enforcement actions (which lack FEI), we implemented **entity resolution**:
- Name normalization (lowercase, strip legal suffixes, remove d/b/a clauses)
- TF-IDF character n-gram vectorization (2-4 grams)
- Cosine similarity matching with threshold 0.8

Results: 805 warning letter matches (34.2%) and 3,220 enforcement matches (70.2%).

In a production system, Qualifyze's **private audit data** would be linked via:
- Direct FEI matching where available
- Company registration databases (DUNS, LEI) for additional identifiers
- The same fuzzy matching pipeline, enhanced with location (city/country) as a tiebreaker

### 1c. Preprocessing pipeline

```
Raw Data → Scope Filtering → Entity Resolution → Feature Engineering → Model-ready Dataset
```

1. **Scope filtering**: Exclude pure food-related inspections (keep drugs, devices, biologics, veterinary, cosmetics)
2. **Date parsing**: Standardize all dates to datetime, handle missing values with `errors="coerce"`
3. **Entity resolution**: Match warning letters and enforcement to facility FEI numbers
4. **Feature engineering**: For each inspection, compute features from the facility's PRIOR history only (temporal leakage prevention)

### 1d. Handling missing and inconsistent data

| Issue | Approach |
|---|---|
| Missing dates in 483s | `errors="coerce"` → NaT → drop row |
| FEI as float in 483s | Cast to Int64 (nullable integer) |
| Inconsistent company names | TF-IDF fuzzy matching with 0.8 threshold |
| Missing prior history (first inspection) | Default to 0/−1 sentinel values |
| FDA database not comprehensive | Acknowledged as limitation; model framed as "public-data baseline" |

---

## 2. Predictive Modeling & Insights

### 2a. Model prototype

**Target**: Binary classification — will this facility receive OAI on its current inspection?

**Validation strategy**: Temporal split (train on pre-2025, test on 2025+). No random splits — we're predicting the future.

**Models trained**:

| Model | ROC-AUC | PR-AUC | Notes |
|---|---|---|---|
| Logistic Regression (baseline) | 0.715 | 0.249 | Fully interpretable coefficients |
| Logistic Regression (balanced) | 0.734 | 0.246 | Addresses class imbalance |
| XGBoost (no weights) | 0.869 | 0.366 | Strong ranking ability |
| XGBoost (weighted) | 0.875 | 0.366 | Better calibrated probabilities |
| XGBoost (tuned) | 0.874 | 0.366 | Hyperparameter search via RandomizedSearchCV |

**Class imbalance handling**: Used `scale_pos_weight` (ratio of negatives to positives ≈ 20:1) rather than SMOTE. Rationale: sufficient positive examples (7,200), dominant feature is binary, and SMOTE with temporal data risks creating unrealistic synthetic examples.

**Hyperparameter tuning**: 30-iteration RandomizedSearchCV with TimeSeriesSplit (3 folds), optimizing PR-AUC. Best parameters: max_depth=5, n_estimators=408, learning_rate=0.039, scale_pos_weight=34.2.

### 2b. Key features influencing supplier risk

| Rank | Feature | Importance | Interpretation |
|---|---|---|---|
| 1 | `last_classification_oai` | 49% | Most recent inspection was OAI |
| 2 | `n_prior_oai` | 11% | Count of historical OAI inspections |
| 3 | `n_prior_nai` | 7% | Clean history reduces risk |
| 4 | `project_area` | 5.5% | Regulatory sector matters |
| 5 | `product_type` | 5.2% | Drug/device higher risk than biologics |
| 6 | `recent_oai_rate` | 3.1% | Trend in recent inspections |
| 7 | `avg_citations_per_inspection` | 2.3% | Citation load signals quality issues |
| 8 | `max_citations_single_inspection` | 2.1% | Peak violation count |
| 9 | `n_prior_inspections` | 1.8% | Experience/oversight level |
| 10 | `days_since_last_inspection` | 1.7% | Recency of last assessment |

**Key insight**: The strongest predictor is a recent OAI — facilities with systemic quality issues tend to persist. Complementary signals (citations, recalls, warning letters) help when classification history is ambiguous.

### 2c. Model performance and trade-offs

**Threshold selection** is driven by business context:

| Recall | Precision | What it means |
|---|---|---|
| 90% | 10% | Catch almost everything, many false alarms |
| **80%** | **14%** | **Recommended: balanced screening** |
| 60% | 25% | Fewer alerts, more missed risks |
| 40% | 40% | High-confidence flags only |

**We recommend 80% recall** because:
- False positives are cheap (analyst reviews supplier, finds no issue)
- False negatives are expensive (client's supply chain partner gets enforcement action)
- The model is a screening tool, not an autonomous decision-maker

---

## 3. Interpretability

### 3a. Model explainability

Every prediction is fully decomposable using **SHAP (SHapley Additive exPlanations)**:

1. **Global importance**: Which features matter most across all predictions
2. **Local explanations**: For any specific facility, "your risk is 73% because: last inspection was OAI (+50%), you have 3 prior OAIs (+12%), ..."
3. **Dependence analysis**: How each feature's value relates to its risk contribution

### 3b. Transparency for stakeholders

**Supplier Risk Report** (production output format):
```
FACILITY: Acme Pharma Manufacturing (FEI: 3007058211)
RISK SCORE: 95.2% — CRITICAL

Risk Drivers:
  ↑ Last inspection was OAI (impact: +50%)
  ↑ 2 prior OAI inspections (impact: +12%)
  ↑ Inspected 0 days ago (impact: +5%)
  ↓ 7 total inspections (-3%)

Recommendation: Immediate review. Request updated audit.
```

**Key principles**:
- Every prediction has a human-readable explanation
- Risk score is a signal for prioritization, not an automated decision
- Human analyst always in the loop
- Full audit trail: model version, features used, threshold applied, date scored

**Limitations communicated clearly**:
- Cannot predict first-time offenders with no prior history
- Public data is incomplete (FDA inspection database is not comprehensive)
- Entity matching introduces noise for ~30% of warning letter linkages
- Model captures correlation, not causation

---

## 4. Scalability & Deployment

### 4a. Production architecture

```
┌─────────────────────────────────────────────────────────┐
│                    Airflow Orchestration                  │
├──────────┬──────────────┬───────────────┬───────────────┤
│  Weekly  │   Triggered  │    Monthly    │    Weekly     │
│          │              │               │               │
│  Data    │   Feature    │    Model      │    Batch      │
│  Ingest  │   Pipeline   │   Retrain     │   Scoring     │
│          │              │               │               │
│ FDA API  │ Entity Res.  │ Train + Eval  │ Score all     │
│ + Bulk   │ + Features   │ Champion/     │ facilities    │
│          │              │ Challenger    │ + Export      │
└────┬─────┴──────┬───────┴───────┬───────┴───────┬───────┘
     │            │               │               │
     ▼            ▼               ▼               ▼
┌─────────┐ ┌──────────┐ ┌──────────────┐ ┌────────────┐
│ data/   │ │ data/    │ │   models/    │ │  data/     │
│ raw/    │ │processed/│ │ champion.pkl │ │  scores/   │
└─────────┘ └──────────┘ └──────────────┘ └────────────┘
```

### 4b. Deployment recommendations

| Component | Recommendation |
|---|---|
| Orchestration | Airflow (DAGs provided in `dags/`) |
| Model serving | Batch scoring (weekly) via Airflow; API endpoint for on-demand queries |
| Storage | Parquet for features; PostgreSQL for scores accessible to the platform |
| Monitoring | Track prediction distribution drift weekly; alert if OAI rate in predictions deviates >2σ from training distribution |
| Retraining | Monthly champion/challenger pattern — new model only promoted if PR-AUC improves on holdout |
| Infrastructure | Docker Compose for local dev (provided); Kubernetes + managed Airflow (e.g., Cloud Composer) for production |

### 4c. Model drift monitoring

The model could degrade if:
- FDA changes inspection criteria or frequency
- New regulatory areas are added
- Company behavior changes in response to the scoring system

**Monitoring strategy**:
- Weekly: compare score distribution vs training baseline
- Monthly: compare predicted vs actual OAI rates (once outcomes are known)
- Quarterly: full retrain with last 3 years of data as sliding window

### 4d. Improvements for accuracy at scale

1. **NLP on citations**: Categorize CFR violations by severity (sterility > labeling) instead of just counting them
2. **Graph features**: Model supplier relationships and contagion effects
3. **Private data integration**: Qualifyze audit reports would dramatically improve first-time-offender detection
4. **Ensemble**: Combine XGBoost with a time-series model (e.g., survival analysis for "time to next OAI")
5. **Active learning**: Use analyst feedback on flagged suppliers to improve the model iteratively

---

## Assumptions made

1. **Scope**: Focused on drugs, devices, biologics, veterinary, and cosmetics. Excluded pure food inspections (less relevant for Qualifyze's pharma-focused supply chain).
2. **Target definition**: OAI as binary target (not severity gradient). In production, a multi-class or ordinal model could capture NAI→VAI→OAI progression.
3. **Entity matching threshold**: 0.8 cosine similarity — conservative to avoid false matches at the cost of lower coverage.
4. **Temporal split at 2025**: Simulates real deployment. Could be adjusted for more/less test data.
5. **No text features from warning letter content**: Would require scraping full letter text and NLP — deferred for time constraints but high potential value.

---

## Reproducibility

```bash
# Clone and setup
git clone <repo-url>
cd qualifyze-case-study
uv sync

# Run data ingestion (warning letters + enforcement)
uv run python src/data/fetch_all.py
# Note: inspections/citations/483s require manual download from FDA Dashboard

# Run feature engineering
uv run python src/features/build_features.py

# Run notebooks
uv run jupyter lab notebooks/

# Run Airflow locally
docker-compose up -d
# Access at http://localhost:8080 (admin/admin)
```
