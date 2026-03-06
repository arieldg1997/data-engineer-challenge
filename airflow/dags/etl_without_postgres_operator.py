from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator

from scripts.tasks import (
    create_dw_schema,
    truncate_dw_tables,
    load_dimensions,
    load_fact_order_items,
    build_reporting_views,
)

default_args = {
    "owner": "Ari",
    "depends_on_past": False,
    "retries": 1,
}

with DAG(
    dag_id="etl_python_only",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["challenge", "python-only"],
) as dag:

    create_dw_schema_task = PythonOperator(
        task_id="create_dw_schema",
        python_callable=create_dw_schema,
    )

    truncate_dw_tables_task = PythonOperator(
        task_id="truncate_dw_tables",
        python_callable=truncate_dw_tables,
    )

    load_dimensions_task = PythonOperator(
        task_id="load_dimensions",
        python_callable=load_dimensions,
    )

    load_fact_order_items_task = PythonOperator(
        task_id="load_fact_order_items",
        python_callable=load_fact_order_items,
    )

    build_reporting_views_task = PythonOperator(
        task_id="build_reporting_views",
        python_callable=build_reporting_views,
    )

    create_dw_schema_task >> truncate_dw_tables_task >> load_dimensions_task >> load_fact_order_items_task >> build_reporting_views_task