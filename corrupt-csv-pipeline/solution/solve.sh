#!/bin/bash
# Do NOT use set -e or set -euo pipefail

mkdir -p /app/output

cat > /app/pipeline.py << 'PYTHON'
import csv
import json
import re
import os
from datetime import datetime
from collections import defaultdict

os.makedirs("/app/output", exist_ok=True)

# Read raw bytes and handle encoding issues
with open("/app/data/sales_raw.csv", "rb") as f:
    raw = f.read()

# Remove BOM if present
if raw.startswith(b'\xef\xbb\xbf'):
    raw = raw[3:]

# Remove null bytes
raw = raw.replace(b'\x00', b'')

# Decode as latin-1 (superset of ascii, handles all byte values)
text = raw.decode('latin-1')

# Normalize line endings
text = text.replace('\r\n', '\n').replace('\r', '')

lines = text.strip().split('\n')

parsed_rows = []

def parse_date(date_str):
    """Try multiple date formats and return YYYY-MM-DD or None."""
    date_str = date_str.strip()
    # Reject dates with extra spaces or non-standard characters
    if '  ' in date_str or ' ' in date_str.replace(' ', '', 0):
        # Check if there's a space that shouldn't be there
        if ' ' in date_str:
            return None
    formats = [
        '%Y-%m-%d',
        '%d/%m/%Y',
        '%m-%d-%Y',
        '%Y.%m.%d',
    ]
    for fmt in formats:
        try:
            dt = datetime.strptime(date_str, fmt)
            # Sanity check the date
            if dt.year < 2000 or dt.year > 2030:
                continue
            return dt.strftime('%Y-%m-%d')
        except ValueError:
            continue
    return None

def parse_number(val):
    """Parse a number, stripping currency symbols and whitespace."""
    if val is None:
        return None
    val = val.strip()
    if not val:
        return None
    # Remove currency symbols
    val = re.sub(r'[$\xa3\xa5]', '', val)
    # Handle scientific notation
    try:
        result = float(val)
        return result
    except ValueError:
        pass
    # Remove any remaining non-numeric chars except . and - and e
    val = re.sub(r'[^\d.\-eE]', '', val)
    if not val or val in ('.', '-', 'e', 'E'):
        return None
    try:
        return float(val)
    except ValueError:
        return None

for line in lines:
    line = line.strip()
    if not line:
        continue

    # Skip header rows (both comma and semicolon variants)
    lower_line = line.lower().replace(' ', '')
    if 'date' in lower_line and 'region' in lower_line and 'category' in lower_line:
        continue

    # Detect delimiter
    if '\t' in line:
        delim = '\t'
    elif ';' in line:
        delim = ';'
    else:
        delim = ','

    # Parse with csv reader to handle quoted fields
    try:
        reader = csv.reader([line], delimiter=delim, quotechar='"')
        fields = next(reader)
    except Exception:
        continue

    if len(fields) < 6:
        continue

    # Extract fields
    date_raw = fields[0].strip()
    region = fields[1].strip()
    category = fields[2].strip()
    product = fields[3].strip()
    qty_raw = fields[4].strip()
    price_raw = fields[5].strip()

    # Parse date
    date_parsed = parse_date(date_raw)
    if date_parsed is None:
        continue

    # Parse quantity and price
    quantity = parse_number(qty_raw)
    unit_price = parse_number(price_raw)

    if quantity is None or unit_price is None:
        continue

    # Drop zero or negative quantities
    if quantity <= 0:
        continue

    # Skip if product is empty
    if not product:
        continue

    total = round(quantity * unit_price, 2)

    parsed_rows.append({
        'date': date_parsed,
        'region': region,
        'category': category,
        'product': product,
        'quantity': int(quantity),
        'unit_price': unit_price,
        'total': total
    })

# Sort by date ascending, then region alphabetically
parsed_rows.sort(key=lambda r: (r['date'], r['region']))

# Write cleaned CSV
with open("/app/output/cleaned.csv", "w", newline='') as f:
    writer = csv.writer(f)
    writer.writerow(['date', 'region', 'category', 'product', 'quantity', 'unit_price', 'total'])
    for row in parsed_rows:
        writer.writerow([
            row['date'],
            row['region'],
            row['category'],
            row['product'],
            row['quantity'],
            row['unit_price'],
            row['total']
        ])

# Build summary
by_region = defaultdict(lambda: {'revenue': 0.0, 'orders': 0})
by_category = defaultdict(lambda: defaultdict(float))

for row in parsed_rows:
    by_region[row['region']]['revenue'] += row['total']
    by_region[row['region']]['orders'] += 1
    by_category[row['region']][row['category']] += row['total']

total_revenue = sum(r['total'] for r in parsed_rows)
total_orders = len(parsed_rows)

dates = [r['date'] for r in parsed_rows]
date_range = {'start': min(dates), 'end': max(dates)}

summary = {
    'by_region': {k: {'revenue': round(v['revenue'], 2), 'orders': v['orders']} for k, v in sorted(by_region.items())},
    'by_category': {k: {ck: round(cv, 2) for ck, cv in sorted(v.items())} for k, v in sorted(by_category.items())},
    'total_revenue': round(total_revenue, 2),
    'total_orders': total_orders,
    'date_range': date_range
}

with open("/app/output/summary.json", "w") as f:
    json.dump(summary, f, indent=2)

print(f"Processed {total_orders} valid rows")
print(f"Total revenue: {total_revenue:.2f}")
PYTHON

python /app/pipeline.py
