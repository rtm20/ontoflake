-- Golden questions expressed against the semantic view. These are the questions every persona asks;
-- harness/consistency_check.py runs them under each persona role and asserts identical answers.
USE SCHEMA ONTOFLAKE.SEMANTIC;

-- Q1 Supplier OTD by plant region
SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN DIMENSIONS plant.plant_region METRICS shipment.supplier_otd_pct, shipment.shipment_count) ORDER BY 1;

-- Q2 Fill rate by plant
SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN DIMENSIONS plant.plant_name METRICS so_line.fill_rate_pct, so_line.backorder_qty) ORDER BY 1;

-- Q3 Days of inventory by category, latest snapshot
SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN DIMENSIONS part.category, inventory.snapshot_date METRICS inventory.days_of_inventory, inventory.inventory_value_total)
WHERE snapshot_date = (SELECT MAX(snapshot_date) FROM ONTOFLAKE.CONFORMED.FACT_INVENTORY_POSITION) ORDER BY 1;

-- Q4 Landed cost per unit by supplier region and transport mode
SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN DIMENSIONS supplier.supplier_region, carrier.transport_mode METRICS shipment.landed_cost_per_unit, shipment.freight_pct_of_landed) ORDER BY 1, 2;

-- Q5 Worst 5 suppliers by OTD (min 100 shipments)
SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN DIMENSIONS supplier.supplier_name, supplier.risk_rating METRICS shipment.supplier_otd_pct, shipment.shipment_count)
WHERE shipment_count >= 100 ORDER BY supplier_otd_pct LIMIT 5;

-- Q6 Customer OTD by month
SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN DIMENSIONS so_line.order_month METRICS so_line.customer_otd_pct, so_line.revenue_total) ORDER BY 1;

-- Q7 PO spend and PPV by category
SELECT * FROM SEMANTIC_VIEW(SUPPLY_CHAIN DIMENSIONS part.category METRICS po_line.po_spend, po_line.purchase_price_variance) ORDER BY 1;
