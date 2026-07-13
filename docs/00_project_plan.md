# Qualifyze AI Data Scientist — Case Study Plan

## Overview

**Goal**: Build a predictive model to assess supplier non-compliance risk using FDA public data.

**Deadline**: 2026-07-17 (7 days from start)

**Deliverables**:
1. GitHub repository with working code
2. Report summarizing findings, methodologies, and recommendations
3. Slide presentation (shared 24h before the meeting)

**Stack**: Python, uv, pandas, scikit-learn, XGBoost, SHAP, matplotlib/plotly, Airflow (DAGs)

---

## Day-by-day plan

### D1 — Setup + Data Collection ✅ DONE

- [x] Create repo structure
- [x] Set up environment with `uv`
- [x] Download Warning Letters (FDA.gov datatables API → `warning_letters.json`)
- [x] Download Enforcement/Recalls (openFDA bulk → `drug-enforcement-0001-of-0001.json`)
- [x] Download Inspections (FDA Dashboard manual → `inspections.xlsx`)
- [x] Download Citations (FDA Dashboard manual → `citations.xlsx`)
- [x] Download Published 483s (FDA Dashboard manual → `published_483s.xlsx`)
- [x] Document data sources and context (`docs/01_data_collection.md`)

### D2 — EDA + Entity Resolution

- [ ] Exploratory notebook (`notebooks/01_eda.ipynb`):
  - Distribution of inspections over time, by country, by product type
  - Classification trends (is OAI increasing/decreasing?)
  - Top repeat offenders (facilities with most OAIs)
  - Warning letter volume over time and by subject category
  - Enforcement/recall patterns
- [ ] Entity resolution strategy:
  - Match warning letters → inspections by company name (fuzzy matching)
  - Match enforcement → inspections by recalling_firm (fuzzy matching)
  - Evaluate matching quality (precision/recall of the matching)
- [ ] Document findings (`docs/02_eda_findings.md`)

### D3 — Preprocessing + Feature Engineering

- [ ] Build feature pipeline (`src/features/build_features.py`):
  - Unit of analysis: **one row per facility (FEI Number) per time window**
  - Features to build:
    - `n_inspections_last_N_years` — inspection count
    - `n_oai`, `n_vai`, `n_nai` — classification history
    - `pct_oai` — OAI rate
    - `trend` — is classification getting worse or better over time?
    - `days_since_last_inspection` — recency
    - `n_citations` — total citation count
    - `n_unique_cfr_violations` — breadth of violations
    - `has_warning_letter` — binary (from entity-matched data)
    - `n_warning_letters` — count
    - `has_recall` — binary
    - `n_class_I_recalls` — most severe recalls
    - `product_type` — categorical (drugs, devices, food)
    - `country` — categorical
    - `n_483s_published` — count of published Form 483s
  - Target variable: **OAI in next inspection** (binary classification)
- [ ] Handle temporal split:
  - Train on inspections up to 2024
  - Test on 2025-2026 inspections
  - This simulates "predicting the future" realistically
- [ ] Save processed dataset (`data/processed/features.parquet`)

### D4 — Modeling

- [ ] Modeling notebook (`notebooks/02_modeling.ipynb`):
  - Baseline: Logistic Regression (interpretable by default)
  - Main model: XGBoost / LightGBM
  - Handle class imbalance (scale_pos_weight or class_weight)
  - Hyperparameter tuning (basic grid/random search)
  - Metrics: Precision-Recall AUC, ROC-AUC, F1, calibration plot
  - Temporal validation (not random split!)
- [ ] Save trained model (`src/models/`)
- [ ] Document trade-offs:
  - Precision vs Recall trade-off for the business context
  - Why we chose threshold X
  - Comparison of model complexity vs interpretability

### D5 — Interpretability

- [ ] Interpretability notebook (`notebooks/03_interpretability.ipynb`):
  - SHAP values (global feature importance)
  - SHAP local explanations (why did we flag facility X?)
  - Partial Dependence Plots for top features
  - Risk scorecard mockup: example output for a single supplier
- [ ] Discussion points for stakeholders:
  - How to communicate "this supplier has 73% risk" to a non-technical user
  - Regulatory transparency requirements
  - Confidence intervals and model uncertainty

### D6 — Report + Slides + Airflow DAGs

- [ ] Write report (`reports/report.md` or PDF):
  - Executive summary
  - Methodology
  - Key findings
  - Limitations and assumptions
  - Recommendations for production
- [ ] Create slides (Google Slides or PDF):
  - ~10-12 slides max
  - Problem → Data → Approach → Results → Interpretability → Next Steps
- [ ] Airflow DAGs (`dags/`):
  - `data_ingestion_dag.py` — periodic FDA data refresh
  - `feature_pipeline_dag.py` — preprocessing + feature engineering
  - `model_retrain_dag.py` — scheduled retraining with champion/challenger
  - `scoring_dag.py` — batch inference for all suppliers
- [ ] Docker-compose for local Airflow (`docker-compose.yml`)
- [ ] Architecture diagram (for deployment/scalability section)

### D7 — Buffer / Polish

- [ ] Review all code and remove debug artifacts
- [ ] Ensure the repo can be cloned and run end-to-end (`README.md` with instructions)
- [ ] Test notebooks run cleanly
- [ ] Rehearse presentation talking points
- [ ] Push to GitHub (personal account: santiago.dominguezc@outlook.es)

---

## Key design decisions

### Target variable

**"Will this facility receive an OAI classification in its next inspection?"** (binary)

Why OAI:
- It's the most actionable signal for supply chain risk
- It directly triggers enforcement actions (warning letters, recalls)
- Well-defined in the data (not subjective)

Alternative targets considered:
- Warning letter in next 12 months (less data, harder entity matching)
- Any enforcement action (too broad)
- VAI → OAI escalation (more specific, less data)

### Temporal validation strategy

We MUST NOT use random train/test splits because:
- Inspections are time-ordered
- We're predicting the future, not interpolating
- Random split would leak future information

**Approach**: Train on everything before 2025, test on 2025-2026.

### Entity resolution approach

For linking warning letters and enforcement data to inspections:
1. Normalize company names (lowercase, remove Inc/LLC/Ltd, strip punctuation)
2. Use fuzzy matching (Levenshtein distance or TF-IDF cosine similarity)
3. Where possible, use location (city + state) as additional matching signal
4. Accept some noise and document matching precision

### Class imbalance (3.9% OAI)

Options:
- `scale_pos_weight` in XGBoost (preferred — simple, no data manipulation)
- Threshold tuning on the probability output (business-driven threshold)
- NOT using SMOTE (tends to overfit on tabular data with temporal structure)

### Model choice rationale

- **Logistic Regression**: baseline, fully interpretable, coefficients = feature importance
- **XGBoost**: best performance on structured/tabular data, handles missing values natively, works well with imbalanced classes
- We're NOT using deep learning (no benefit on this type of structured data, harder to explain)

---

## Presentation strategy

The case study says: *"We want to understand your perspective, your hypotheses, and your decision-making process."*

Structure the presentation around **decisions and trade-offs**, not just results:
- "We chose X because Y, accepting trade-off Z"
- "Given more time/data, we would also do W"
- Show awareness of real-world deployment challenges

Key messages to land:
1. **Public data is a starting point** — the real value comes from combining with Qualifyze's private audit data
2. **Interpretability is not optional** — in regulated industries, you must explain every prediction
3. **The model is a tool, not a replacement** — it surfaces risk signals for human analysts to act on
4. **MLOps matters** — a model that can't be retrained and monitored is useless in production

---

## Repository structure

```
qualifyze-case-study/
├── notebooks/
│   ├── 01_eda.ipynb
│   ├── 02_modeling.ipynb
│   └── 03_interpretability.ipynb
├── src/
│   ├── data/
│   │   ├── fetch_warning_letters.py      ✅ done
│   │   └── fetch_inspections.py          ✅ done (not usable — needs headless browser)
│   ├── features/
│   │   └── build_features.py             (D3)
│   ├── models/
│   │   └── train.py                      (D4)
│   └── utils/
│       └── entity_resolution.py          (D2-D3)
├── dags/
│   ├── data_ingestion_dag.py             (D6)
│   ├── feature_pipeline_dag.py           (D6)
│   ├── model_retrain_dag.py              (D6)
│   └── scoring_dag.py                    (D6)
├── data/
│   ├── raw/                              ✅ populated
│   └── processed/                        (D3)
├── reports/
│   └── report.md                         (D6)
├── docs/
│   ├── 00_project_plan.md                ✅ this file
│   └── 01_data_collection.md             ✅ done
├── docker-compose.yml                    (D6)
├── pyproject.toml                        ✅ done
└── README.md                             (D7)
```

---

## Resume context for new sessions

If continuing this project in a new Claude session, key facts:

- **Working directory**: `/Users/SANTIDO/Code/qualifyze-case-study`
- **Git config**: personal account (santiago.dominguezc@outlook.es), NOT Mercedes-Benz
- **Environment**: managed with `uv`, Python 3.12
- **Data already downloaded**: all 5 files in `data/raw/` (see `docs/01_data_collection.md`)
- **Next step**: D2 — EDA notebook + entity resolution
- **Important**: the inspections dataset is NOT comprehensive (acknowledged limitation)
- **User preference**: documentation and plan in English, conversation in Spanish
