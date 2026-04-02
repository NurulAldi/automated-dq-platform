from airflow import DAG
from airflow.sdk import Variable
from airflow.providers.standard.operators.bash import BashOperator
from airflow.providers.standard.operators.python import PythonOperator
from airflow.task.trigger_rule import TriggerRule
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
    
    local_time = pendulum.now("Asia/Jakarta")
    exec_date_str = local_time.strftime("%Y-%m-%d")
    exec_time_str = local_time.strftime("%H:%M:%S WIB")

    log_url = task_instance.log_url
    public_url = Variable.get("PUBLIC_AIRFLOW_URL", default=None)
    if public_url:
        public_url = public_url.rstrip("/")
        if log_url.startswith("http://localhost:8080"):
            log_url = log_url.replace("http://localhost:8080", public_url)

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

def clean_bad_data_fn():
    from google.cloud import bigquery
    import logging
    client = bigquery.Client()
    query = """
    DELETE FROM `automated-dq-platform.raw_data.daily_orders`
    WHERE total_price < 0 OR total_price IS NULL
    """
    job = client.query(query)
    job.result()
    logging.info("Bad data cleaned successfully.")

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

    task_dbt_test = BashOperator(
        task_id='dbt_test',
        bash_command='cd /opt/airflow/dbt_project && dbt test --profiles-dir .'
    )

    task_clean_data = PythonOperator(
        task_id='clean_bad_data',
        python_callable=clean_bad_data_fn,
        trigger_rule=TriggerRule.ALL_FAILED
    )

    task_dbt_run = BashOperator(
        task_id='dbt_run',
        bash_command='cd /opt/airflow/dbt_project && dbt run --profiles-dir .',
        trigger_rule=TriggerRule.ONE_SUCCESS
    )

    # Workflow Branching
    task_ingest >> task_dbt_test
    
    # Path A: dbt_test succeeds -> skip clean -> run dbt_run
    task_dbt_test >> task_dbt_run
    
    # Path B: dbt_test fails -> run clean_data -> run dbt_run
    task_dbt_test >> task_clean_data >> task_dbt_run