"""
DAG: Batch Scoring
Schedule: Weekly (every Tuesday at 7:00 UTC, after ingestion on Monday)
Purpose: Generate updated risk scores for all active facilities.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data-science",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fda_batch_scoring",
    default_args=default_args,
    description="Weekly batch inference — generate risk scores for all facilities",
    schedule_interval="0 7 * * 2",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["scoring", "fda", "mlops"],
) as dag:

    generate_scores = BashOperator(
        task_id="generate_scores",
        bash_command="""
            python -c "
import pandas as pd
import joblib
from pathlib import Path
from datetime import datetime

MODEL_DIR = Path('/opt/airflow/models')
DATA_DIR = Path('/opt/airflow/data/processed')
OUTPUT_DIR = Path('/opt/airflow/data/scores')
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

# Load champion model
model = joblib.load(MODEL_DIR / 'champion.joblib')
meta = joblib.load(MODEL_DIR / 'champion_meta.joblib')
features_used = meta['features']

# Load latest features
df = pd.read_parquet(DATA_DIR / 'features.parquet')

# Score only the most recent inspection per facility
latest = df.sort_values('inspection_date').groupby('fei_number').last().reset_index()
X = latest[features_used].values

# Generate predictions
latest['risk_score'] = model.predict_proba(X)[:, 1]
latest['risk_tier'] = pd.cut(
    latest['risk_score'],
    bins=[0, 0.1, 0.3, 0.6, 1.0],
    labels=['Low', 'Medium', 'High', 'Critical']
)

# Save scored output
output = latest[['fei_number', 'product_type', 'country', 'risk_score', 'risk_tier', 'inspection_date']]
output = output.sort_values('risk_score', ascending=False)

timestamp = datetime.now().strftime('%Y%m%d')
output.to_parquet(OUTPUT_DIR / f'facility_scores_{timestamp}.parquet', index=False)
output.to_csv(OUTPUT_DIR / f'facility_scores_{timestamp}.csv', index=False)

print(f'Scored {len(output):,} facilities.')
print(f'Risk tier distribution:')
print(output['risk_tier'].value_counts())
"
        """,
    )

    export_high_risk = BashOperator(
        task_id="export_high_risk",
        bash_command="""
            python -c "
import pandas as pd
from pathlib import Path
from datetime import datetime

OUTPUT_DIR = Path('/opt/airflow/data/scores')
timestamp = datetime.now().strftime('%Y%m%d')
scores = pd.read_parquet(OUTPUT_DIR / f'facility_scores_{timestamp}.parquet')

high_risk = scores[scores['risk_tier'].isin(['High', 'Critical'])]
print(f'High/Critical risk facilities: {len(high_risk):,}')
high_risk.to_csv(OUTPUT_DIR / f'high_risk_alerts_{timestamp}.csv', index=False)
print('Exported for analyst review.')
"
        """,
    )

    generate_scores >> export_high_risk
