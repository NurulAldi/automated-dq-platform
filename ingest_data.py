import pandas as pd
import random
from google.cloud import bigquery
from datetime import datetime, timedelta
import os

PROJECT_ID = "automated-dq-platform"
DATASET_ID = "raw_data"
TABLE_NAME = "daily_orders"

client = bigquery.Client()

def ingest_data():
    now = datetime.now()

    dates = [(now - timedelta(days=i)).strftime('%Y-%m-%d') for i in range(30)]

    print("Create 1000 normal data spread across 30 days...")
    normal_data = {
        'order_id': list(range(1, 1001)),
        'customer_id': [f"CUST-{random.randint(1, 500)}" for _ in range(1000)],
        'total_price': [round(random.uniform(50.0, 1000.0), 2) for _ in range(1000)],
        'order_date': [random.choice(dates) for _ in range(1000)],
        'status': [random.choice(['completed', 'pending']) for _ in range(1000)]
    }
    df_normal = pd.DataFrame(normal_data)

    print("Create 10 broken data...")
    anomaly_order_ids = list(range(50001, 50011))

    anomaly_prices = [-99.99, -500.00, -10.5, -9999.0, -1.0, None, None, None, None, None]
    random.shuffle(anomaly_prices)

    anomaly_data = {
        'order_id': anomaly_order_ids,
        'customer_id': ['CUST-ERR'] * 10,
        'total_price': anomaly_prices,
        'order_date': [random.choice(dates) for _ in range(10)],
        'status': ['error'] * 10
    }
    df_anomaly = pd.DataFrame(anomaly_data)

    df_final = pd.concat([df_normal, df_anomaly], ignore_index=True)

    df_final = df_final.sort_values(by='order_date').reset_index(drop=True)

    table_id = f"{PROJECT_ID}.{DATASET_ID}.{TABLE_NAME}"

    print(f"Send {len(df_final)} rows to BigQuery {table_id}...")

    job_config = bigquery.LoadJobConfig(
        write_disposition="WRITE_TRUNCATE"
    )
    job = client.load_table_from_dataframe(df_final, table_id, job_config=job_config)
    job.result()

    print("Successfully Load All Data")

if __name__ == "__main__":
    ingest_data()