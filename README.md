# Automated Data Quality Platform

## Overview
This repository contains an end-to-end Automated Data Quality (DQ) Platform built with **Apache Airflow**, **dbt (Data Build Tool)**, and **Google BigQuery**. The project is designed to simulate a daily batch data ingestion process, transform the raw data, and automatically enforce data quality checks. If any anomalies or bad data are detected during the pipeline execution, an alert is sent directly to a Slack channel via a webhook.

## Architecture & Technologies
- **Apache Airflow (v3.1.8+)**: Orchestrates the daily workflow, managing task dependencies and scheduling.
- **dbt (Data Build Tool)**: Handles data transformation and rigorous data quality testing inside the data warehouse.
- **Google BigQuery**: Serves as the cloud data warehouse where both raw data and aggregated/transformed metrics reside.
- **Pandas**: Used inside the ingestion script to generate, manipulate, and load dummy datasets directly into BigQuery.
- **Docker & Docker Compose**: Containerizes the entire Airflow stack (Webserver, Scheduler, Celery Workers, Redis, Postgres) for reproducible local development.
- **Slack Webhook**: Provides real-time alerting for data quality check failures.

## Workflow Description
1. **Data Ingestion (`ingest_raw_data`)**: A python script (`ingest_data.py`) runs via an Airflow `BashOperator`. It generates 1000 rows of valid daily order records alongside 10 deliberately corrupted records (e.g., negative prices, null values) and loads them into a BigQuery dataset (`raw_data.daily_orders`).
2. **Data Transformation (`dbt_run`)**: dbt connects to BigQuery to select the raw data, perform transformations, and materialize it as views/tables.
3. **Data Quality Checks (`dbt_test`)**: dbt runs predefined validation tests (schema tests, custom data tests) to catch anomalies such as nulls or negative revenue.
4. **Automated Alerting (`on_failure_callback`)**: If `dbt_test` fails, Airflow immediately triggers a callback function (`send_slack_alert`). This function captures the DAG run details, execution time, failed task ID, and log URL, pushing a formatted alert directly to a configured Slack channel.

## Project Structure
```text
.
├── config/              # Airflow configurations and GCP Service Account Key
├── dags/                # Airflow DAG definitions (e.g., data_pipeline_dag.py)
├── my_data_platform/    # dbt project directory (models, tests, profiles.yml, etc.)
├── docker-compose.yaml  # Docker setup for Airflow cluster
├── ingest_data.py       # Python script for mock data generation & BigQuery ingestion
├── requirements.txt     # Python dependencies
└── .gitignore           # Ignored files and folders (e.g., .env, venv, GCP keys)
```

## Setup and Installation

### 1. Prerequisites
- Docker and Docker Compose installed.
- Python 3.11+ installed locally (for testing outside of Docker).
- A Google Cloud Platform (GCP) Project with BigQuery enabled.
- A Slack workspace and an Incoming Webhook URL.

### 2. Configuration
1. **GCP Credentials**: Place your GCP Service Account JSON key inside `config/gcp-key.json`. This key must have permissions to manage BigQuery datasets and tables.
2. **Environment Variables**: Create a `.env` file in the root directory based on the following template:
    ```env
    AIRFLOW_UID=50000
    SLACK_WEBHOOK_URL=https://hooks.slack.com/services/YOUR/WEBHOOK/URL
    ```

### 3. Running the Platform
Simply bring up the Airflow cluster using Docker Compose:
```bash
docker-compose up -d
```
Access the Airflow Web UI at `http://localhost:8080` (default credentials: `airflow` / `airflow`). Enable the `automated_data_quality_pipeline` DAG to observe the end-to-end ingestion, dbt transformations, and automated Slack alerts upon failure.
