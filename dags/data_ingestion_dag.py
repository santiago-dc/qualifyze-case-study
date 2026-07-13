"""
DAG: FDA Data Ingestion
Schedule: Weekly (every Monday at 6:00 UTC)
Purpose: Refresh all FDA public datasets.
"""

from datetime import datetime, timedelta

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator

default_args = {
    "owner": "data-science",
    "depends_on_past": False,
    "email_on_failure": True,
    "email_on_retry": False,
    "retries": 2,
    "retry_delay": timedelta(minutes=10),
}

with DAG(
    dag_id="fda_data_ingestion",
    default_args=default_args,
    description="Weekly refresh of FDA public datasets",
    schedule_interval="0 6 * * 1",
    start_date=datetime(2025, 1, 1),
    catchup=False,
    tags=["ingestion", "fda"],
) as dag:

    fetch_warning_letters = BashOperator(
        task_id="fetch_warning_letters",
        bash_command="python /opt/airflow/src/data/fetch_warning_letters.py",
    )

    fetch_enforcement = BashOperator(
        task_id="fetch_enforcement",
        bash_command="python /opt/airflow/src/data/fetch_enforcement.py",
    )

    validate_data = BashOperator(
        task_id="validate_data",
        bash_command="""
            python -c "
import json
from pathlib import Path

raw = Path('/opt/airflow/data/raw')

# Check warning letters
with open(raw / 'warning_letters.json') as f:
    wl = json.load(f)
assert len(wl) > 3000, f'Warning letters too few: {len(wl)}'

# Check enforcement files exist and have data
for product in ['drug', 'device', 'food']:
    path = raw / f'{product}-enforcement-0001-of-0001.json'
    assert path.exists(), f'Missing: {path}'
    with open(path) as f:
        data = json.load(f)
    assert len(data['results']) > 1000, f'{product} enforcement too few'

print('Data validation passed.')
"
        """,
    )

    notify_success = BashOperator(
        task_id="notify_success",
        bash_command='echo "FDA data ingestion completed successfully at $(date)"',
    )

    [fetch_warning_letters, fetch_enforcement] >> validate_data >> notify_success
