"""
DAG: Model Retraining
Schedule: Monthly (1st of each month at 8:00 UTC)
Purpose: Retrain the model with latest data, compare with current champion,
         promote if better.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data-science",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="fda_model_retrain",
    default_args=default_args,
    description="Monthly model retraining with champion/challenger evaluation",
    schedule_interval="0 8 1 * *",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["model", "fda", "mlops"],
) as dag:

    train_challenger = BashOperator(
        task_id="train_challenger",
        bash_command="""
            python -c "
import pandas as pd
import xgboost as xgb
import joblib
from pathlib import Path
from sklearn.metrics import average_precision_score

MODEL_DIR = Path('/opt/airflow/models')
MODEL_DIR.mkdir(parents=True, exist_ok=True)

features = pd.read_parquet('/opt/airflow/data/processed/features.parquet')
features['year'] = features['inspection_date'].dt.year

# Use latest 1 year as validation, rest as train
max_year = features['year'].max()
train = features[features['year'] < max_year]
val = features[features['year'] == max_year]

FEATURES = [c for c in features.columns if c not in [
    'inspection_id', 'fei_number', 'inspection_date', 'target_oai', 'year',
    'product_type', 'country', 'project_area',
    'has_warning_letter', 'has_recall', 'has_published_483', 'pct_oai', 'pct_vai'
]]

X_train, y_train = train[FEATURES].values, train['target_oai'].values
X_val, y_val = val[FEATURES].values, val['target_oai'].values

n_neg = (y_train == 0).sum()
n_pos = (y_train == 1).sum()

model = xgb.XGBClassifier(
    n_estimators=300, max_depth=6, learning_rate=0.1,
    scale_pos_weight=n_neg / n_pos, random_state=42,
    eval_metric='aucpr', early_stopping_rounds=20,
)
model.fit(X_train, y_train, eval_set=[(X_val, y_val)], verbose=False)

y_proba = model.predict_proba(X_val)[:, 1]
pr_auc = average_precision_score(y_val, y_proba)
print(f'Challenger PR-AUC: {pr_auc:.4f}')

joblib.dump(model, MODEL_DIR / 'challenger.joblib')
joblib.dump({'pr_auc': pr_auc, 'features': FEATURES}, MODEL_DIR / 'challenger_meta.joblib')
"
        """,
    )

    evaluate_champion_vs_challenger = BashOperator(
        task_id="evaluate_champion_vs_challenger",
        bash_command="""
            python -c "
import joblib
from pathlib import Path

MODEL_DIR = Path('/opt/airflow/models')
champion_meta_path = MODEL_DIR / 'champion_meta.joblib'
challenger_meta_path = MODEL_DIR / 'challenger_meta.joblib'

challenger_meta = joblib.load(challenger_meta_path)
challenger_score = challenger_meta['pr_auc']

if champion_meta_path.exists():
    champion_meta = joblib.load(champion_meta_path)
    champion_score = champion_meta['pr_auc']
    print(f'Champion PR-AUC: {champion_score:.4f}')
    print(f'Challenger PR-AUC: {challenger_score:.4f}')
    if challenger_score > champion_score:
        print('PROMOTE: Challenger is better.')
        # Flag for promotion
        (MODEL_DIR / 'promote_challenger').touch()
    else:
        print('KEEP: Champion is still better.')
else:
    print('No champion exists. Promoting challenger.')
    (MODEL_DIR / 'promote_challenger').touch()
"
        """,
    )

    promote_if_better = BashOperator(
        task_id="promote_if_better",
        bash_command="""
            python -c "
import shutil
from pathlib import Path

MODEL_DIR = Path('/opt/airflow/models')
flag = MODEL_DIR / 'promote_challenger'

if flag.exists():
    shutil.copy(MODEL_DIR / 'challenger.joblib', MODEL_DIR / 'champion.joblib')
    shutil.copy(MODEL_DIR / 'challenger_meta.joblib', MODEL_DIR / 'champion_meta.joblib')
    flag.unlink()
    print('Champion updated.')
else:
    print('No promotion needed.')
"
        """,
    )

    train_challenger >> evaluate_champion_vs_challenger >> promote_if_better
