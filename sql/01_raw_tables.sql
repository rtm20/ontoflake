-- 01: raw tables mirror source extracts 1:1 (column order = CSV order).
USE SCHEMA ONTOFLAKE.RAW;

CREATE OR REPLACE TABLE SUPPLIER (
  supplier_id STRING, supplier_name STRING, supplier_tier STRING, supplier_country STRING, supplier_region STRING,
  commodity_focus STRING, risk_rating STRING
);
CREATE OR REPLACE TABLE PART (
  part_id STRING, part_number STRING, part_description STRING, commodity STRING, category STRING, uom STRING,
  abc_class STRING, standard_cost NUMBER(12,2), lifecycle_status STRING
);
CREATE OR REPLACE TABLE PLANT (
  plant_id STRING, plant_code STRING, plant_name STRING, plant_country STRING, plant_region STRING, plant_type STRING
);
CREATE OR REPLACE TABLE CUSTOMER (
  customer_id STRING, customer_name STRING, customer_segment STRING, customer_country STRING, customer_region STRING, channel STRING
);
CREATE OR REPLACE TABLE CARRIER (
  carrier_id STRING, carrier_name STRING, transport_mode STRING, service_level STRING
);
CREATE OR REPLACE TABLE SOURCE_LIST (
  source_id STRING, supplier_id STRING, part_id STRING, plant_id STRING, agreed_unit_price NUMBER(12,2),
  agreed_lead_time_days INT, moq INT, is_primary_source BOOLEAN, currency STRING
);
CREATE OR REPLACE TABLE PURCHASE_ORDER_LINE (
  po_line_id STRING, po_number STRING, supplier_id STRING, part_id STRING, plant_id STRING, source_id STRING,
  order_date DATE, requested_date DATE, promised_date DATE, qty_ordered INT, unit_price NUMBER(12,2), currency STRING
);
CREATE OR REPLACE TABLE INBOUND_SHIPMENT (
  shipment_id STRING, po_line_id STRING, carrier_id STRING, ship_date DATE, delivery_date DATE,
  qty_shipped INT, qty_received INT, qty_rejected INT,
  freight_cost NUMBER(12,2), duty_cost NUMBER(12,2), insurance_cost NUMBER(12,2), handling_cost NUMBER(12,2), status STRING
);
CREATE OR REPLACE TABLE SALES_ORDER_LINE (
  so_line_id STRING, so_number STRING, customer_id STRING, part_id STRING, plant_id STRING, carrier_id STRING,
  order_date DATE, requested_date DATE, qty_ordered INT, qty_shipped INT, unit_price NUMBER(12,2), ship_date DATE, delivery_date DATE
);
CREATE OR REPLACE TABLE INVENTORY_POSITION (
  snapshot_date DATE, plant_id STRING, part_id STRING, qty_on_hand INT, unit_cost NUMBER(12,2),
  avg_daily_demand_qty NUMBER(12,4), safety_stock_qty INT
);
