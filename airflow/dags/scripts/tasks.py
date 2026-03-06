from decimal import Decimal

from .config import (
    ORDERS_DB_CONFIG,
    PRODUCTS_DB_CONFIG,
    WAREHOUSE_DB_CONFIG,
    WAREHOUSE_SCHEMA_SQL_PATH,
    REPORTING_VIEWS_SQL_PATH,
)
from .db import get_connection, execute_sql_file
from .fix import get_fx_rate_to_usd


def create_dw_schema():
    conn = get_connection(WAREHOUSE_DB_CONFIG)
    try:
        execute_sql_file(conn, WAREHOUSE_SCHEMA_SQL_PATH)
    finally:
        conn.close()


def truncate_dw_tables():
    conn = get_connection(WAREHOUSE_DB_CONFIG)
    try:
        with conn.cursor() as cur:
            cur.execute("""
                TRUNCATE TABLE
                    dw.fact_order_item,
                    dw.dim_date,
                    dw.dim_customer,
                    dw.dim_product
                RESTART IDENTITY CASCADE;
            """)
        conn.commit()
    finally:
        conn.close()


def load_dimensions():
    orders_conn = get_connection(ORDERS_DB_CONFIG)
    products_conn = get_connection(PRODUCTS_DB_CONFIG)
    warehouse_conn = get_connection(WAREHOUSE_DB_CONFIG)

    try:
        with orders_conn.cursor() as orders_cur, \
             products_conn.cursor() as products_cur, \
             warehouse_conn.cursor() as wh_cur:

            orders_cur.execute("""
                SELECT id, name, email, country
                FROM customers
            """)
            customers = orders_cur.fetchall()

            for customer in customers:
                wh_cur.execute("""
                    INSERT INTO dw.dim_customer (
                        customer_id,
                        customer_name,
                        email,
                        country
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (customer_id)
                    DO UPDATE SET
                        customer_name = EXCLUDED.customer_name,
                        email = EXCLUDED.email,
                        country = EXCLUDED.country
                """, customer)

            products_cur.execute("""
                SELECT id, name, category, description
                FROM product_descriptions
            """)
            products = products_cur.fetchall()

            for product in products:
                wh_cur.execute("""
                    INSERT INTO dw.dim_product (
                        product_id,
                        product_name,
                        category,
                        description
                    )
                    VALUES (%s, %s, %s, %s)
                    ON CONFLICT (product_id)
                    DO UPDATE SET
                        product_name = EXCLUDED.product_name,
                        category = EXCLUDED.category,
                        description = EXCLUDED.description
                """, product)

        warehouse_conn.commit()

    finally:
        orders_conn.close()
        products_conn.close()
        warehouse_conn.close()


def load_fact_order_items():
    orders_conn = get_connection(ORDERS_DB_CONFIG)
    warehouse_conn = get_connection(WAREHOUSE_DB_CONFIG)

    try:
        with orders_conn.cursor() as orders_cur, \
             warehouse_conn.cursor() as wh_cur:

            wh_cur.execute("SELECT product_id FROM dw.dim_product")
            valid_product_ids = {row[0] for row in wh_cur.fetchall()}

            orders_cur.execute("""
                SELECT
                    o.id,
                    oi.id,
                    o.customer_id,
                    oi.product_id,
                    o.order_date,
                    oi.currency,
                    oi.quantity,
                    oi.unit_price
                FROM orders o
                JOIN order_items oi
                    ON o.id = oi.order_id
            """)
            rows = orders_cur.fetchall()

            for row in rows:
                (
                    order_id,
                    order_item_id,
                    customer_id,
                    product_id,
                    order_date,
                    currency,
                    quantity,
                    unit_price
                ) = row

                if product_id not in valid_product_ids:
                    continue

                quantity = Decimal(str(quantity))
                unit_price = Decimal(str(unit_price))
                revenue_native = quantity * unit_price

                date_key = int(order_date.strftime("%Y%m%d"))
                hour_of_day = order_date.hour

                wh_cur.execute("""
                    INSERT INTO dw.dim_date (
                        date_key,
                        full_date,
                        year,
                        month,
                        day,
                        day_of_week
                    )
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (date_key) DO NOTHING
                """, (
                    date_key,
                    order_date.date(),
                    order_date.year,
                    order_date.month,
                    order_date.day,
                    order_date.isoweekday()
                ))

                fx_rate = get_fx_rate_to_usd(currency)
                revenue_usd = revenue_native * fx_rate

                wh_cur.execute("""
                    INSERT INTO dw.fact_order_item (
                        order_id,
                        order_item_id,
                        customer_id,
                        product_id,
                        order_timestamp,
                        date_key,
                        hour_of_day,
                        currency,
                        quantity,
                        unit_price,
                        revenue_native,
                        fx_rate_to_usd,
                        revenue_usd
                    )
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                """, (
                    order_id,
                    order_item_id,
                    customer_id,
                    product_id,
                    order_date,
                    date_key,
                    hour_of_day,
                    currency,
                    quantity,
                    unit_price,
                    revenue_native,
                    fx_rate,
                    revenue_usd
                ))

        warehouse_conn.commit()

    finally:
        orders_conn.close()
        warehouse_conn.close()


def build_reporting_views():
    conn = get_connection(WAREHOUSE_DB_CONFIG)
    try:
        execute_sql_file(conn, REPORTING_VIEWS_SQL_PATH)
    finally:
        conn.close()