from airflow import DAG
from airflow.sdk import Variable
from airflow.providers.standard.operators.bash import BashOperator
from datetime import timedelta
import json
import logging
import pendulum
from urllib import request


def send_slack_alert(context):
    task_instance = context.get('task_instance')
    if task_instance is None:
        return

    task_id = task_instance.task_id
    
    if task_id != 'dbt_test':
        return

    dag_id = task_instance.dag_id
    dag_run = context.get('dag_run')
    exec_date = (
        context.get('logical_date')
        or getattr(dag_run, 'logical_date', None)
        or context.get('execution_date')
        or getattr(task_instance, 'start_date', None)
        or context.get('ts')
    )
    if hasattr(exec_date, 'strftime'):
        exec_date_str = exec_date.strftime("%Y-%m-%d")
        exec_time_str = exec_date.strftime("%H:%M:%S")
    else:
        raw_ts = str(exec_date)
        if 'T' in raw_ts:
            date_part, time_part = raw_ts.split('T', 1)
        elif ' ' in raw_ts:
            date_part, time_part = raw_ts.split(' ', 1)
        else:
            date_part, time_part = raw_ts, ""

        time_part = time_part.split('+', 1)[0].split('Z', 1)[0].strip()
        exec_date_str = date_part.strip()
        exec_time_str = time_part.strip() or "unknown"
    log_url = task_instance.log_url

    msg = f"""
    *DATA QUALITY ALERT*
    *DAG:* {dag_id}
    *FAILED TASK:* {task_id}
    *Date:* {exec_date_str}
    *Time:* {exec_time_str}
    *Check Logs:* {log_url}
    ---------------------------
    IMPORTANT!! There are negative or null data
    """

    slack_webhook_url = Variable.get("SLACK_WEBHOOK_URL")
    payload = json.dumps({"text": msg}).encode("utf-8")
    req = request.Request(
        slack_webhook_url,
        data=payload,
        headers={"Content-Type": "application/json"},
        method="POST",
    )

    try:
        with request.urlopen(req, timeout=10) as resp:
            if resp.status >= 400:
                logging.getLogger(__name__).error(
                    "Slack webhook returned status %s for task %s",
                    resp.status,
                    task_id,
                )
    except Exception:
        logging.getLogger(__name__).exception(
            "Failed sending Slack alert for DAG %s task %s", dag_id, task_id
        )

default_args = {
    'owner': 'airflow',
    'on_failure_callback': send_slack_alert,
    'retry_delay': timedelta(minutes=5)
}

with DAG(
    dag_id='automated_data_quality_pipeline',
    default_args=default_args,
    schedule='@daily',
    start_date=pendulum.datetime(2026, 3, 31, tz="UTC"),
    catchup=False
) as dag:
    
    task_ingest = BashOperator(
        task_id='ingest_raw_data',
        bash_command='python /opt/airflow/ingest_data.py'
    )

    task_dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='cd /opt/airflow/dbt_project && dbt run --profiles-dir .'
    )

    task_dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt_project && dbt test --profiles-dir .'
    )

    task_ingest >> task_dbt_run >> task_dbt_test