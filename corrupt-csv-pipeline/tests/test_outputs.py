import csv
import json
import os
import subprocess
import hashlib
from pathlib import Path


def test_pipeline_script_exists():
    """Test that the pipeline Python script was created at the expected path."""
    assert os.path.exists("/app/pipeline.py"), "Pipeline script /app/pipeline.py does not exist"


def test_output_directory_exists():
    """Test that the output directory was created."""
    assert os.path.isdir("/app/output"), "Output directory /app/output does not exist"


def test_cleaned_csv_exists():
    """Test that the cleaned CSV output file was produced."""
    assert os.path.exists("/app/output/cleaned.csv"), "Cleaned CSV /app/output/cleaned.csv does not exist"


def test_summary_json_exists():
    """Test that the summary JSON output file was produced."""
    assert os.path.exists("/app/output/summary.json"), "Summary JSON /app/output/summary.json does not exist"


def test_pipeline_runs_without_error():
    """Test that the pipeline script executes successfully without crashing."""
    result = subprocess.run(
        ["python", "/app/pipeline.py"],
        capture_output=True, text=True, cwd="/app"
    )
    assert result.returncode == 0, f"Pipeline failed with error: {result.stderr}"


def test_cleaned_csv_header():
    """Test that the cleaned CSV has the correct column headers."""
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.reader(f)
        header = next(reader)
    expected = ["date", "region", "category", "product", "quantity", "unit_price", "total"]
    assert header == expected, f"Expected header {expected}, got {header}"


def test_cleaned_csv_row_count():
    """Test that the cleaned CSV contains the correct number of valid data rows after filtering."""
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.reader(f)
        next(reader)  # skip header
        rows = list(reader)
    # 31 valid rows after removing: header dupes, unparseable dates, empty product row,
    # zero/negative quantity rows, and rows with completely invalid numbers
    assert len(rows) == 31, f"Expected 31 data rows, got {len(rows)}"


def test_cleaned_csv_date_format():
    """Test that all dates in the cleaned CSV are in YYYY-MM-DD format."""
    import re
    date_pattern = re.compile(r'^\d{4}-\d{2}-\d{2}$')
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            assert date_pattern.match(row["date"]), (
                f"Row {i+1} date '{row['date']}' is not in YYYY-MM-DD format"
            )


def test_cleaned_csv_sorted_by_date_then_region():
    """Test that output rows are sorted by date ascending then region alphabetically."""
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
    sort_keys = [(r["date"], r["region"]) for r in rows]
    assert sort_keys == sorted(sort_keys), "Rows are not sorted by date then region"


def test_cleaned_csv_total_column_computed():
    """Test that the total column equals quantity times unit_price for each row."""
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.DictReader(f)
        for i, row in enumerate(reader):
            qty = float(row["quantity"])
            price = float(row["unit_price"])
            total = float(row["total"])
            expected = round(qty * price, 2)
            assert abs(total - expected) < 0.01, (
                f"Row {i+1}: total {total} != quantity({qty}) * price({price}) = {expected}"
            )


def test_cleaned_csv_no_null_bytes():
    """Test that the cleaned output contains no null bytes or control characters."""
    with open("/app/output/cleaned.csv", "rb") as f:
        content = f.read()
    assert b'\x00' not in content, "Cleaned CSV contains null bytes"


def test_summary_json_valid():
    """Test that the summary JSON is valid and parseable."""
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    assert isinstance(data, dict), "Summary JSON root should be an object"


def test_summary_has_required_keys():
    """Test that the summary JSON contains all required top-level keys."""
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    required = {"by_region", "by_category", "total_revenue", "total_orders", "date_range"}
    missing = required - set(data.keys())
    assert not missing, f"Summary JSON missing keys: {missing}"


def test_summary_regions_present():
    """Test that all three regions appear in the by_region summary."""
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    regions = set(data["by_region"].keys())
    expected_regions = {"East", "West", "South"}
    assert regions == expected_regions, f"Expected regions {expected_regions}, got {regions}"


def test_summary_total_orders_matches_csv():
    """Test that total_orders in summary matches the row count in cleaned CSV."""
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.reader(f)
        next(reader)
        row_count = sum(1 for _ in reader)
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    assert data["total_orders"] == row_count, (
        f"total_orders {data['total_orders']} != CSV row count {row_count}"
    )


def test_summary_total_revenue_consistent():
    """Test that total_revenue equals sum of all totals in the cleaned CSV."""
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.DictReader(f)
        csv_total = sum(float(row["total"]) for row in reader)
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    assert abs(data["total_revenue"] - round(csv_total, 2)) < 0.01, (
        f"total_revenue {data['total_revenue']} != sum of CSV totals {csv_total:.2f}"
    )


def test_summary_region_revenue_sums_to_total():
    """Test that sum of per-region revenues equals total_revenue."""
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    region_sum = sum(v["revenue"] for v in data["by_region"].values())
    assert abs(region_sum - data["total_revenue"]) < 0.01, (
        f"Sum of region revenues {region_sum:.2f} != total_revenue {data['total_revenue']}"
    )


def test_summary_region_orders_sum_to_total():
    """Test that sum of per-region orders equals total_orders."""
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    region_orders = sum(v["orders"] for v in data["by_region"].values())
    assert region_orders == data["total_orders"], (
        f"Sum of region orders {region_orders} != total_orders {data['total_orders']}"
    )


def test_summary_date_range():
    """Test that the date_range in summary matches the actual min and max dates in the CSV."""
    with open("/app/output/cleaned.csv", "r") as f:
        reader = csv.DictReader(f)
        dates = [row["date"] for row in reader]
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    assert data["date_range"]["start"] == min(dates), (
        f"date_range start {data['date_range']['start']} != min date {min(dates)}"
    )
    assert data["date_range"]["end"] == max(dates), (
        f"date_range end {data['date_range']['end']} != max date {max(dates)}"
    )


def test_summary_by_category_structure():
    """Test that by_category is nested as region -> category -> revenue float."""
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    by_cat = data["by_category"]
    assert isinstance(by_cat, dict), "by_category should be a dict"
    for region, cats in by_cat.items():
        assert isinstance(cats, dict), f"by_category[{region}] should be a dict"
        for cat, val in cats.items():
            assert isinstance(val, (int, float)), (
                f"by_category[{region}][{cat}] should be numeric, got {type(val)}"
            )


def test_summary_by_category_revenue_matches_region():
    """Test that sum of category revenues per region matches that region total revenue."""
    with open("/app/output/summary.json", "r") as f:
        data = json.load(f)
    for region, cats in data["by_category"].items():
        cat_sum = sum(cats.values())
        region_rev = data["by_region"][region]["revenue"]
        assert abs(cat_sum - region_rev) < 0.01, (
            f"Region {region}: category sum {cat_sum:.2f} != region revenue {region_rev:.2f}"
        )


def test_no_duplicate_header_rows_in_output():
    """Test that the cleaned CSV does not contain duplicate header rows in the data."""
    with open("/app/output/cleaned.csv", "r") as f:
        lines = f.readlines()
    header_count = sum(1 for l in lines if l.strip().startswith("date,region,category"))
    assert header_count == 1, f"Found {header_count} header-like rows, expected exactly 1"


def test_handles_latin1_characters():
    """Test that products with special characters (like accented letters) are preserved in output."""
    with open("/app/output/cleaned.csv", "r", encoding="utf-8") as f:
        content = f.read()
    # The latin-1 encoded e-acute should be present in some form (decoded properly)
    assert "Caf" in content, "Product with special characters should be present in output"
