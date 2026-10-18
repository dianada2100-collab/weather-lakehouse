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

INSERT INTO customers VALUES (1, 'Anna', 'Germany', '2024-01-01');
INSERT INTO customers VALUES (2, 'Ben', 'Austria', '2024-01-26');
INSERT INTO customers VALUES (3, 'Clara', 'Switzerland', '2024-02-20');
INSERT INTO customers VALUES (4, 'David', 'France', '2024-03-16');
INSERT INTO customers VALUES (5, 'Emma', 'Germany', '2024-04-10');
INSERT INTO customers VALUES (6, 'Felix', 'Germany', '2024-05-05');
INSERT INTO customers VALUES (7, 'Greta', 'Switzerland', '2024-05-30');
INSERT INTO customers VALUES (8, 'Hannes', 'France', '2024-06-24');
INSERT INTO customers VALUES (9, 'Ida', 'Germany', '2024-07-19');
INSERT INTO customers VALUES (10, 'Jonas', 'Austria', '2024-08-13');
INSERT INTO customers VALUES (11, 'Klara', 'Germany', '2024-09-07');
INSERT INTO customers VALUES (12, 'Lukas', 'France', '2024-10-02');
INSERT INTO customers VALUES (13, 'Mia', 'Germany', '2024-10-27');
INSERT INTO customers VALUES (14, 'Noah', 'Austria', '2024-11-21');
INSERT INTO customers VALUES (15, 'Olivia', 'Switzerland', '2024-12-16');

INSERT INTO products VALUES (1, 'Laptop', 'Electronics', 999.0);
INSERT INTO products VALUES (2, 'Headphones', 'Electronics', 149.5);
INSERT INTO products VALUES (3, 'Monitor', 'Electronics', 289.0);
INSERT INTO products VALUES (4, 'Desk', 'Furniture', 349.0);
INSERT INTO products VALUES (5, 'Chair', 'Furniture', 199.0);
INSERT INTO products VALUES (6, 'Notebook', 'Stationery', 4.5);
INSERT INTO products VALUES (7, 'Pen Set', 'Stationery', 12.9);
INSERT INTO products VALUES (8, 'Backpack', 'Accessories', 59.0);

INSERT INTO orders VALUES (27, 8, '2025-01-01', 'returned');
INSERT INTO orders VALUES (1, 1, '2025-01-07', 'completed');
INSERT INTO orders VALUES (4, 2, '2025-01-07', 'cancelled');
INSERT INTO orders VALUES (3, 2, '2025-01-08', 'completed');
INSERT INTO orders VALUES (48, 13, '2025-01-13', 'returned');
INSERT INTO orders VALUES (15, 5, '2025-01-15', 'completed');
INSERT INTO orders VALUES (34, 10, '2025-01-16', 'completed');
INSERT INTO orders VALUES (35, 10, '2025-01-19', 'cancelled');
INSERT INTO orders VALUES (29, 9, '2025-01-22', 'completed');
INSERT INTO orders VALUES (20, 6, '2025-01-24', 'completed');
INSERT INTO orders VALUES (11, 4, '2025-01-26', 'completed');
INSERT INTO orders VALUES (40, 11, '2025-01-26', 'completed');
INSERT INTO orders VALUES (43, 12, '2025-01-26', 'completed');
INSERT INTO orders VALUES (2, 1, '2025-01-27', 'cancelled');
INSERT INTO orders VALUES (7, 3, '2025-01-27', 'completed');
INSERT INTO orders VALUES (23, 7, '2025-01-30', 'cancelled');
INSERT INTO orders VALUES (30, 9, '2025-02-02', 'completed');
INSERT INTO orders VALUES (41, 12, '2025-02-18', 'cancelled');
INSERT INTO orders VALUES (26, 8, '2025-02-20', 'completed');
INSERT INTO orders VALUES (36, 11, '2025-02-24', 'cancelled');
INSERT INTO orders VALUES (47, 13, '2025-02-25', 'completed');
INSERT INTO orders VALUES (5, 3, '2025-02-26', 'completed');
INSERT INTO orders VALUES (10, 4, '2025-02-28', 'completed');
INSERT INTO orders VALUES (28, 9, '2025-03-03', 'completed');
INSERT INTO orders VALUES (18, 6, '2025-03-05', 'cancelled');
INSERT INTO orders VALUES (8, 3, '2025-03-09', 'completed');
INSERT INTO orders VALUES (16, 6, '2025-03-10', 'completed');
INSERT INTO orders VALUES (14, 5, '2025-03-11', 'cancelled');
INSERT INTO orders VALUES (6, 3, '2025-03-13', 'completed');
INSERT INTO orders VALUES (9, 3, '2025-03-17', 'returned');
INSERT INTO orders VALUES (17, 6, '2025-03-22', 'completed');
INSERT INTO orders VALUES (33, 10, '2025-03-28', 'completed');
INSERT INTO orders VALUES (12, 5, '2025-04-01', 'completed');
INSERT INTO orders VALUES (19, 6, '2025-04-03', 'completed');
INSERT INTO orders VALUES (45, 13, '2025-04-10', 'completed');
INSERT INTO orders VALUES (38, 11, '2025-04-15', 'completed');
INSERT INTO orders VALUES (21, 7, '2025-04-19', 'returned');
INSERT INTO orders VALUES (31, 9, '2025-04-19', 'completed');
INSERT INTO orders VALUES (39, 11, '2025-04-21', 'completed');
INSERT INTO orders VALUES (24, 8, '2025-04-22', 'completed');
INSERT INTO orders VALUES (32, 10, '2025-04-23', 'cancelled');
INSERT INTO orders VALUES (42, 12, '2025-04-29', 'completed');
INSERT INTO orders VALUES (22, 7, '2025-04-30', 'cancelled');
INSERT INTO orders VALUES (44, 13, '2025-05-04', 'completed');
INSERT INTO orders VALUES (25, 8, '2025-05-09', 'completed');
INSERT INTO orders VALUES (13, 5, '2025-05-17', 'completed');
INSERT INTO orders VALUES (46, 13, '2025-05-23', 'completed');
INSERT INTO orders VALUES (37, 11, '2025-05-28', 'completed');

INSERT INTO order_items VALUES (1, 2, 1, 149.5);
INSERT INTO order_items VALUES (2, 5, 2, 199.0);
INSERT INTO order_items VALUES (3, 2, 3, 149.5);
INSERT INTO order_items VALUES (4, 6, 3, 4.5);
INSERT INTO order_items VALUES (5, 3, 3, 289.0);
INSERT INTO order_items VALUES (5, 1, 2, 999.0);
INSERT INTO order_items VALUES (5, 2, 2, 149.5);
INSERT INTO order_items VALUES (6, 7, 2, 12.9);
INSERT INTO order_items VALUES (7, 1, 2, 999.0);
INSERT INTO order_items VALUES (7, 3, 3, 289.0);
INSERT INTO order_items VALUES (8, 4, 2, 349.0);
INSERT INTO order_items VALUES (8, 5, 1, 199.0);
INSERT INTO order_items VALUES (8, 1, 3, 999.0);
INSERT INTO order_items VALUES (9, 5, 3, 199.0);
INSERT INTO order_items VALUES (9, 2, 1, 149.5);
INSERT INTO order_items VALUES (10, 7, 1, 12.9);
INSERT INTO order_items VALUES (11, 4, 2, 349.0);
INSERT INTO order_items VALUES (11, 6, 1, 4.5);
INSERT INTO order_items VALUES (12, 3, 3, 289.0);
INSERT INTO order_items VALUES (12, 6, 3, 4.5);
INSERT INTO order_items VALUES (12, 1, 1, 999.0);
INSERT INTO order_items VALUES (13, 4, 2, 349.0);
INSERT INTO order_items VALUES (14, 6, 2, 4.5);
INSERT INTO order_items VALUES (15, 7, 2, 12.9);
INSERT INTO order_items VALUES (16, 5, 3, 199.0);
INSERT INTO order_items VALUES (17, 4, 1, 349.0);
INSERT INTO order_items VALUES (17, 7, 2, 12.9);
INSERT INTO order_items VALUES (17, 6, 1, 4.5);
INSERT INTO order_items VALUES (18, 3, 2, 289.0);
INSERT INTO order_items VALUES (18, 6, 3, 4.5);
INSERT INTO order_items VALUES (18, 5, 2, 199.0);
INSERT INTO order_items VALUES (19, 5, 2, 199.0);
INSERT INTO order_items VALUES (20, 2, 3, 149.5);
INSERT INTO order_items VALUES (21, 4, 2, 349.0);
INSERT INTO order_items VALUES (22, 5, 3, 199.0);
INSERT INTO order_items VALUES (22, 1, 3, 999.0);
INSERT INTO order_items VALUES (23, 7, 2, 12.9);
INSERT INTO order_items VALUES (23, 6, 1, 4.5);
INSERT INTO order_items VALUES (24, 1, 3, 999.0);
INSERT INTO order_items VALUES (24, 6, 2, 4.5);
INSERT INTO order_items VALUES (25, 1, 3, 999.0);
INSERT INTO order_items VALUES (25, 6, 3, 4.5);
INSERT INTO order_items VALUES (25, 3, 3, 289.0);
INSERT INTO order_items VALUES (26, 7, 3, 12.9);
INSERT INTO order_items VALUES (26, 2, 3, 149.5);
INSERT INTO order_items VALUES (27, 4, 1, 349.0);
INSERT INTO order_items VALUES (27, 1, 2, 999.0);
INSERT INTO order_items VALUES (28, 5, 1, 199.0);
INSERT INTO order_items VALUES (29, 7, 3, 12.9);
INSERT INTO order_items VALUES (30, 4, 2, 349.0);
INSERT INTO order_items VALUES (30, 5, 3, 199.0);
INSERT INTO order_items VALUES (30, 2, 3, 149.5);
INSERT INTO order_items VALUES (31, 7, 3, 12.9);
INSERT INTO order_items VALUES (31, 6, 2, 4.5);
INSERT INTO order_items VALUES (31, 2, 2, 149.5);
INSERT INTO order_items VALUES (32, 1, 1, 999.0);
INSERT INTO order_items VALUES (32, 2, 1, 149.5);
INSERT INTO order_items VALUES (33, 5, 1, 199.0);
INSERT INTO order_items VALUES (33, 2, 1, 149.5);
INSERT INTO order_items VALUES (33, 7, 1, 12.9);
INSERT INTO order_items VALUES (34, 1, 2, 999.0);
INSERT INTO order_items VALUES (35, 3, 3, 289.0);
INSERT INTO order_items VALUES (36, 6, 3, 4.5);
INSERT INTO order_items VALUES (37, 7, 2, 12.9);
INSERT INTO order_items VALUES (38, 1, 3, 999.0);
INSERT INTO order_items VALUES (39, 4, 3, 349.0);
INSERT INTO order_items VALUES (39, 7, 1, 12.9);
INSERT INTO order_items VALUES (40, 6, 1, 4.5);
INSERT INTO order_items VALUES (40, 3, 1, 289.0);
INSERT INTO order_items VALUES (41, 2, 1, 149.5);
INSERT INTO order_items VALUES (41, 4, 2, 349.0);
INSERT INTO order_items VALUES (42, 4, 3, 349.0);
INSERT INTO order_items VALUES (43, 5, 1, 199.0);
INSERT INTO order_items VALUES (43, 1, 1, 999.0);
INSERT INTO order_items VALUES (43, 6, 2, 4.5);
INSERT INTO order_items VALUES (44, 1, 2, 999.0);
INSERT INTO order_items VALUES (44, 2, 1, 149.5);
INSERT INTO order_items VALUES (45, 3, 3, 289.0);
INSERT INTO order_items VALUES (45, 4, 3, 349.0);
INSERT INTO order_items VALUES (46, 2, 2, 149.5);
INSERT INTO order_items VALUES (47, 6, 3, 4.5);
INSERT INTO order_items VALUES (47, 5, 2, 199.0);
INSERT INTO order_items VALUES (47, 1, 1, 999.0);
INSERT INTO order_items VALUES (48, 5, 1, 199.0);
INSERT INTO order_items VALUES (48, 7, 1, 12.9);

INSERT INTO activity VALUES (1, 1);
INSERT INTO activity VALUES (1, 2);
INSERT INTO activity VALUES (1, 3);
INSERT INTO activity VALUES (1, 5);
INSERT INTO activity VALUES (1, 6);
INSERT INTO activity VALUES (1, 7);
INSERT INTO activity VALUES (1, 8);
INSERT INTO activity VALUES (1, 9);
INSERT INTO activity VALUES (1, 20);
INSERT INTO activity VALUES (2, 4);
INSERT INTO activity VALUES (2, 5);
INSERT INTO activity VALUES (2, 6);
INSERT INTO activity VALUES (2, 10);
INSERT INTO activity VALUES (3, 1);
INSERT INTO activity VALUES (3, 3);
INSERT INTO activity VALUES (3, 5);
INSERT INTO activity VALUES (3, 7);
INSERT INTO activity VALUES (4, 10);
INSERT INTO activity VALUES (4, 11);
INSERT INTO activity VALUES (4, 12);
INSERT INTO activity VALUES (4, 13);
INSERT INTO activity VALUES (4, 14);
INSERT INTO activity VALUES (4, 15);

INSERT INTO raw_events VALUES (1, 1, 'purchase', 50.0, '2025-03-01 10:00:00');
INSERT INTO raw_events VALUES (1, 1, 'purchase', 55.0, '2025-03-01 12:00:00');
INSERT INTO raw_events VALUES (2, 2, 'refund', 20.0, '2025-03-02 09:00:00');
INSERT INTO raw_events VALUES (3, 3, 'purchase', 80.0, '2025-03-02 11:00:00');
INSERT INTO raw_events VALUES (3, 3, 'purchase', 80.0, '2025-03-02 11:00:00');
INSERT INTO raw_events VALUES (3, 3, 'purchase', 85.0, '2025-03-03 08:00:00');
INSERT INTO raw_events VALUES (4, 1, 'purchase', 10.0, '2025-03-04 15:30:00');

INSERT INTO employees VALUES (1, 'Dora (CEO)', NULL);
INSERT INTO employees VALUES (2, 'Elias', 1);
INSERT INTO employees VALUES (3, 'Frieda', 1);
INSERT INTO employees VALUES (4, 'Gustav', 2);
INSERT INTO employees VALUES (5, 'Helga', 2);
INSERT INTO employees VALUES (6, 'Ingo', 3);
INSERT INTO employees VALUES (7, 'Jule', 4);
INSERT INTO employees VALUES (8, 'Kai', 7);

INSERT INTO dim_customer_scd VALUES (1, 1, 'Germany', '2024-01-01', NULL, 1);
INSERT INTO dim_customer_scd VALUES (2, 2, 'Austria', '2024-01-26', NULL, 1);
INSERT INTO dim_customer_scd VALUES (3, 3, 'Switzerland', '2024-02-20', NULL, 1);

INSERT INTO stg_customer_changes VALUES (2, 'Germany', '2025-04-01');
INSERT INTO stg_customer_changes VALUES (3, 'Switzerland', '2025-04-01');

