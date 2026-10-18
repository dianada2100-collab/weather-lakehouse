# SQL practice: 20 exercises

**Setup (pick one):**
- SQLite (zero install): `sqlite3 practice.db < 01_schema_and_data.sql`
- PostgreSQL: `psql -d mydb -f 01_schema_and_data.sql`

**Rules:** "Revenue" = `quantity * unit_price` of **completed** orders unless stated otherwise.
Try each exercise yourself first, then compare with `03_solutions.sql`. Check them all with
`python verify_solutions.py`.

**Tables:** `customers`, `products`, `orders`, `order_items`, `activity`, `raw_events`,
`employees`, `dim_customer_scd`, `stg_customer_changes` (see `01_schema_and_data.sql`).

## Level 1: joins and aggregation
| # | Task | Concepts |
|---|------|----------|
| 1 | Revenue per product category, highest first. | JOIN, GROUP BY |
| 2 | List customers who never placed an order. | LEFT JOIN + IS NULL |
| 3 | The 3 customers with the highest revenue. | JOIN, ORDER BY, LIMIT |
| 4 | Categories with revenue above 1000. | HAVING |
| 5 | Number of orders per status plus its percentage of all orders. | window over aggregate |

## Level 2: window functions and CTEs
| # | Task | Concepts |
|---|------|----------|
| 6 | Rank products by revenue within their category (show `RANK` and `DENSE_RANK`). | PARTITION BY |
| 7 | Best-selling product per category (exactly one row per category). | ROW_NUMBER, top-1 per group |
| 8 | Monthly revenue and month-over-month growth in %. | LAG |
| 9 | Running revenue total per customer over time. | SUM OVER, frame |
| 10 | Moving average of the last 3 order values per customer. | ROWS BETWEEN 2 PRECEDING |
| 11 | Each customer's first order (date and value). | ROW_NUMBER |
| 12 | Customers who bought from at least 2 different categories. | COUNT DISTINCT, HAVING |
| 13 | Split customers into revenue quartiles. | NTILE |
| 14 | Each category's share of total revenue in %. | SUM OVER () |

## Level 3: data-engineering patterns
| # | Task | Concepts |
|---|------|----------|
| 15 | `raw_events` contains duplicate `event_id`s. Keep only the latest version of each. | de-duplication |
| 16 | Longest streak of consecutive active days per customer (`activity.day_no`). | gaps and islands |
| 17 | All direct and indirect reports of employee 2, with their level. | recursive CTE |
| 18 | Apply `stg_customer_changes` to `dim_customer_scd` as SCD Type 2 (close old row, insert new row, leave unchanged customers alone). | UPDATE + INSERT, SCD2 |
| 19 | Per country: number of completed / cancelled / returned orders and the completed percentage. | conditional aggregation (pivot) |
| 20 | Products that never appeared in a completed order. | NOT EXISTS (anti-join) |

## Bonus: performance questions (answer in your own words, then check below)
1. A query filters `orders` by `customer_id` and sorts by `order_date`. Which index helps and why?
2. What does `EXPLAIN` / `EXPLAIN ANALYZE` show, and which signals tell you a query is slow?
3. When is `NOT EXISTS` better than `NOT IN`?

<details><summary>Answers</summary>

1. A composite index on `(customer_id, order_date)`: the filter uses the first column, and the rows come out
   already sorted by the second, so the database can skip a separate sort step.
2. The execution plan. Warning signs: sequential/full table scans on big tables, large gaps between estimated
   and actual rows, sorts or hash joins spilling to disk, and nested loops over large inputs.
3. `NOT IN` returns no rows at all if the subquery contains a NULL (three-valued logic) and can be slower;
   `NOT EXISTS` handles NULLs correctly and is usually optimised into an anti-join.
</details>

## Window-function cheat sheet
```sql
fn() OVER (PARTITION BY group_col ORDER BY sort_col ROWS BETWEEN 2 PRECEDING AND CURRENT ROW)
-- ranking:     ROW_NUMBER, RANK, DENSE_RANK, NTILE(n)
-- navigation:  LAG(col, n), LEAD(col, n), FIRST_VALUE, LAST_VALUE
-- aggregates:  SUM, AVG, COUNT, MIN, MAX  (running totals, moving averages, shares of total)
```
