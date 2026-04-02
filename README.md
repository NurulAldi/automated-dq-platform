# Automated Data Quality Platform

## Overview
This repository contains an end-to-end Automated Data Quality (DQ) Platform built with **Apache Airflow**, **dbt (Data Build Tool)**, **Google BigQuery**, and **Looker Studio**. The project simulates a daily batch data ingestion process, enforces data quality checks, and automatically cleanses bad data upon failure. If anomalies are detected, an alert is sent directly to a Slack channel via a webhook, the corrupted data is automated wiped out, and the clean data is finally transformed and modeled for visualization in Looker Studio.

## Architecture & Technologies
- **Apache Airflow (v3.1.8+)**: Orchestrates the daily workflow, managing task dependencies and scheduling.
- **dbt (Data Build Tool)**: Handles data transformation and rigorous data quality testing inside the data warehouse.
- **Google BigQuery**: Serves as the cloud data warehouse where both raw data and aggregated/transformed metrics reside.
- **Pandas**: Used inside the ingestion script to generate, manipulate, and load dummy datasets directly into BigQuery.
- **Docker & Docker Compose**: Containerizes the entire Airflow stack (Webserver, Scheduler, Celery Workers, Redis, Postgres) for reproducible local development.
- **Slack Webhook**: Provides real-time alerting for data quality check failures.
- **Looker Studio**: Connects to the final transformed dbt models (e.g., `stg.orders`) to visualize the verified, clean data (1000 valid rows).

## Workflow Description
1. **Data Ingestion (`ingest_raw_data`)**: A python script (`ingest_data.py`) runs via an Airflow `BashOperator`. It generates 1000 rows of valid daily order records alongside 10 deliberately corrupted records (e.g., negative prices, null values) and loads them into a BigQuery dataset (`raw_data.daily_orders`) for a total of 1010 rows.
2. **Data Quality Checks (`dbt_test`)**: dbt first runs predefined validation tests (schema tests, custom data tests) to catch anomalies such as nulls or negative revenue in the raw data.
3. **Automated Alerting (`on_failure_callback`)**: If `dbt_test` fails, Airflow immediately triggers an automated alert to a configured Slack channel reporting the incident.
4. **Automated Data Cleansing (`clean_bad_data`)**: If the `dbt_test` fails due to bad data, this automated task is triggered to clean the raw data in BigQuery by executing a query to delete records with negative or null values.
5. **Data Transformation (`dbt_run`)**: After the data passes the quality checks (or is automatically cleansed by `clean_bad_data`), dbt performs transformations to model the data into its final state (e.g., `stg.orders`).
6. **Data Visualization (Looker Studio)**: Looker Studio is connected to the transformed dbt dataset (`stg.orders`) to seamlessly visualize the final 1000 rows of filtered, clean data.

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
    PUBLIC_AIRFLOW_URL=http://airflow.your-company.com:8080
    ```

### 3. Running the Platform
Simply bring up the Airflow cluster using Docker Compose:
```bash
docker-compose up -d
```
Access the Airflow Web UI at `http://localhost:8080` (default credentials: `airflow` / `airflow`). Enable the `automated_data_quality_pipeline` DAG to observe the end-to-end ingestion, dbt transformations, and automated Slack alerts upon failure.

### 4. Optional: Public Log URL for Slack Alerts
By default, the Slack alerts will generate log URLs pointing to `http://localhost:8080`. If your Airflow server is running remotely (e.g., in an EC2 instance or remote VM) and you want your team to access the logs over the internet, you can easily configure it via the `.env` file.

Simply set the `PUBLIC_AIRFLOW_URL` in your `.env` file to your instance's public IP or domain (e.g., `PUBLIC_AIRFLOW_URL=http://192.168.1.100:8080`). The DAG will automatically replace the `localhost` section in the Slack alert with your public URL. If it's left blank or missing, it will safely fallback to the local host.
