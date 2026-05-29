Hey, so we've got this sales data dump from three different regional offices and someone just mashed them together into one file at `/app/data/sales_raw.csv`. The thing is a mess — each office apparently used their own export settings and nobody bothered to standardize anything before merging.

I need you to write a Python script at `/app/pipeline.py` that reads this file, cleans it up, and produces two output files:

1. `/app/output/cleaned.csv` — the fully cleaned data with columns: `date,region,category,product,quantity,unit_price,total`  
   - All dates must be in `YYYY-MM-DD` format (drop rows with unparseable or malformed dates)
   - The `total` column should be `quantity * unit_price`  
   - Drop rows where quantity or unit_price cannot be parsed into valid positive numbers
   - Drop rows where quantity is zero or negative
   - Drop rows with empty product names
   - Output should be sorted by date ascending, then region alphabetically

2. `/app/output/summary.json` — aggregated stats as a JSON object with this structure:
   ```
   {
     "by_region": {"<region>": {"revenue": <float>, "orders": <int>}},
     "by_category": {"<region>": {"<category>": <float>}},
     "total_revenue": <float>,
     "total_orders": <int>,
     "date_range": {"start": "<YYYY-MM-DD>", "end": "<YYYY-MM-DD>"}
   }
   ```

Revenue means sum of all `total` values. Orders means count of valid rows. The `by_category` groups revenue by region first, then category within each region.

Make sure the output directory exists before writing. Run the script after creating it.
