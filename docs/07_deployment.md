# Phase 7: Deployment & CI/CD

## Plan

| Step | Status |
|------|--------|
| Streamlit app for interactive risk assessment | Done |
| Deploy to Azure App Service (free tier) | Done |
| GitHub Actions CI (tests on every PR) | Done |
| Deploy workflow triggers only after CI passes | Done |
| Branch protection on main (requires PR + tests) | Done |
| Airflow DAGs for pipeline orchestration | Done (local only) |
| Selenium automation for FDA Dashboard downloads | Done |

## Architecture

```
GitHub (repo público)
    │
    ├── PR → CI workflow (pytest) → must pass to merge
    │
    └── Merge to main → CI passes → Deploy workflow → Azure App Service
                                                          │
                                                          ▼
                                            https://qualifyze-risk-xxx.azurewebsites.net
                                            (Streamlit app — interactive risk scoring)


Local (demo):
    docker-compose up → Airflow UI (localhost:8080)
                        ├── data_ingestion_dag (weekly)
                        ├── feature_pipeline_dag (triggered)
                        ├── model_retrain_dag (monthly)
                        └── scoring_dag (weekly)
```

## Streamlit App

- **URL**: https://qualifyze-risk-gubrdrhng5gka8d4.spaincentral-01.azurewebsites.net
- **Features**:
  - Enter a FEI number → get risk score + tier (Low/Medium/High/Critical)
  - SHAP-based risk drivers explanation for each prediction
  - Facility profile and inspection history
  - Example FEI numbers provided for demo
- **Stack**: Streamlit on Azure App Service Free (F1), Python 3.12

## CI/CD Pipeline

```
Developer creates branch
    → Push to GitHub
    → Open PR
    → CI workflow runs pytest (tests/test_features.py + tests/test_model.py)
    → Tests must pass to merge (branch protection)
    → Merge to main
    → CI runs again on main
    → If CI passes → Deploy workflow triggers
    → Azure App Service updates automatically
```

## Tests

| Test file | What it validates |
|---|---|
| `test_features.py` | Dataset integrity, no leakage, correct columns, OAI rate in range, temporal split |
| `test_model.py` | Model loads, has features list, metrics above threshold, predictions are valid probabilities |

## Data ingestion automation

All data sources now fully automated:

| Dataset | Script | Method |
|---|---|---|
| Warning letters | `fetch_warning_letters.py` | FDA.gov datatables API (paginated) |
| Enforcement/Recalls | `fetch_enforcement.py` | openFDA bulk JSON download |
| Inspections, Citations, 483s | `fetch_dashboard.py` | Selenium headless Chrome (Qlik Sense) |
| All at once | `fetch_all.py` | Orchestrator calling all three |

## Production recommendations (mentioned in presentation)

- **Airflow**: Azure Data Factory or managed Airflow (Astronomer/Cloud Composer) in production
- **Model registry**: MLflow for versioning, metrics tracking, and model promotion
- **Monitoring**: Track prediction distribution drift weekly, alert on deviation
- **Scaling**: Azure App Service B1+ tier for real traffic; batch scoring via Azure Functions
