-- 03: conformed layer. Ontology-shaped dims + facts. Facts are denormalised so every canonical metric
-- can be computed within a single fact grain (required for Semantic View metrics).
USE SCHEMA ONTOFLAKE.CONFORMED;

CREATE OR REPLACE TABLE DIM_SUPPLIER AS
SELECT supplier_id, supplier_name, supplier_tier, supplier_country, supplier_region, commodity_focus, risk_rating
FROM ONTOFLAKE.RAW.SUPPLIER;

CREATE OR REPLACE TABLE DIM_PART AS
SELECT part_id, part_number, part_description, commodity, category, uom, abc_class, standard_cost, lifecycle_status
FROM ONTOFLAKE.RAW.PART;

CREATE OR REPLACE TABLE DIM_PLANT AS
SELECT plant_id, plant_code, plant_name, plant_country, plant_region, plant_type
FROM ONTOFLAKE.RAW.PLANT;

CREATE OR REPLACE TABLE DIM_CUSTOMER AS
SELECT customer_id, customer_name, customer_segment, customer_country, customer_region, channel
FROM ONTOFLAKE.RAW.CUSTOMER;

CREATE OR REPLACE TABLE DIM_CARRIER AS
SELECT carrier_id, carrier_name, transport_mode, service_level
FROM ONTOFLAKE.RAW.CARRIER;

CREATE OR REPLACE TABLE DIM_DATE AS
SELECT d AS date_key,
       YEAR(d) AS year, QUARTER(d) AS quarter, MONTH(d) AS month, WEEKOFYEAR(d) AS week,
       TO_CHAR(d, 'YYYY-MM') AS year_month, 'Q' || QUARTER(d) || '-' || YEAR(d) AS year_quarter
FROM (SELECT DATEADD(day, SEQ4(), '2024-01-01'::DATE) d FROM TABLE(GENERATOR(ROWCOUNT => 1200)));

CREATE OR REPLACE TABLE FACT_PURCHASE_ORDER_LINE AS
SELECT pol.po_line_id, pol.po_number, pol.supplier_id, pol.part_id, pol.plant_id, pl.plant_region,
       pol.order_date, pol.requested_date, pol.promised_date, pol.qty_ordered, pol.unit_price, pol.currency,
       p.standard_cost,
       pol.qty_ordered * pol.unit_price                    AS po_line_value,
       (pol.unit_price - p.standard_cost) * pol.qty_ordered AS price_variance_value
FROM ONTOFLAKE.RAW.PURCHASE_ORDER_LINE pol
JOIN ONTOFLAKE.RAW.PART  p  ON p.part_id  = pol.part_id
JOIN ONTOFLAKE.RAW.PLANT pl ON pl.plant_id = pol.plant_id;

CREATE OR REPLACE TABLE FACT_INBOUND_SHIPMENT AS
SELECT s.shipment_id, s.po_line_id, pol.supplier_id, pol.part_id, pol.plant_id, pl.plant_region, s.carrier_id,
       pol.order_date, pol.promised_date, s.ship_date, s.delivery_date,
       pol.qty_ordered, s.qty_shipped, s.qty_received, s.qty_rejected, pol.unit_price,
       s.freight_cost, s.duty_cost, s.insurance_cost, s.handling_cost, s.status,
       s.delivery_date <= pol.promised_date                                     AS is_on_time,
       s.delivery_date <= pol.promised_date AND s.qty_received >= pol.qty_ordered AS is_on_time_in_full,
       DATEDIFF(day, pol.order_date, s.delivery_date)                            AS lead_time_days,
       DATEDIFF(day, pol.promised_date, s.delivery_date)                         AS days_late,
       s.qty_received * pol.unit_price                                           AS material_cost,
       s.qty_received * pol.unit_price + s.freight_cost + s.duty_cost + s.insurance_cost + s.handling_cost AS landed_cost
FROM ONTOFLAKE.RAW.INBOUND_SHIPMENT s
JOIN ONTOFLAKE.RAW.PURCHASE_ORDER_LINE pol ON pol.po_line_id = s.po_line_id
JOIN ONTOFLAKE.RAW.PLANT pl ON pl.plant_id = pol.plant_id;

CREATE OR REPLACE TABLE FACT_SALES_ORDER_LINE AS
SELECT sol.so_line_id, sol.so_number, sol.customer_id, sol.part_id, sol.plant_id, pl.plant_region, sol.carrier_id,
       sol.order_date, sol.requested_date, sol.ship_date, sol.delivery_date,
       sol.qty_ordered, sol.qty_shipped, sol.unit_price,
       sol.qty_ordered - sol.qty_shipped                       AS qty_backordered,
       sol.qty_shipped * sol.unit_price                        AS revenue,
       sol.delivery_date IS NOT NULL AND sol.delivery_date <= sol.requested_date AS is_on_time
FROM ONTOFLAKE.RAW.SALES_ORDER_LINE sol
JOIN ONTOFLAKE.RAW.PLANT pl ON pl.plant_id = sol.plant_id;

CREATE OR REPLACE TABLE FACT_INVENTORY_POSITION AS
SELECT MD5(inv.snapshot_date || inv.plant_id || inv.part_id) AS inventory_key,
       inv.snapshot_date, inv.plant_id, pl.plant_region, inv.part_id,
       inv.qty_on_hand, inv.unit_cost, inv.avg_daily_demand_qty, inv.safety_stock_qty,
       inv.qty_on_hand * inv.unit_cost      AS inventory_value,
       inv.qty_on_hand < inv.safety_stock_qty AS is_below_safety_stock
FROM ONTOFLAKE.RAW.INVENTORY_POSITION inv
JOIN ONTOFLAKE.RAW.PLANT pl ON pl.plant_id = inv.plant_id;

-- Primary keys are informational in Snowflake but are required metadata for Semantic View relationships.
ALTER TABLE DIM_SUPPLIER ADD PRIMARY KEY (supplier_id);
ALTER TABLE DIM_PART     ADD PRIMARY KEY (part_id);
ALTER TABLE DIM_PLANT    ADD PRIMARY KEY (plant_id);
ALTER TABLE DIM_CUSTOMER ADD PRIMARY KEY (customer_id);
ALTER TABLE DIM_CARRIER  ADD PRIMARY KEY (carrier_id);
ALTER TABLE DIM_DATE     ADD PRIMARY KEY (date_key);
ALTER TABLE FACT_PURCHASE_ORDER_LINE ADD PRIMARY KEY (po_line_id);
ALTER TABLE FACT_INBOUND_SHIPMENT    ADD PRIMARY KEY (shipment_id);
ALTER TABLE FACT_SALES_ORDER_LINE    ADD PRIMARY KEY (so_line_id);
ALTER TABLE FACT_INVENTORY_POSITION  ADD PRIMARY KEY (inventory_key);
