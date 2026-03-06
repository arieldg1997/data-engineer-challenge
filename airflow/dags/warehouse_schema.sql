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

CREATE INDEX IF NOT EXISTS idx_fact_order_timestamp
    ON dw.fact_order_item(order_timestamp);

CREATE INDEX IF NOT EXISTS idx_fact_product_id
    ON dw.fact_order_item(product_id);

CREATE INDEX IF NOT EXISTS idx_fact_date_key
    ON dw.fact_order_item(date_key);

CREATE INDEX IF NOT EXISTS idx_fact_hour_of_day
    ON dw.fact_order_item(hour_of_day);