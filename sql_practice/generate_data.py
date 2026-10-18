"""Generates 01_schema_and_data.sql deterministically (seeded). Run: python generate_data.py"""
import random
from datetime import date, timedelta

random.seed(42)
out: list[str] = []

SCHEMA = """
-- Portable SQL (PostgreSQL / SQLite / most engines). Dates are ISO strings 'YYYY-MM-DD'.
DROP TABLE IF EXISTS order_items;
DROP TABLE IF EXISTS orders;
DROP TABLE IF EXISTS products;
DROP TABLE IF EXISTS customers;
DROP TABLE IF EXISTS activity;
DROP TABLE IF EXISTS raw_events;
DROP TABLE IF EXISTS employees;
DROP TABLE IF EXISTS dim_customer_scd;
DROP TABLE IF EXISTS stg_customer_changes;

CREATE TABLE customers (
  customer_id INTEGER PRIMARY KEY, name VARCHAR(50) NOT NULL,
  country VARCHAR(20) NOT NULL, signup_date DATE NOT NULL);
CREATE TABLE products (
  product_id INTEGER PRIMARY KEY, name VARCHAR(50) NOT NULL,
  category VARCHAR(20) NOT NULL, price DECIMAL(10,2) NOT NULL);
CREATE TABLE orders (
  order_id INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL REFERENCES customers(customer_id),
  order_date DATE NOT NULL, status VARCHAR(10) NOT NULL);  -- completed | cancelled | returned
CREATE TABLE order_items (
  order_id INTEGER NOT NULL REFERENCES orders(order_id),
  product_id INTEGER NOT NULL REFERENCES products(product_id),
  quantity INTEGER NOT NULL, unit_price DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (order_id, product_id));
CREATE TABLE activity (customer_id INTEGER NOT NULL, day_no INTEGER NOT NULL);  -- one row per active day
CREATE TABLE raw_events (
  event_id INTEGER NOT NULL, customer_id INTEGER NOT NULL, event_type VARCHAR(20) NOT NULL,
  amount DECIMAL(10,2), updated_at TIMESTAMP NOT NULL);  -- contains duplicates per event_id
CREATE TABLE employees (emp_id INTEGER PRIMARY KEY, name VARCHAR(30) NOT NULL, manager_id INTEGER);
CREATE TABLE dim_customer_scd (
  customer_key INTEGER PRIMARY KEY, customer_id INTEGER NOT NULL, country VARCHAR(20) NOT NULL,
  valid_from DATE NOT NULL, valid_to DATE, is_current INTEGER NOT NULL);
CREATE TABLE stg_customer_changes (customer_id INTEGER NOT NULL, new_country VARCHAR(20) NOT NULL, change_date DATE NOT NULL);
"""
out.append(SCHEMA.strip() + "\n")

def ins(table, rows):
    for r in rows:
        vals = ", ".join("NULL" if v is None else (f"'{v}'" if isinstance(v, str) else str(v)) for v in r)
        out.append(f"INSERT INTO {table} VALUES ({vals});")
    out.append("")

countries = ["Germany", "Austria", "Switzerland", "France"]
names = ["Anna", "Ben", "Clara", "David", "Emma", "Felix", "Greta", "Hannes", "Ida", "Jonas",
         "Klara", "Lukas", "Mia", "Noah", "Olivia"]
customers = [(i + 1, n, countries[i % 4] if i % 5 else "Germany", (date(2024, 1, 1) + timedelta(days=25 * i)).isoformat())
             for i, n in enumerate(names)]
ins("customers", customers)

products = [
    (1, "Laptop", "Electronics", 999.00), (2, "Headphones", "Electronics", 149.50),
    (3, "Monitor", "Electronics", 289.00), (4, "Desk", "Furniture", 349.00),
    (5, "Chair", "Furniture", 199.00), (6, "Notebook", "Stationery", 4.50),
    (7, "Pen Set", "Stationery", 12.90), (8, "Backpack", "Accessories", 59.00),
]
ins("products", products)

orders, items = [], []
statuses = ["completed"] * 8 + ["cancelled", "returned"]
oid = 0
for cust in range(1, 14):          # customers 14 and 15 never order (exercise 2)
    for _ in range(random.randint(2, 5)):
        oid += 1
        d = date(2025, 1, 1) + timedelta(days=random.randint(0, 150))
        orders.append((oid, cust, d.isoformat(), random.choice(statuses)))
        for pid in random.sample(range(1, 8), random.randint(1, 3)):  # product 8 is never sold (exercise 20)
            price = next(p[3] for p in products if p[0] == pid)
            items.append((oid, pid, random.randint(1, 3), price))
orders.sort(key=lambda r: (r[2], r[0]))
ins("orders", orders)
ins("order_items", items)

activity = []
for cust, days in {1: [1, 2, 3, 5, 6, 7, 8, 9, 20], 2: [4, 5, 6, 10], 3: [1, 3, 5, 7], 4: list(range(10, 16))}.items():
    activity += [(cust, d) for d in days]
ins("activity", activity)

events = [
    (1, 1, "purchase", 50.00, "2025-03-01 10:00:00"), (1, 1, "purchase", 55.00, "2025-03-01 12:00:00"),
    (2, 2, "refund", 20.00, "2025-03-02 09:00:00"),
    (3, 3, "purchase", 80.00, "2025-03-02 11:00:00"), (3, 3, "purchase", 80.00, "2025-03-02 11:00:00"),
    (3, 3, "purchase", 85.00, "2025-03-03 08:00:00"),
    (4, 1, "purchase", 10.00, "2025-03-04 15:30:00"),
]
ins("raw_events", events)

emps = [(1, "Dora (CEO)", None), (2, "Elias", 1), (3, "Frieda", 1), (4, "Gustav", 2),
        (5, "Helga", 2), (6, "Ingo", 3), (7, "Jule", 4), (8, "Kai", 7)]
ins("employees", emps)

scd = [(1, 1, "Germany", "2024-01-01", None, 1), (2, 2, "Austria", "2024-01-26", None, 1),
       (3, 3, "Switzerland", "2024-02-20", None, 1)]
ins("dim_customer_scd", scd)
ins("stg_customer_changes", [(2, "Germany", "2025-04-01"), (3, "Switzerland", "2025-04-01")])  # 3 = unchanged

open("01_schema_and_data.sql", "w").write("\n".join(out) + "\n")
print(f"orders={len(orders)} items={len(items)}")
