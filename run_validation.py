"""Runs validation_queries.sql using Python's built-in sqlite3 (use this if the sqlite3 CLI isn't installed)."""
import sqlite3
con = sqlite3.connect("output/customers.db")
sql = open("validation_queries.sql").read()
for stmt in [s.strip() for s in sql.split(";") if s.strip()]:
    title = [l for l in stmt.splitlines() if l.startswith("--")]
    cur = con.execute("\n".join(l for l in stmt.splitlines() if not l.startswith("--")))
    cols = [d[0] for d in cur.description]
    print("\n" + (title[0] if title else ""))
    print(" | ".join(cols))
    for row in cur.fetchall(): print(" | ".join(str(v) for v in row))
