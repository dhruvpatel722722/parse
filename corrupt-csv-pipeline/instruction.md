Hey, so we've got this sales data dump from three different regional offices and someone just mashed them together into one file at `/app/data/sales_raw.csv`. The thing is a mess — each office used their own export settings and nobody standardized anything before merging.

I need you to write a Python script at `/app/pipeline.py` that reads this file, cleans it up, and produces two output files:

1. `/app/output/cleaned.csv` — the fully cleaned data with columns: `date,region,category,product,quantity,unit_price,total`  
   - Dates appear in multiple formats (YYYY-MM-DD, DD/MM/YYYY, MM-DD-YYYY, YYYY.MM.DD) — normalize all to `YYYY-MM-DD`, drop rows with invalid calendar dates
   - Strip currency symbols ($) and thousands separators (commas between digits) before parsing numbers
   - Remove any embedded null bytes from fields before parsing
   - The `total` column should be `quantity * unit_price`  
   - Drop rows where quantity or unit_price cannot be parsed into valid positive numbers (strictly greater than zero)
   - Quantities can be fractional (e.g., 3.5 is valid)
   - If a row has more or fewer than 6 data fields after delimiter detection, drop it
   - Drop rows with empty product names
   - Output sorted by date ascending, then region alphabetically

2. `/app/output/summary.json` — aggregated stats:
   ```
   {
     "by_region": {"<region>": {"revenue": <float>, "orders": <int>}},
     "by_category": {"<region>": {"<category>": <float>}},
     "total_revenue": <float>,
     "total_orders": <int>,
     "date_range": {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"}
   }
   ```

Revenue is sum of `total` values. Orders is count of valid rows. `by_category` groups revenue by region then category.

Make sure the output directory exists. Run the script after creating it.
