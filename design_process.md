# Design Process

## Setup Notes and Adjustments

While setting up the environment, a couple of issues were encountered:

- The instruction `cd data_engineer_setup` referenced in the README does not exist in the repository structure.
- The PostgreSQL instance used as the **Data Warehouse** is also used internally by Airflow (metadata tables such as `dag`, `task_instance`, etc.).

To avoid conflicts with Airflow system tables, the warehouse objects were created inside a dedicated schema:

`dw`

instead of using the default `public` schema.

---

# Exploratory Data Analysis

## Source Database 1 – Orders and Customers

Tables and schema:

| table_name  | column_name       | data_type | nullable |
| ----------- | ----------------- | --------- | -------- |
| customers   | id                | integer   | NO       |
| customers   | name              | varchar   | NO       |
| customers   | email             | varchar   | NO       |
| customers   | registration_date | timestamp | NO       |
| customers   | country           | varchar   | NO       |
| order_items | id                | integer   | NO       |
| order_items | order_id          | integer   | NO       |
| order_items | product_id        | integer   | NO       |
| order_items | quantity          | integer   | NO       |
| order_items | unit_price        | numeric   | NO       |
| order_items | currency          | varchar   | NO       |
| orders      | id                | integer   | NO       |
| orders      | customer_id       | integer   | NO       |
| orders      | order_date        | timestamp | NO       |
| orders      | total_amount      | numeric   | NO       |
| orders      | currency          | varchar   | NO       |
| orders      | status            | varchar   | NO       |

Row counts:

- **customers:** 50
- **orders:** 453
- **order_items:** 363

Observations:

- Orders contain high-level transactional data.
- Order items represent the **granularity of product sales**.
- Revenue can be recomputed from `quantity * unit_price`.
- Currency is stored per item, meaning FX conversion must be applied during transformation.

---

## Source Database 2 – Product Catalog

Table:

| table_name           | column_name | data_type | nullable |
| -------------------- | ----------- | --------- | -------- |
| product_descriptions | id          | integer   | NO       |
| product_descriptions | name        | varchar   | NO       |
| product_descriptions | category    | varchar   | NO       |
| product_descriptions | description | text      | YES      |
| product_descriptions | base_price  | numeric   | NO       |
| product_descriptions | currency    | varchar   | NO       |

Row count:

- **product_descriptions:** 100

Categories available:

- Electronics
- Pet Supplies
- Office Supplies
- Beauty & Personal Care
- Books
- Clothing
- Home & Garden
- Automotive
- Sports & Outdoors
- Toys & Games

Observations:

- Product metadata is separated from transactional data.
- This is a typical **dimension table candidate**.

---

# Design Considerations

## Modular Code Structure

The ETL implementation was structured in modular components:

- `config.py` – configuration and paths
- `db.py` – database helpers
- `fx.py` – currency conversion API
- `tasks.py` – ETL logic
- DAG definitions

This keeps the DAG definitions simple and separates orchestration from logic.

---

## Two Airflow Implementations

Two DAG implementations were created:

1. **Python-only DAG**
2. **DAG using PostgresOperator**

Both DAGs reuse the same ETL functions.

The difference is only the orchestration style:

| Approach         | Usage                                                 |
| ---------------- | ----------------------------------------------------- |
| PythonOperator   | Executes schema creation and SQL files through Python |
| PostgresOperator | Uses native Airflow operators for SQL execution       |

This demonstrates two common Airflow patterns while keeping the business logic shared.

---

# Data Warehouse Design

The warehouse follows a **star schema design**, optimized for analytics queries.

## Grain

The fact table is defined at the **order item level**.

Each row represents:

`one product in one order`

This allows accurate aggregation for:

- product performance
- revenue analysis
- time-based analysis

---

# Schema Definition

```sql
CREATE SCHEMA IF NOT EXISTS dw;

CREATE TABLE IF NOT EXISTS dw.dim_product (
    product_id BIGINT PRIMARY KEY,
    product_name TEXT,
    category TEXT,
    description TEXT
);

CREATE TABLE IF NOT EXISTS dw.dim_customer (
    customer_id BIGINT PRIMARY KEY,
    customer_name TEXT,
    email TEXT,
    country TEXT
);

CREATE TABLE IF NOT EXISTS dw.dim_date (
    date_key INT PRIMARY KEY,
    full_date DATE NOT NULL,
    year INT NOT NULL,
    month INT NOT NULL,
    day INT NOT NULL,
    day_of_week INT NOT NULL
);

CREATE TABLE IF NOT EXISTS dw.fact_order_item (
    fact_id BIGSERIAL PRIMARY KEY,
    order_id BIGINT NOT NULL,
    order_item_id BIGINT,
    customer_id BIGINT NOT NULL,
    product_id BIGINT NOT NULL,
    order_timestamp TIMESTAMP NOT NULL,
    date_key INT NOT NULL,
    hour_of_day INT NOT NULL,
    currency VARCHAR(3) NOT NULL,
    quantity NUMERIC(18,4) NOT NULL,
    unit_price NUMERIC(18,4) NOT NULL,
    revenue_native NUMERIC(18,4) NOT NULL,
    fx_rate_to_usd NUMERIC(18,8) NOT NULL,
    revenue_usd NUMERIC(18,4) NOT NULL,
    loaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,

    CONSTRAINT fk_fact_customer
        FOREIGN KEY (customer_id) REFERENCES dw.dim_customer(customer_id),

    CONSTRAINT fk_fact_product
        FOREIGN KEY (product_id) REFERENCES dw.dim_product(product_id),

    CONSTRAINT fk_fact_date
        FOREIGN KEY (date_key) REFERENCES dw.dim_date(date_key)
);
```

## Indexing Strategy

Indexes were added to optimize analytical queries.

```sql
CREATE INDEX IF NOT EXISTS idx_fact_order_timestamp
ON dw.fact_order_item(order_timestamp);

CREATE INDEX IF NOT EXISTS idx_fact_product_id
ON dw.fact_order_item(product_id);

CREATE INDEX IF NOT EXISTS idx_fact_date_key
ON dw.fact_order_item(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_hour_of_day
ON dw.fact_order_item(hour_of_day);
```

These indexes support the main analytical use cases:

- product performance
- time-based analysis
- hourly aggregation

---

# Warehouse Creation

The schema was deployed using:

```bash
docker exec -i data_warehouse psql -U postgres -d data_warehouse < warehouse_schema.sql
```

Result:

    dw.dim_customer
    dw.dim_date
    dw.dim_product
    dw.fact_order_item

---

# Airflow DAG

The pipeline is composed of the following tasks:

    create_dw_schema
            ↓
    truncate_dw_tables
            ↓
    load_dimensions
            ↓
    load_fact_order_items
            ↓
    build_reporting_views

## Responsibilities

Task Purpose

---

create_dw_schema create warehouse tables
truncate_dw_tables full refresh strategy
load_dimensions populate dimension tables
load_fact_order_items load transactional fact data
build_reporting_views create analytical views

---

# Currency Conversion

Revenue normalization is required because transactions may occur in
multiple currencies.

The pipeline calls the external API:

    https://api.exchangerate-api.com

For simplicity, conversion is performed during the ETL process.

Given the small dataset size, FX rates are retrieved per row without
caching.

In a production scenario, FX rates would likely be:

- cached
- stored in a dedicated FX table
- refreshed periodically

---

### Handling Invalid Currencies

During pipeline execution it was observed that some records contain
invalid currency codes such as:

`XYZ`

These currencies are not supported by the external exchange rate API and
would normally cause the ETL pipeline to fail with a `404` response.

To make the pipeline more robust, defensive handling was implemented in
the FX conversion function:

- If the API returns an error
- or if the currency code is unsupported

the pipeline defaults the conversion rate to:

`1.0`

This allows the pipeline to continue processing while still preserving
the original transaction values.

---

### Handling Missing Products

During pipeline execution it was observed that some `order_items`
reference product identifiers that do not exist in the product catalog.

Because the warehouse enforces referential integrity through the
constraint:

`fact_order_item.product_id → dim_product.product_id`

attempting to insert these records would cause a **foreign key
violation**.

To prevent the ETL pipeline from failing, product identifiers are
validated before inserting records into the fact table.

- If the product exists in `dim_product`, the record is inserted.
- If the product does not exist, the record is skipped.

This ensures that:

- referential integrity is preserved in the warehouse
- invalid source records do not break the pipeline
- the fact table only contains valid dimensional references

---

# Business KPIs

Two analytical views were created to answer the business questions.

## Top Performing Products

```sql
CREATE OR REPLACE VIEW dw.v_top_products AS
SELECT
    p.product_id,
    p.product_name,
    p.category,
    SUM(f.quantity) AS units_sold,
    SUM(f.revenue_usd) AS revenue_usd
FROM dw.fact_order_item f
JOIN dw.dim_product p
  ON f.product_id = p.product_id
GROUP BY p.product_id, p.product_name, p.category;
```

Provides:

- total units sold
- total revenue
- product ranking

---

## Optimal Promotion Time

```sql
CREATE OR REPLACE VIEW dw.v_sales_by_hour AS
SELECT
    hour_of_day,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(quantity) AS units_sold,
    SUM(revenue_usd) AS revenue_usd
FROM dw.fact_order_item
GROUP BY hour_of_day;
```

Provides insights about:

- peak shopping hours
- optimal promotion timing

---

# Final DAG Dependency

    create_dw_schema
          ↓
    truncate_dw_tables
          ↓
    load_dimensions
          ↓
    load_fact_order_items
          ↓
    build_reporting_views

This pipeline performs a full refresh load and produces analytics-ready
views in the warehouse.
