-- Solutions for 02_exercises.md. Portable SQL: tested on SQLite 3.45, written to also run on PostgreSQL.
-- "Revenue" always means quantity * unit_price of COMPLETED orders unless stated otherwise.
-- Each block starts with a marker line "-- Exercise N" (used by verify_solutions.py).

-- Exercise 1
SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN orders   o ON o.order_id   = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
GROUP BY p.category
ORDER BY revenue DESC;

-- Exercise 2
SELECT c.customer_id, c.name
FROM customers c
LEFT JOIN orders o ON o.customer_id = c.customer_id
WHERE o.order_id IS NULL
ORDER BY c.customer_id;

-- Exercise 3
SELECT c.name, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM customers c
JOIN orders      o  ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name
ORDER BY revenue DESC, c.name
LIMIT 3;

-- Exercise 4
SELECT p.category, ROUND(SUM(oi.quantity * oi.unit_price), 2) AS revenue
FROM order_items oi
JOIN orders   o ON o.order_id   = oi.order_id
JOIN products p ON p.product_id = oi.product_id
WHERE o.status = 'completed'
GROUP BY p.category
HAVING SUM(oi.quantity * oi.unit_price) > 1000
ORDER BY revenue DESC;

-- Exercise 5
SELECT status,
       COUNT(*) AS orders,
       ROUND(100.0 * COUNT(*) / SUM(COUNT(*)) OVER (), 1) AS pct
FROM orders
GROUP BY status
ORDER BY orders DESC;

-- Exercise 6
WITH product_revenue AS (
  SELECT p.category, p.name, SUM(oi.quantity * oi.unit_price) AS revenue
  FROM order_items oi
  JOIN orders   o ON o.order_id   = oi.order_id
  JOIN products p ON p.product_id = oi.product_id
  WHERE o.status = 'completed'
  GROUP BY p.category, p.name
)
SELECT category, name, ROUND(revenue, 2) AS revenue,
       RANK()       OVER (PARTITION BY category ORDER BY revenue DESC) AS rnk,
       DENSE_RANK() OVER (PARTITION BY category ORDER BY revenue DESC) AS dense_rnk
FROM product_revenue
ORDER BY category, rnk, name;

-- Exercise 7
WITH product_revenue AS (
  SELECT p.category, p.name, SUM(oi.quantity * oi.unit_price) AS revenue
  FROM order_items oi
  JOIN orders   o ON o.order_id   = oi.order_id
  JOIN products p ON p.product_id = oi.product_id
  WHERE o.status = 'completed'
  GROUP BY p.category, p.name
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY category ORDER BY revenue DESC, name) AS rn
  FROM product_revenue
)
SELECT category, name, ROUND(revenue, 2) AS revenue
FROM ranked
WHERE rn = 1
ORDER BY category;

-- Exercise 8
-- (PostgreSQL idiom for the month key: DATE_TRUNC('month', order_date); the SUBSTR/CAST form runs everywhere.)
WITH monthly AS (
  SELECT SUBSTR(CAST(o.order_date AS VARCHAR(10)), 1, 7) AS month,
         SUM(oi.quantity * oi.unit_price) AS revenue
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'completed'
  GROUP BY SUBSTR(CAST(o.order_date AS VARCHAR(10)), 1, 7)
)
SELECT month,
       ROUND(revenue, 2) AS revenue,
       ROUND(100.0 * (revenue - LAG(revenue) OVER (ORDER BY month))
             / LAG(revenue) OVER (ORDER BY month), 1) AS mom_growth_pct
FROM monthly
ORDER BY month;

-- Exercise 9
WITH order_totals AS (
  SELECT o.order_id, o.customer_id, o.order_date, SUM(oi.quantity * oi.unit_price) AS order_value
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'completed'
  GROUP BY o.order_id, o.customer_id, o.order_date
)
SELECT customer_id, order_id, order_date,
       ROUND(order_value, 2) AS order_value,
       ROUND(SUM(order_value) OVER (
               PARTITION BY customer_id ORDER BY order_date, order_id
               ROWS BETWEEN UNBOUNDED PRECEDING AND CURRENT ROW), 2) AS running_total
FROM order_totals
ORDER BY customer_id, order_date, order_id;

-- Exercise 10
WITH order_totals AS (
  SELECT o.order_id, o.customer_id, o.order_date, SUM(oi.quantity * oi.unit_price) AS order_value
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'completed'
  GROUP BY o.order_id, o.customer_id, o.order_date
)
SELECT customer_id, order_id, order_date,
       ROUND(order_value, 2) AS order_value,
       ROUND(AVG(order_value) OVER (
               PARTITION BY customer_id ORDER BY order_date, order_id
               ROWS BETWEEN 2 PRECEDING AND CURRENT ROW), 2) AS moving_avg_3
FROM order_totals
ORDER BY customer_id, order_date, order_id;

-- Exercise 11
WITH order_totals AS (
  SELECT o.order_id, o.customer_id, o.order_date, SUM(oi.quantity * oi.unit_price) AS order_value
  FROM orders o
  JOIN order_items oi ON oi.order_id = o.order_id
  WHERE o.status = 'completed'
  GROUP BY o.order_id, o.customer_id, o.order_date
),
numbered AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY order_date, order_id) AS rn
  FROM order_totals
)
SELECT c.name, n.order_id, n.order_date, ROUND(n.order_value, 2) AS first_order_value
FROM numbered n
JOIN customers c ON c.customer_id = n.customer_id
WHERE n.rn = 1
ORDER BY c.name;

-- Exercise 12
SELECT c.name, COUNT(DISTINCT p.category) AS categories
FROM customers c
JOIN orders      o  ON o.customer_id = c.customer_id
JOIN order_items oi ON oi.order_id   = o.order_id
JOIN products    p  ON p.product_id  = oi.product_id
WHERE o.status = 'completed'
GROUP BY c.customer_id, c.name
HAVING COUNT(DISTINCT p.category) >= 2
ORDER BY categories DESC, c.name;

-- Exercise 13
WITH customer_revenue AS (
  SELECT c.customer_id, c.name, SUM(oi.quantity * oi.unit_price) AS revenue
  FROM customers c
  JOIN orders      o  ON o.customer_id = c.customer_id
  JOIN order_items oi ON oi.order_id   = o.order_id
  WHERE o.status = 'completed'
  GROUP BY c.customer_id, c.name
)
SELECT name, ROUND(revenue, 2) AS revenue,
       NTILE(4) OVER (ORDER BY revenue DESC) AS quartile
FROM customer_revenue
ORDER BY revenue DESC;

-- Exercise 14
WITH category_revenue AS (
  SELECT p.category, SUM(oi.quantity * oi.unit_price) AS revenue
  FROM order_items oi
  JOIN orders   o ON o.order_id   = oi.order_id
  JOIN products p ON p.product_id = oi.product_id
  WHERE o.status = 'completed'
  GROUP BY p.category
)
SELECT category, ROUND(revenue, 2) AS revenue,
       ROUND(100.0 * revenue / SUM(revenue) OVER (), 1) AS share_pct
FROM category_revenue
ORDER BY revenue DESC;

-- Exercise 15
WITH ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY event_id ORDER BY updated_at DESC) AS rn
  FROM raw_events
)
SELECT event_id, customer_id, event_type, amount, updated_at
FROM ranked
WHERE rn = 1
ORDER BY event_id;

-- Exercise 16
WITH numbered AS (
  SELECT customer_id, day_no,
         day_no - ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY day_no) AS grp
  FROM activity
),
streaks AS (
  SELECT customer_id, MIN(day_no) AS streak_start, MAX(day_no) AS streak_end, COUNT(*) AS streak_len
  FROM numbered
  GROUP BY customer_id, grp
),
ranked AS (
  SELECT *, ROW_NUMBER() OVER (PARTITION BY customer_id ORDER BY streak_len DESC, streak_start) AS rn
  FROM streaks
)
SELECT customer_id, streak_start, streak_end, streak_len
FROM ranked
WHERE rn = 1
ORDER BY customer_id;

-- Exercise 17
WITH RECURSIVE reports AS (
  SELECT emp_id, name, manager_id, 1 AS level
  FROM employees
  WHERE manager_id = 2
  UNION ALL
  SELECT e.emp_id, e.name, e.manager_id, r.level + 1
  FROM employees e
  JOIN reports r ON e.manager_id = r.emp_id
)
SELECT emp_id, name, level
FROM reports
ORDER BY level, emp_id;

-- Exercise 18
-- Step 1: close the current version of every customer whose country changed.
UPDATE dim_customer_scd
SET valid_to   = (SELECT s.change_date FROM stg_customer_changes s
                  WHERE s.customer_id = dim_customer_scd.customer_id),
    is_current = 0
WHERE is_current = 1
  AND EXISTS (SELECT 1 FROM stg_customer_changes s
              WHERE s.customer_id = dim_customer_scd.customer_id
                AND s.new_country <> dim_customer_scd.country);

-- Step 2: insert a new current version for every customer that now has no current row.
-- (In a real warehouse the surrogate key comes from a sequence / identity column.)
INSERT INTO dim_customer_scd (customer_key, customer_id, country, valid_from, valid_to, is_current)
SELECT (SELECT COALESCE(MAX(customer_key), 0) FROM dim_customer_scd)
         + ROW_NUMBER() OVER (ORDER BY s.customer_id),
       s.customer_id, s.new_country, s.change_date, NULL, 1
FROM stg_customer_changes s
WHERE NOT EXISTS (SELECT 1 FROM dim_customer_scd d
                  WHERE d.customer_id = s.customer_id AND d.is_current = 1);

-- Exercise 19
SELECT c.country,
       SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) AS completed,
       SUM(CASE WHEN o.status = 'cancelled' THEN 1 ELSE 0 END) AS cancelled,
       SUM(CASE WHEN o.status = 'returned'  THEN 1 ELSE 0 END) AS returned,
       ROUND(100.0 * SUM(CASE WHEN o.status = 'completed' THEN 1 ELSE 0 END) / COUNT(*), 1) AS completed_pct
FROM orders o
JOIN customers c ON c.customer_id = o.customer_id
GROUP BY c.country
ORDER BY c.country;

-- Exercise 20
SELECT p.product_id, p.name
FROM products p
WHERE NOT EXISTS (
  SELECT 1
  FROM order_items oi
  JOIN orders o ON o.order_id = oi.order_id
  WHERE oi.product_id = p.product_id AND o.status = 'completed'
)
ORDER BY p.product_id;
