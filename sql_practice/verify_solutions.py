"""Runs every solution in 03_solutions.sql against a fresh in-memory SQLite database and checks
the results. Only the standard library is needed:  python verify_solutions.py"""
import re
import sqlite3
from pathlib import Path

HERE = Path(__file__).parent


def load_blocks() -> dict[int, str]:
    text = (HERE / "03_solutions.sql").read_text()
    parts = re.split(r"^-- Exercise (\d+)\s*$", text, flags=re.MULTILINE)
    return {int(parts[i]): parts[i + 1].strip() for i in range(1, len(parts), 2)}


def fresh_db() -> sqlite3.Connection:
    con = sqlite3.connect(":memory:")
    con.executescript((HERE / "01_schema_and_data.sql").read_text())
    return con


def run_select(con, sql):
    cur = con.execute(sql)
    return [d[0] for d in cur.description], cur.fetchall()


def main() -> None:
    blocks = load_blocks()
    assert sorted(blocks) == list(range(1, 21)), "expected exercises 1..20"
    results = {}
    for n, sql in blocks.items():
        con = fresh_db()
        if n == 18:
            con.executescript(sql)
            results[n] = con.execute(
                "SELECT customer_id, country, valid_from, valid_to, is_current "
                "FROM dim_customer_scd ORDER BY customer_id, valid_from").fetchall()
        else:
            cols, rows = run_select(con, sql)
            assert rows, f"exercise {n} returned no rows"
            results[n] = rows
        print(f"Exercise {n:>2}: OK ({len(results[n])} rows)")

    # --- result checks (independent of the SQL under test) ---------------------------------
    con = fresh_db()
    items = con.execute(
        "SELECT p.category, oi.quantity * oi.unit_price FROM order_items oi "
        "JOIN orders o USING (order_id) JOIN products p USING (product_id) "
        "WHERE o.status = 'completed'").fetchall()
    expected: dict[str, float] = {}
    for cat, value in items:
        expected[cat] = expected.get(cat, 0.0) + value
    got = dict(results[1])
    assert got.keys() == expected.keys()
    assert all(abs(got[c] - round(expected[c], 2)) < 0.01 for c in got), "ex1 revenue mismatch"
    assert abs(sum(r[2] for r in results[14]) - 100.0) < 0.5, "shares must add up to ~100 %"

    assert [r[0] for r in results[2]] == [14, 15]
    assert len(results[3]) == 3 and results[3] == sorted(results[3], key=lambda r: -r[1])
    assert abs(sum(r[2] for r in results[5]) - 100.0) < 0.2
    assert len({r[0] for r in results[7]}) == len(results[7]), "ex7: one row per category"
    assert results[8][0][2] is None, "first month has no previous month"
    assert {r[0]: r[3] for r in results[16]} == {1: 5, 2: 3, 3: 1, 4: 6}
    assert [r[0] for r in results[17]] == [4, 5, 7, 8] and [r[2] for r in results[17]] == [1, 1, 2, 3]
    ev = {r[0]: r[3] for r in results[15]}
    assert len(ev) == 4 and ev[1] == 55.0 and ev[3] == 85.0, "ex15: latest version must win"
    assert {r[0] for r in results[13]} and max(r[2] for r in results[13]) <= 4

    assert [r[0] for r in results[20]] == [8], "ex20: only the backpack was never sold"

    scd = results[18]
    assert [r for r in scd if r[0] == 2] == [
        (2, "Austria", "2024-01-26", "2025-04-01", 0), (2, "Germany", "2025-04-01", None, 1)]
    assert len([r for r in scd if r[0] == 3]) == 1, "unchanged customer must not get a new version"
    assert sum(1 for r in scd if r[4] == 1 and r[0] == 2) == 1

    print("\nAll 20 solutions run and pass their result checks.")


if __name__ == "__main__":
    main()
