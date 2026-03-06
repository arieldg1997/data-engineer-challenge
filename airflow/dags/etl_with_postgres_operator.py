from datetime import datetime

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator

from scripts.tasks import (
    load_dimensions,
    load_fact_order_items,
)

default_args = {
    "owner": "Ari",
    "depends_on_past": False,
    "retries": 1,
}

with DAG(
    dag_id="etl_with_postgres_operator",
    default_args=default_args,
    start_date=datetime(2024, 1, 1),
    schedule_interval=None,
    catchup=False,
    tags=["challenge", "postgres-operator"],
) as dag:

    create_dw_schema_task = PostgresOperator(
        task_id="create_dw_schema",
        postgres_conn_id="warehouse_db",
        sql="warehouse_schema.sql",
    )

    truncate_dw_tables_task = PostgresOperator(
        task_id="truncate_dw_tables",
        postgres_conn_id="warehouse_db",
        sql="""
        TRUNCATE TABLE
            dw.fact_order_item,
            dw.dim_date,
            dw.dim_customer,
            dw.dim_product
        RESTART IDENTITY CASCADE;
        """,
    )

    load_dimensions_task = PythonOperator(
        task_id="load_dimensions",
        python_callable=load_dimensions,
    )

    load_fact_order_items_task = PythonOperator(
        task_id="load_fact_order_items",
        python_callable=load_fact_order_items,
    )

    build_reporting_views_task = PostgresOperator(
        task_id="build_reporting_views",
        postgres_conn_id="warehouse_db",
        sql="reporting_views.sql",
    )

    create_dw_schema_task >> truncate_dw_tables_task >> load_dimensions_task >> load_fact_order_items_task >> build_reporting_views_task