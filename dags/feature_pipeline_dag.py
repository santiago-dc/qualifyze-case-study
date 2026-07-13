"""
DAG: Feature Engineering Pipeline
Schedule: Triggered after data_ingestion completes (via TriggerDagRunOperator)
Purpose: Run entity resolution, build features from raw data.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.bash import BashOperator
from airflow.sensors.external_task import ExternalTaskSensor

default_args = {
    "owner": "data-science",
    "depends_on_past": False,
    "email_on_failure": True,
    "retries": 1,
    "retry_delay": timedelta(minutes=5),
}

with DAG(
    dag_id="fda_feature_pipeline",
    default_args=default_args,
    description="Entity resolution + feature engineering after data refresh",
    schedule_interval=None,
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["features", "fda"],
) as dag:

    wait_for_ingestion = ExternalTaskSensor(
        task_id="wait_for_ingestion",
        external_dag_id="fda_data_ingestion",
        external_task_id="notify_success",
        mode="poke",
        timeout=3600,
    )

    run_entity_resolution = BashOperator(
        task_id="run_entity_resolution",
        bash_command="python /opt/airflow/src/utils/entity_resolution.py",
    )

    build_features = BashOperator(
        task_id="build_features",
        bash_command="python /opt/airflow/src/features/build_features.py",
    )

    validate_features = BashOperator(
        task_id="validate_features",
        bash_command="""
            python -c "
import pandas as pd
from pathlib import Path

features = pd.read_parquet('/opt/airflow/data/processed/features.parquet')
assert len(features) > 100000, f'Features too few: {len(features)}'
assert 'target_oai' in features.columns, 'Missing target column'
assert features['target_oai'].mean() > 0.01, 'OAI rate suspiciously low'
assert features['target_oai'].mean() < 0.20, 'OAI rate suspiciously high'

print(f'Feature validation passed. {len(features):,} rows, OAI rate: {features[\"target_oai\"].mean():.4f}')
"
        """,
    )

    wait_for_ingestion >> run_entity_resolution >> build_features >> validate_features
