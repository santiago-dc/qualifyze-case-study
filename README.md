# Qualifyze Case Study — Supplier Non-Compliance Risk Prediction

Predictive model to assess the likelihood of future non-compliance (OAI) for FDA-regulated facilities, using publicly available data from warning letters, inspection classifications, enforcement actions, and citations.

## Results

- **ROC-AUC: 0.87** | PR-AUC: 0.37
- 80% recall at 14% precision (recommended screening threshold)
- Full SHAP-based explainability for every prediction

## Repository structure

```
├── notebooks/
│   ├── 01_eda.ipynb              # Exploratory data analysis
│   ├── 02_modeling.ipynb         # Model training and evaluation
│   └── 03_interpretability.ipynb # SHAP explanations and risk profiles
├── src/
│   ├── data/                     # Ingestion scripts (FDA API + bulk downloads)
│   ├── features/                 # Feature engineering pipeline
│   └── utils/                    # Entity resolution (fuzzy name matching)
├── dags/                         # Airflow DAGs for production orchestration
├── data/
│   ├── raw/                      # Downloaded FDA datasets
│   └── processed/                # Engineered features (parquet)
├── docs/                         # Phase-by-phase documentation
├── reports/                      # Final report + generated figures
├── docker-compose.yml            # Local Airflow setup
└── pyproject.toml                # Dependencies (managed with uv)
```

## Quick start

```bash
# Setup
uv sync

# Data ingestion (automated sources)
uv run python src/data/fetch_all.py

# Feature engineering
uv run python src/features/build_features.py

# Notebooks
uv run jupyter lab notebooks/

# Airflow (local)
docker-compose up -d
# → http://localhost:8080 (admin/admin)
```

## Data sources

| Source | Records | Link |
|---|---|---|
| FDA Inspection Classifications | 337,519 | [FDA Dashboard](https://datadashboard.fda.gov) |
| FDA Citations | 277,463 | [FDA Dashboard](https://datadashboard.fda.gov) |
| FDA Warning Letters | 3,608 | [FDA.gov](https://www.fda.gov/inspections-compliance-enforcement-and-criminal-investigations/compliance-actions-and-activities/warning-letters) |
| openFDA Enforcement | 86,419 | [openFDA](https://open.fda.gov) |
| Published Form 483s | 1,973 | [FDA Dashboard](https://datadashboard.fda.gov) |

## Key design decisions

- **Temporal validation**: train on pre-2025, test on 2025+ (no data leakage)
- **Class imbalance**: handled via `scale_pos_weight`, not SMOTE
- **Feature redundancy**: binary features (`has_*`) used only by linear models, excluded from tree models
- **Threshold**: optimized for high recall (asymmetric cost in supply chain risk)
- **Hyperparameter tuning**: RandomizedSearchCV with PR-AUC scoring and TimeSeriesSplit
