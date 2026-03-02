import csv
import io
from pathlib import Path


def query_csv(file_path: str, columns: list[str] = None) -> list[dict[str, str]]:
    """Reads a CSV file and optionally filters by specific columns."""
    path = Path(file_path)
    if not path.is_file():
        raise FileNotFoundError(f"CSV file not found: {file_path}")

    results = []
    with path.open(mode="r", encoding="utf-8") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if columns:
                # Filter down to just the requested columns
                filtered_row = {
                    col: row[col] for col in columns if col in row
                }
                results.append(filtered_row)
            else:
                results.append(dict(row))
    return results
