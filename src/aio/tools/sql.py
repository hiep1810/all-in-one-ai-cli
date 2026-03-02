import sqlite3
from pathlib import Path


def query_sqlite(db_path: str, query: str) -> list[dict]:
    """Executes a SQL query against a SQLite database and returns the rows as a list of dicts."""
    path = Path(db_path)
    if not path.is_file():
        raise FileNotFoundError(f"SQLite database not found: {db_path}")

    results = []
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row  # Enables access by column name
        cursor = conn.cursor()
        cursor.execute(query)
        rows = cursor.fetchall()
        for row in rows:
            results.append(dict(row))
    return results
