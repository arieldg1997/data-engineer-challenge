ORDERS_DB_CONFIG = {
    "host": "ecommerce_db1",
    "port": 5432,
    "dbname": "ecommerce_orders",
    "user": "postgres",
    "password": "postgres",
}

PRODUCTS_DB_CONFIG = {
    "host": "ecommerce_db2",
    "port": 5432,
    "dbname": "ecommerce_products",
    "user": "postgres",
    "password": "postgres",
}

WAREHOUSE_DB_CONFIG = {
    "host": "data_warehouse",
    "port": 5432,
    "dbname": "data_warehouse",
    "user": "postgres",
    "password": "postgres",
}

WAREHOUSE_SCHEMA_SQL_PATH = "/opt/airflow/dags/warehouse_schema.sql"
REPORTING_VIEWS_SQL_PATH = "/opt/airflow/dags/reporting_views.sql"