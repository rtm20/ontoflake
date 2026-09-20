"""Seeded synthetic supply-chain data generator. Stdlib only. Writes CSVs to data/out/."""
import csv
import os
import random
from datetime import date, timedelta

SEED = 42
OUT = os.path.join(os.path.dirname(__file__), "out")
START = date(2025, 1, 1)
END = date(2026, 6, 30)
DAYS = (END - START).days

rng = random.Random(SEED)

REGIONS = {
    "NA": ["US", "CA", "MX"],
    "EMEA": ["DE", "FR", "PL", "TR"],
    "APAC": ["IN", "CN", "JP", "TH"],
    "LATAM": ["BR", "AR"],
}
COUNTRY_REGION = {c: r for r, cs in REGIONS.items() for c in cs}

CATEGORIES = {
    "Powertrain": ["Castings", "Forgings", "Bearings"],
    "Electrical": ["Harnesses", "Sensors", "Controllers"],
    "Hydraulics": ["Pumps", "Valves", "Hoses"],
    "Structures": ["Fabrications", "Fasteners", "Sheet Metal"],
}
COMMODITY_CATEGORY = {c: cat for cat, cs in CATEGORIES.items() for c in cs}

CARRIERS = [
    ("C01", "Maersk", "OCEAN", "STANDARD"), ("C02", "DHL Global", "AIR", "EXPRESS"),
    ("C03", "DB Schenker", "ROAD", "STANDARD"), ("C04", "Kuehne+Nagel", "OCEAN", "ECONOMY"),
    ("C05", "FedEx Freight", "ROAD", "EXPRESS"), ("C06", "Blue Dart", "AIR", "STANDARD"),
    ("C07", "Concor Rail", "RAIL", "ECONOMY"),
]

PLANTS = [
    ("P100", "Waterloo Works", "US", "MANUFACTURING"), ("P200", "Mannheim Plant", "DE", "MANUFACTURING"),
    ("P300", "Pune Works", "IN", "MANUFACTURING"), ("P400", "Tianjin Plant", "CN", "MANUFACTURING"),
    ("P500", "Horizontina Plant", "BR", "MANUFACTURING"), ("P600", "Bangkok DC", "TH", "DISTRIBUTION"),
]


def d(days_from_start):
    return START + timedelta(days=days_from_start)


def rand_date(lo=0, hi=DAYS):
    return d(rng.randint(lo, hi))


def write(name, header, rows):
    os.makedirs(OUT, exist_ok=True)
    with open(os.path.join(OUT, f"{name}.csv"), "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f)
        w.writerow(header)
        w.writerows(rows)
    print(f"{name:24s} {len(rows):>8,d} rows")


def gen_suppliers(n=60):
    rows = []
    for i in range(1, n + 1):
        country = rng.choice(list(COUNTRY_REGION))
        commodity = rng.choice(list(COMMODITY_CATEGORY))
        tier = rng.choices(["TIER1", "TIER2", "TIER3"], [0.3, 0.5, 0.2])[0]
        # Supplier quality drives OTD/defects downstream; keep as hidden attribute.
        quality = rng.betavariate(8, 2)
        rows.append(dict(
            supplier_id=f"S{i:04d}", supplier_name=f"{rng.choice(['Apex','Nordic','Sakura','Delta','Vega','Orion','Titan','Lotus'])} {commodity} {rng.choice(['GmbH','Inc','Ltd','SA','Pvt Ltd'])} {i}",
            supplier_tier=tier, supplier_country=country, supplier_region=COUNTRY_REGION[country],
            commodity_focus=commodity, risk_rating=rng.choices(["LOW", "MEDIUM", "HIGH"], [0.6, 0.3, 0.1])[0],
            _quality=quality,
        ))
    return rows


def gen_parts(n=400):
    rows = []
    for i in range(1, n + 1):
        commodity = rng.choice(list(COMMODITY_CATEGORY))
        cost = round(rng.lognormvariate(3.5, 1.0), 2)
        rows.append(dict(
            part_id=f"PN{i:05d}", part_number=f"{rng.choice(['AH','RE','AL','DZ'])}{rng.randint(100000, 999999)}",
            part_description=f"{commodity[:-1] if commodity.endswith('s') else commodity} {rng.choice(['Assy','Kit','Unit','Module'])} {i}",
            commodity=commodity, category=COMMODITY_CATEGORY[commodity], uom=rng.choice(["EA", "EA", "EA", "KG", "M"]),
            abc_class=rng.choices(["A", "B", "C"], [0.2, 0.3, 0.5])[0], standard_cost=cost,
            lifecycle_status=rng.choices(["ACTIVE", "ACTIVE", "ACTIVE", "PHASE_OUT", "NEW"], [0.7, 0.1, 0.1, 0.05, 0.05])[0],
        ))
    return rows


def gen_plants():
    return [dict(plant_id=p[0], plant_code=p[0], plant_name=p[1], plant_country=p[2], plant_region=COUNTRY_REGION[p[2]], plant_type=p[3]) for p in PLANTS]


def gen_customers(n=120):
    rows = []
    for i in range(1, n + 1):
        country = rng.choice(list(COUNTRY_REGION))
        rows.append(dict(
            customer_id=f"CU{i:04d}", customer_name=f"{rng.choice(['Prairie','Green Valley','Harvest','Sunrise','Riverbend','Highland'])} {rng.choice(['Equipment','Ag Supply','Machinery','Dealers'])} {i}",
            customer_segment=rng.choices(["DEALER", "FLEET", "GOVERNMENT", "RENTAL"], [0.6, 0.2, 0.1, 0.1])[0],
            customer_country=country, customer_region=COUNTRY_REGION[country],
            channel=rng.choices(["DIRECT", "DEALER_NETWORK", "ONLINE"], [0.3, 0.6, 0.1])[0],
        ))
    return rows


def gen_carriers():
    return [dict(carrier_id=c[0], carrier_name=c[1], transport_mode=c[2], service_level=c[3]) for c in CARRIERS]


def gen_source_list(suppliers, parts, plants):
    rows, sid = [], 0
    for part in parts:
        n_src = rng.choices([1, 2, 3], [0.55, 0.35, 0.10])[0]
        eligible = [s for s in suppliers if s["commodity_focus"] == part["commodity"]] or suppliers
        chosen = rng.sample(eligible, min(n_src, len(eligible)))
        for plant in rng.sample(plants, rng.randint(1, 3)):
            for k, sup in enumerate(chosen):
                sid += 1
                same_region = sup["supplier_region"] == plant["plant_region"]
                rows.append(dict(
                    source_id=f"SRC{sid:06d}", supplier_id=sup["supplier_id"], part_id=part["part_id"], plant_id=plant["plant_id"],
                    agreed_unit_price=round(part["standard_cost"] * rng.uniform(0.92, 1.12), 2),
                    agreed_lead_time_days=rng.randint(7, 21) if same_region else rng.randint(30, 75),
                    moq=rng.choice([1, 10, 50, 100, 500]), is_primary_source=(k == 0), currency="USD",
                ))
    return rows


def gen_po_and_shipments(source_list, suppliers, parts, n_lines=30000):
    sup_by_id = {s["supplier_id"]: s for s in suppliers}
    part_by_id = {p["part_id"]: p for p in parts}
    po_rows, ship_rows = [], []
    po_counter, ship_counter = 4500000, 8000000
    weights = [3 if s["is_primary_source"] else 1 for s in source_list]
    for i in range(n_lines):
        src = rng.choices(source_list, weights)[0]
        sup, part = sup_by_id[src["supplier_id"]], part_by_id[src["part_id"]]
        order_day = rng.randint(0, DAYS - 90)
        order_date = d(order_day)
        lt = src["agreed_lead_time_days"]
        requested_date = order_date + timedelta(days=lt)
        promised_date = requested_date + timedelta(days=rng.choice([0, 0, 0, 2, 5]))
        qty = max(src["moq"], int(rng.lognormvariate(4.5, 0.8)))
        unit_price = round(src["agreed_unit_price"] * rng.uniform(0.97, 1.06), 2)
        if i % 7 == 0:
            po_counter += 1
        po_line_id = f"POL{i + 1:07d}"
        po_rows.append(dict(
            po_line_id=po_line_id, po_number=f"{po_counter}", supplier_id=sup["supplier_id"], part_id=part["part_id"], plant_id=src["plant_id"],
            source_id=src["source_id"], order_date=order_date, requested_date=requested_date, promised_date=promised_date,
            qty_ordered=qty, unit_price=unit_price, currency="USD",
        ))
        # Supplier quality + distance drive lateness. HIGH risk suppliers are systematically late.
        q = sup["_quality"] - (0.25 if sup["risk_rating"] == "HIGH" else 0.0)
        n_ship = 1 if rng.random() < 0.85 else 2
        remaining = qty
        for s in range(n_ship):
            ship_counter += 1
            qty_shipped = remaining if s == n_ship - 1 else int(remaining * rng.uniform(0.4, 0.7))
            remaining -= qty_shipped
            late_days = 0 if rng.random() < q else int(rng.expovariate(1 / 6)) + 1
            delivery_date = promised_date + timedelta(days=late_days - (rng.choice([0, 1, 2]) if late_days == 0 else 0))
            transit = max(2, int(lt * rng.uniform(0.2, 0.5)))
            ship_date = delivery_date - timedelta(days=transit)
            rejected = int(qty_shipped * rng.betavariate(1, 60)) if rng.random() < 0.3 else 0
            received = qty_shipped - rejected
            mode_carrier = rng.choice(CARRIERS)
            base_value = received * unit_price
            plant_country = next(p[2] for p in PLANTS if p[0] == src["plant_id"])
            freight = round(base_value * rng.uniform(0.02, 0.08) * (2.5 if mode_carrier[2] == "AIR" else 1.0), 2)
            duty = round(base_value * rng.uniform(0.0, 0.12), 2) if sup["supplier_country"] != plant_country else 0.0
            ship_rows.append(dict(
                shipment_id=f"SH{ship_counter}", po_line_id=po_line_id, carrier_id=mode_carrier[0], ship_date=ship_date, delivery_date=delivery_date,
                qty_shipped=qty_shipped, qty_received=received, qty_rejected=rejected,
                freight_cost=freight, duty_cost=duty, insurance_cost=round(base_value * 0.004, 2), handling_cost=round(rng.uniform(15, 120), 2),
                status="RECEIVED" if delivery_date <= END else "IN_TRANSIT",
            ))
    return po_rows, ship_rows


def gen_sales_orders(parts, plants, customers, n_lines=50000):
    rows, so_counter = [], 9100000
    for i in range(n_lines):
        part, plant, cust = rng.choice(parts), rng.choice(plants), rng.choice(customers)
        order_day = rng.randint(0, DAYS - 30)
        order_date = d(order_day)
        requested_date = order_date + timedelta(days=rng.randint(3, 21))
        qty = max(1, int(rng.lognormvariate(2.5, 0.9)))
        # Fill-rate: C-class and PHASE_OUT parts short more often.
        short_p = 0.08 + (0.10 if part["abc_class"] == "C" else 0) + (0.15 if part["lifecycle_status"] == "PHASE_OUT" else 0)
        qty_shipped = qty if rng.random() > short_p else int(qty * rng.uniform(0.0, 0.9))
        late = rng.random() < (0.12 if plant["plant_type"] == "MANUFACTURING" else 0.06)
        ship_date = requested_date + timedelta(days=(rng.randint(1, 10) if late else -rng.randint(3, 10)))
        delivery_date = ship_date + timedelta(days=rng.randint(1, 3))
        if i % 4 == 0:
            so_counter += 1
        rows.append(dict(
            so_line_id=f"SOL{i + 1:07d}", so_number=f"{so_counter}", customer_id=cust["customer_id"], part_id=part["part_id"], plant_id=plant["plant_id"],
            carrier_id=rng.choice(CARRIERS)[0], order_date=order_date, requested_date=requested_date, qty_ordered=qty, qty_shipped=qty_shipped,
            unit_price=round(part["standard_cost"] * rng.uniform(1.25, 1.8), 2), ship_date=ship_date if qty_shipped > 0 else None,
            delivery_date=delivery_date if qty_shipped > 0 else None,
        ))
    return rows


def gen_inventory(parts, plants, so_lines):
    # Trailing-90-day demand per plant-part from sales order lines, evaluated at each month end.
    demand = {}
    for r in so_lines:
        demand.setdefault((r["plant_id"], r["part_id"]), []).append((r["order_date"], r["qty_shipped"]))
    rows = []
    m = date(START.year, START.month, 1)
    month_ends = []
    while m <= END:
        nm = date(m.year + (m.month == 12), (m.month % 12) + 1, 1)
        month_ends.append(nm - timedelta(days=1))
        m = nm
    for snap in month_ends:
        for plant in plants:
            for part in parts:
                hist = demand.get((plant["plant_id"], part["part_id"]), [])
                d90 = sum(q for dt, q in hist if snap - timedelta(days=90) < dt <= snap) / 90.0
                if d90 == 0 and rng.random() < 0.6:
                    continue
                target_days = rng.uniform(20, 75)
                on_hand = int(max(0, d90 * target_days * rng.uniform(0.5, 1.6)))
                rows.append(dict(
                    snapshot_date=snap, plant_id=plant["plant_id"], part_id=part["part_id"], qty_on_hand=on_hand,
                    unit_cost=round(part["standard_cost"] * rng.uniform(0.98, 1.04), 2),
                    avg_daily_demand_qty=round(d90, 4), safety_stock_qty=int(d90 * 14),
                ))
    return rows


def main():
    suppliers = gen_suppliers()
    parts = gen_parts()
    plants = gen_plants()
    customers = gen_customers()
    carriers = gen_carriers()
    source_list = gen_source_list(suppliers, parts, plants)
    po_lines, shipments = gen_po_and_shipments(source_list, suppliers, parts)
    so_lines = gen_sales_orders(parts, plants, customers)
    inventory = gen_inventory(parts, plants, so_lines)

    def dump(name, rows):
        cols = [c for c in rows[0].keys() if not c.startswith("_")]
        write(name, cols, [[r[c] for c in cols] for r in rows])

    dump("supplier", suppliers)
    dump("part", parts)
    dump("plant", plants)
    dump("customer", customers)
    dump("carrier", carriers)
    dump("source_list", source_list)
    dump("purchase_order_line", po_lines)
    dump("inbound_shipment", shipments)
    dump("sales_order_line", so_lines)
    dump("inventory_position", inventory)


if __name__ == "__main__":
    main()
