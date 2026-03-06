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

CREATE OR REPLACE VIEW dw.v_sales_by_hour AS
SELECT
    hour_of_day,
    COUNT(DISTINCT order_id) AS total_orders,
    SUM(quantity) AS units_sold,
    SUM(revenue_usd) AS revenue_usd
FROM dw.fact_order_item
GROUP BY hour_of_day;