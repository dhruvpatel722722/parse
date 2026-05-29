#!/usr/bin/env python3
"""Generate the corrupted sales CSV for the task."""
import os

os.makedirs("/app/data", exist_ok=True)

# The data has intentional corruption layered in non-obvious ways:
# 1. Mixed delimiters (commas, semicolons, tabs) per "office"
# 2. Encoding issues (latin-1 chars in a file with UTF-8 BOM)
# 3. Null bytes hidden inside numeric fields
# 4. Inconsistent date formats (DD/MM/YYYY, MM-DD-YYYY, YYYY.MM.DD, YYYY-MM-DD)
# 5. Quoted fields containing the delimiter character itself
# 6. UTF-8 BOM at start
# 7. Duplicate headers mid-file
# 8. Rows with wrong column count
# 9. Currency symbols in prices
# 10. Trailing whitespace and \r mixed line endings
# 11. Negative quantity (should be dropped)
# 12. Scientific notation in a price field
# 13. Unicode en-dash instead of hyphen in date
# 14. Trailing period in quantity

lines = []

# header (BOM written separately as bytes)
lines.append('date,region,category,product,quantity,unit_price')

# === EAST office: comma-delimited, YYYY-MM-DD dates ===
lines.append('2024-03-15,East,Electronics,Laptop Stand,12,45.99')
lines.append('2024-03-16,East,Electronics,USB Hub,8,29.50')
lines.append('2024-03-18,East,Furniture,"Office Chair, Ergonomic",3,299.99')
lines.append('2024-03-20,East,Electronics,Monitor Arm,5,89.00')
lines.append('2024-03-22,East,Stationery,Notebook Pack,\x0050,4.99')  # null byte before 50
lines.append('2024-03-25,East,Furniture,Standing Desk,2,549.00')
lines.append('2024-03-26,East,Electronics,Docking Station,  3  ,85.00')  # spaces around qty

# === WEST office: semicolon delimited, DD/MM/YYYY dates ===
lines.append('15/03/2024;West;Electronics;Wireless Mouse;25;19.99')
lines.append('17/03/2024;West;Stationery;Pen Set;1\x000;7.50')  # null byte: "1\x000" -> "10"
lines.append('19/03/2024;West;Electronics;"Keyboard; Mechanical";15;74.99')  # semicolon in quotes
lines.append('21/03/2024;West;Furniture;Bookshelf;4;189.50')
lines.append('23/03/2024;West;Electronics;Webcam HD;20;59.99')
lines.append('26/03/2024;West;Stationery;Marker Set;60;12.49')
lines.append('28/03/2024;West;Electronics;"Cable; HDMI; 2m";10;8.99')  # multiple semicolons in quotes

# Duplicate header sneaked in mid-file (from copy-paste during merge)
lines.append('date,region,category,product,quantity,unit_price')

# === SOUTH office: tab delimited, MM-DD-YYYY dates ===
lines.append('03-14-2024\tSouth\tElectronics\tPower Strip\t30\t24.99')
lines.append('03-16-2024\tSouth\tFurniture\tFiling Cabinet\t6\t175.00')
lines.append('03-18-2024\tSouth\tStationery\tSticky Notes\t200\t3.49')
lines.append('03-20-2024\tSouth\tElectronics\tLaptop Riser\t\x0014\t39.99')  # null byte before 14
lines.append('03-22-2024\tSouth\tFurniture\tDesk Lamp\t18\t64.50')
lines.append('03-25-2024\tSouth\tElectronics\tUSB-C Dock\t7\t129.99')
lines.append('03-27-2024\tSouth\tStationery\tLabel Maker\t-5\t45.00')  # negative qty -> drop

# === More EAST rows with encoding issues (latin-1 byte values) ===
lines.append('2024-03-27,East,Furniture,Caf\xe9 Table,4,220.00')  # e-acute in latin-1
lines.append('2024-03-28,East,Electronics,Display Cabl\xe9,30,14.99')  # e-acute
lines.append('2024-03-30,East,Stationery,Planner 2024,15,22.00')

# === WEST continued ===
lines.append('30/03/2024;West;Furniture;Monitor Stand;8;94.50')

# === SOUTH with price corruptions ===
lines.append('03-28-2024\tSouth\tStationery\tBinder Clips\t45\t5.99')
lines.append('03-29-2024\tSouth\tElectronics\tMouse Pad XL\t22\t$19.99')  # dollar sign
lines.append('03-30-2024\tSouth\tFurniture\tWhiteboard\t3\t189.00')

# Row with completely unparseable date
lines.append('not-a-date,Nowhere,???,,abc,xyz')

# Row with empty product and zero quantity -> drop
lines.append('2024-04-01,East,Electronics,,0,15.99')

# SOUTH row with YYYY.MM.DD format (yet another variant)
lines.append('2024.03.31\tSouth\tStationery\tClipboard\t35\t6.75')

# Row with en-dash (\u2013) instead of hyphen in date -> must handle or drop
# en-dash is 0xe2 0x80 0x93 in utf-8 but we write as latin-1 so \u2013 won't work
# Instead use a date with extra spaces that looks wrong
lines.append('2024- 03-29,East,Stationery,Binder Set,10,11.50')  # space in date -> invalid

# Row with scientific notation price
lines.append('04/03/2024;West;Stationery;Paper Ream;40;1.25e1')  # 1.25e1 = 12.50

# Row with \r at end (Windows artifact)
lines.append('05/03/2024;West;Electronics;Screen Protector;15;9.99\r')

# Another duplicate header but with semicolons (from WEST export)
lines.append('date;region;category;product;quantity;unit_price')

# Row where quantity has trailing period (e.g., "12.")
lines.append('2024-03-19,East,Stationery,Tape Dispenser,12.,8.25')

# Write as latin-1 encoded with UTF-8 BOM prefix (creates encoding confusion)
with open('/app/data/sales_raw.csv', 'wb') as f:
    # Write UTF-8 BOM first (misleading since actual content is latin-1)
    f.write(b'\xef\xbb\xbf')
    for i, line in enumerate(lines):
        encoded_line = line.encode('latin-1')
        f.write(encoded_line)
        f.write(b'\n')

print("Generated corrupted CSV at /app/data/sales_raw.csv")
