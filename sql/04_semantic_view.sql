-- 04: THE ontology as a Snowflake Semantic View. Every metric here is the single canonical definition
-- from ontology/ontology.yaml. Personas query this object, never the tables.
USE SCHEMA ONTOFLAKE.SEMANTIC;

CREATE OR REPLACE SEMANTIC VIEW SUPPLY_CHAIN
  TABLES (
    supplier  AS ONTOFLAKE.CONFORMED.DIM_SUPPLIER PRIMARY KEY (supplier_id)
      WITH SYNONYMS ('vendor', 'vendors', 'suppliers') COMMENT = 'External vendor supplying parts to plants',
    part      AS ONTOFLAKE.CONFORMED.DIM_PART     PRIMARY KEY (part_id)
      WITH SYNONYMS ('material', 'materials', 'parts', 'component', 'SKU') COMMENT = 'Purchased or manufactured material',
    plant     AS ONTOFLAKE.CONFORMED.DIM_PLANT    PRIMARY KEY (plant_id)
      WITH SYNONYMS ('site', 'factory', 'facility', 'plants', 'DC') COMMENT = 'Manufacturing or distribution site',
    customer  AS ONTOFLAKE.CONFORMED.DIM_CUSTOMER PRIMARY KEY (customer_id)
      WITH SYNONYMS ('dealer', 'account', 'customers') COMMENT = 'Dealer or end customer',
    carrier   AS ONTOFLAKE.CONFORMED.DIM_CARRIER  PRIMARY KEY (carrier_id)
      WITH SYNONYMS ('logistics provider', 'forwarder', 'carriers') COMMENT = 'Freight carrier',
    po_line   AS ONTOFLAKE.CONFORMED.FACT_PURCHASE_ORDER_LINE PRIMARY KEY (po_line_id)
      WITH SYNONYMS ('purchase order', 'PO', 'POs', 'purchase orders', 'procurement orders') COMMENT = 'Purchase order line placed by a plant with a supplier',
    shipment  AS ONTOFLAKE.CONFORMED.FACT_INBOUND_SHIPMENT PRIMARY KEY (shipment_id)
      WITH SYNONYMS ('inbound shipment', 'delivery', 'deliveries', 'receipt', 'goods receipt', 'inbound') COMMENT = 'Inbound delivery of a PO line from supplier to plant',
    so_line   AS ONTOFLAKE.CONFORMED.FACT_SALES_ORDER_LINE PRIMARY KEY (so_line_id)
      WITH SYNONYMS ('sales order', 'customer order', 'orders', 'outbound', 'demand') COMMENT = 'Customer sales order line fulfilled from a plant',
    inventory AS ONTOFLAKE.CONFORMED.FACT_INVENTORY_POSITION PRIMARY KEY (inventory_key)
      WITH SYNONYMS ('stock', 'on hand', 'inventory position', 'stock level') COMMENT = 'Month-end on-hand inventory by plant and part'
  )
  RELATIONSHIPS (
    po_line_supplier   AS po_line (supplier_id)   REFERENCES supplier,
    po_line_part       AS po_line (part_id)       REFERENCES part,
    po_line_plant      AS po_line (plant_id)      REFERENCES plant,
    shipment_supplier  AS shipment (supplier_id)  REFERENCES supplier,
    shipment_part      AS shipment (part_id)      REFERENCES part,
    shipment_plant     AS shipment (plant_id)     REFERENCES plant,
    shipment_carrier   AS shipment (carrier_id)   REFERENCES carrier,
    so_line_customer   AS so_line (customer_id)   REFERENCES customer,
    so_line_part       AS so_line (part_id)       REFERENCES part,
    so_line_plant      AS so_line (plant_id)      REFERENCES plant,
    so_line_carrier    AS so_line (carrier_id)    REFERENCES carrier,
    inventory_part     AS inventory (part_id)     REFERENCES part,
    inventory_plant    AS inventory (plant_id)    REFERENCES plant
  )
  FACTS (
    po_line.qty_ordered            AS qty_ordered,
    po_line.po_line_value          AS po_line_value,
    po_line.price_variance_value   AS price_variance_value,
    shipment.qty_received          AS qty_received,
    shipment.qty_rejected          AS qty_rejected,
    shipment.qty_ordered           AS qty_ordered,
    shipment.on_time_qty           AS IFF(shipment.is_on_time, shipment.qty_received, 0),
    shipment.otif_flag             AS IFF(shipment.is_on_time_in_full, 1, 0),
    shipment.lead_time_days        AS lead_time_days,
    shipment.landed_cost           AS landed_cost,
    shipment.material_cost         AS material_cost,
    shipment.freight_cost          AS freight_cost,
    shipment.duty_cost             AS duty_cost,
    so_line.qty_ordered            AS qty_ordered,
    so_line.qty_shipped            AS qty_shipped,
    so_line.qty_backordered        AS qty_backordered,
    so_line.revenue                AS revenue,
    so_line.on_time_qty            AS IFF(so_line.is_on_time, so_line.qty_shipped, 0),
    inventory.qty_on_hand          AS qty_on_hand,
    inventory.avg_daily_demand_qty AS avg_daily_demand_qty,
    inventory.inventory_value      AS inventory_value,
    inventory.below_ss_flag        AS IFF(inventory.is_below_safety_stock, 1, 0)
  )
  DIMENSIONS (
    supplier.supplier_name    AS supplier_name    WITH SYNONYMS ('vendor name'),
    supplier.supplier_tier    AS supplier_tier,
    supplier.supplier_country AS supplier_country,
    supplier.supplier_region  AS supplier_region  WITH SYNONYMS ('vendor region', 'source region'),
    supplier.risk_rating      AS risk_rating      WITH SYNONYMS ('supplier risk'),
    part.part_number          AS part_number      WITH SYNONYMS ('material number', 'SKU'),
    part.part_description     AS part_description,
    part.commodity            AS commodity,
    part.category             AS category         WITH SYNONYMS ('part category', 'product category'),
    part.abc_class            AS abc_class,
    part.lifecycle_status     AS lifecycle_status,
    plant.plant_code          AS plant_code,
    plant.plant_name          AS plant_name       WITH SYNONYMS ('site name', 'factory'),
    plant.plant_country       AS plant_country,
    plant.plant_region        AS plant_region     WITH SYNONYMS ('region', 'site region', 'receiving region'),
    plant.plant_type          AS plant_type,
    customer.customer_name    AS customer_name    WITH SYNONYMS ('dealer name'),
    customer.customer_segment AS customer_segment,
    customer.customer_region  AS customer_region,
    customer.channel          AS channel,
    carrier.carrier_name      AS carrier_name,
    carrier.transport_mode    AS transport_mode   WITH SYNONYMS ('mode', 'shipping mode'),
    po_line.order_date        AS order_date,
    po_line.order_month       AS TO_CHAR(po_line.order_date, 'YYYY-MM') WITH SYNONYMS ('PO month'),
    shipment.delivery_date    AS delivery_date,
    shipment.delivery_month   AS TO_CHAR(shipment.delivery_date, 'YYYY-MM') WITH SYNONYMS ('receipt month', 'month received'),
    shipment.delivery_quarter AS 'Q' || QUARTER(shipment.delivery_date) || '-' || YEAR(shipment.delivery_date),
    shipment.delivery_year    AS YEAR(shipment.delivery_date),
    so_line.requested_date    AS requested_date,
    so_line.order_month       AS TO_CHAR(so_line.order_date, 'YYYY-MM') WITH SYNONYMS ('sales month', 'demand month'),
    so_line.order_year        AS YEAR(so_line.order_date),
    inventory.snapshot_date   AS snapshot_date    WITH SYNONYMS ('as of date', 'stock date'),
    inventory.snapshot_month  AS TO_CHAR(inventory.snapshot_date, 'YYYY-MM')
  )
  METRICS (
    -- Procurement
    shipment.supplier_otd_pct          AS 100 * SUM(shipment.on_time_qty) / NULLIF(SUM(shipment.qty_received), 0)
      WITH SYNONYMS ('supplier on time delivery', 'inbound OTD', 'vendor OTD', 'on-time delivery rate')
      COMMENT = 'Quantity-weighted % of received quantity delivered on or before the PO promised date',
    shipment.supplier_otif_pct         AS 100 * SUM(shipment.otif_flag) / NULLIF(COUNT(shipment.shipment_id), 0)
      WITH SYNONYMS ('OTIF', 'on time in full') COMMENT = '% of inbound shipments that were on time AND received in full',
    shipment.landed_cost_total         AS SUM(shipment.landed_cost)
      WITH SYNONYMS ('total landed cost', 'landed cost') COMMENT = 'Material + freight + duty + insurance + handling',
    shipment.landed_cost_per_unit      AS SUM(shipment.landed_cost) / NULLIF(SUM(shipment.qty_received), 0)
      WITH SYNONYMS ('unit landed cost', 'landed cost per piece') COMMENT = 'Total landed cost divided by received quantity',
    shipment.freight_pct_of_landed     AS 100 * SUM(shipment.freight_cost) / NULLIF(SUM(shipment.landed_cost), 0)
      COMMENT = 'Freight share of landed cost',
    shipment.supplier_defect_rate_pct  AS 100 * SUM(shipment.qty_rejected) / NULLIF(SUM(shipment.qty_received + shipment.qty_rejected), 0)
      WITH SYNONYMS ('defect rate', 'rejection rate', 'PPM quality') COMMENT = '% of delivered quantity rejected at receipt',
    shipment.avg_lead_time_days        AS AVG(shipment.lead_time_days)
      WITH SYNONYMS ('lead time', 'actual lead time', 'PO to receipt days') COMMENT = 'Average days from PO order date to delivery',
    shipment.received_qty              AS SUM(shipment.qty_received),
    shipment.shipment_count            AS COUNT(shipment.shipment_id) WITH SYNONYMS ('number of deliveries', 'inbound shipments'),
    po_line.po_spend                   AS SUM(po_line.po_line_value)
      WITH SYNONYMS ('spend', 'purchase spend', 'procurement spend', 'PO value') COMMENT = 'Ordered quantity x PO unit price',
    po_line.purchase_price_variance    AS SUM(po_line.price_variance_value)
      WITH SYNONYMS ('PPV', 'price variance') COMMENT = '(PO unit price - standard cost) x ordered quantity; positive = paying above standard',
    po_line.po_line_count              AS COUNT(po_line.po_line_id) WITH SYNONYMS ('number of PO lines'),
    -- Logistics
    so_line.customer_otd_pct           AS 100 * SUM(so_line.on_time_qty) / NULLIF(SUM(so_line.qty_shipped), 0)
      WITH SYNONYMS ('customer on time delivery', 'outbound OTD', 'delivery performance', 'on time to customer')
      COMMENT = 'Quantity-weighted % of shipped quantity delivered on or before the customer requested date',
    so_line.backorder_qty              AS SUM(so_line.qty_backordered)
      WITH SYNONYMS ('backorders', 'open backorder', 'shortage quantity') COMMENT = 'Ordered minus shipped quantity',
    so_line.revenue_total              AS SUM(so_line.revenue) WITH SYNONYMS ('sales', 'revenue'),
    -- Planning
    so_line.fill_rate_pct              AS 100 * SUM(so_line.qty_shipped) / NULLIF(SUM(so_line.qty_ordered), 0)
      WITH SYNONYMS ('fill rate', 'order fill', 'line fill rate', 'service level')
      COMMENT = 'First-pass fill: shipped quantity as % of ordered quantity; backorders do not count as filled',
    inventory.days_of_inventory        AS SUM(inventory.qty_on_hand) / NULLIF(SUM(inventory.avg_daily_demand_qty), 0)
      WITH SYNONYMS ('DOI', 'days of supply', 'DOS', 'inventory days', 'days on hand')
      COMMENT = 'On-hand quantity divided by trailing-90-day average daily demand quantity',
    inventory.inventory_value_total    AS SUM(inventory.inventory_value)
      WITH SYNONYMS ('stock value', 'inventory valuation', 'inventory dollars') COMMENT = 'On-hand quantity x unit cost',
    inventory.on_hand_qty              AS SUM(inventory.qty_on_hand) WITH SYNONYMS ('stock quantity', 'units on hand'),
    inventory.below_safety_stock_pct   AS 100 * SUM(inventory.below_ss_flag) / NULLIF(COUNT(inventory.inventory_key), 0)
      WITH SYNONYMS ('stockout risk', 'below safety stock') COMMENT = '% of plant-part positions below safety stock'
  )
  COMMENT = 'OntoFlake supply chain ontology v0.1.0. Canonical definitions for OTD, fill rate, DOI, landed cost. Source: ontology/ontology.yaml';

SHOW SEMANTIC VIEWS IN SCHEMA ONTOFLAKE.SEMANTIC;
