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

### D2 — EDA + Entity Resolution ✅ DONE

- [x] Exploratory notebook (`notebooks/01_eda.ipynb`)
- [x] Entity resolution (TF-IDF + location matching)
- [x] Document findings (`docs/02_eda_and_entity_resolution.md`)

### D3 — Preprocessing + Feature Engineering ✅ DONE

- [x] Feature pipeline (`src/features/build_features.py`)
- [x] 22 temporal features per inspection (no leakage)
- [x] Temporal split: train < 2025, test >= 2025
- [x] Saved as `data/processed/features.parquet`

### D4 — Modeling ✅ DONE

- [x] Logistic Regression baseline + XGBoost with class weights
- [x] Hyperparameter tuning (RandomizedSearchCV, PR-AUC, TimeSeriesSplit)
- [x] Ablation: removed `last_classification_oai` → model improved
- [x] Final: ROC-AUC 0.875, PR-AUC 0.376
- [x] Threshold analysis with business justification

### D5 — Interpretability ✅ DONE

- [x] SHAP global + local explanations
- [x] Dependence plots
- [x] Supplier Risk Report mockup
- [x] Stakeholder communication guidelines
- [x] Feature experiments notebook (failed attempts documented)

### D6 — Report + Slides + MLOps ✅ DONE

- [x] Report (`reports/report.md`)
- [x] Slides (`reports/presentation.pptx`)
- [x] Airflow DAGs (4 DAGs in `dags/`)
- [x] Docker Compose for local Airflow
- [x] Selenium automation for FDA Dashboard downloads

### D7 — Deployment & CI/CD ✅ DONE

- [x] Streamlit app (`app/streamlit_app.py`)
- [x] Deployed to Azure App Service (free tier)
- [x] GitHub Actions CI (pytest on PRs)
- [x] Deploy only after tests pass
- [x] Branch protection on main (requires PR)
- [x] Repo made public: https://github.com/santiago-dc/qualifyze-case-study

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
