#!/usr/bin/env python3
"""Generate the corrupted sales CSV for the task."""
import os
import struct

os.makedirs("/app/data", exist_ok=True)

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
lines.append('19/03/2024;West;Electronics;"Keyboard; Mechanical";15;74.99')
lines.append('21/03/2024;West;Furniture;Bookshelf;4;189.50')
lines.append('23/03/2024;West;Electronics;Webcam HD;20;59.99')
lines.append('26/03/2024;West;Stationery;Marker Set;60;12.49')
lines.append('28/03/2024;West;Electronics;"Cable; HDMI; 2m";10;8.99')

# Duplicate header mid-file
lines.append('date,region,category,product,quantity,unit_price')

# === SOUTH office: tab delimited, MM-DD-YYYY dates ===
lines.append('03-14-2024\tSouth\tElectronics\tPower Strip\t30\t24.99')
lines.append('03-16-2024\tSouth\tFurniture\tFiling Cabinet\t6\t175.00')
lines.append('03-18-2024\tSouth\tStationery\tSticky Notes\t200\t3.49')
lines.append('03-20-2024\tSouth\tElectronics\tLaptop Riser\t\x0014\t39.99')  # null byte before 14
lines.append('03-22-2024\tSouth\tFurniture\tDesk Lamp\t18\t64.50')
lines.append('03-25-2024\tSouth\tElectronics\tUSB-C Dock\t7\t129.99')
lines.append('03-27-2024\tSouth\tStationery\tLabel Maker\t-5\t45.00')  # negative qty -> drop

# === More EAST rows with latin-1 encoding ===
lines.append('2024-03-27,East,Furniture,Caf\xe9 Table,4,220.00')
lines.append('2024-03-28,East,Electronics,Display Cabl\xe9,30,14.99')
lines.append('2024-03-30,East,Stationery,Planner 2024,15,22.00')

# === WEST continued ===
lines.append('30/03/2024;West;Furniture;Monitor Stand;8;94.50')

# === SOUTH with price corruptions ===
lines.append('03-28-2024\tSouth\tStationery\tBinder Clips\t45\t5.99')
lines.append('03-29-2024\tSouth\tElectronics\tMouse Pad XL\t22\t$19.99')
lines.append('03-30-2024\tSouth\tFurniture\tWhiteboard\t3\t189.00')

# Unparseable date row -> drop
lines.append('not-a-date,Nowhere,???,,abc,xyz')

# Empty product + zero qty -> drop
lines.append('2024-04-01,East,Electronics,,0,15.99')

# SOUTH YYYY.MM.DD format
lines.append('2024.03.31\tSouth\tStationery\tClipboard\t35\t6.75')

# Space in date -> invalid, drop
lines.append('2024- 03-29,East,Stationery,Binder Set,10,11.50')

# Scientific notation price
lines.append('04/03/2024;West;Stationery;Paper Ream;40;1.25e1')

# Windows \r artifact
lines.append('05/03/2024;West;Electronics;Screen Protector;15;9.99\r')

# Duplicate header semicolon variant
lines.append('date;region;category;product;quantity;unit_price')

# Trailing period in quantity
lines.append('2024-03-19,East,Stationery,Tape Dispenser,12.,8.25')

# === NEW TRICKY ROWS that make it harder ===

# Row with pipe character that looks like a field but isn't (noise in product name)
lines.append('2024-03-21,East,Electronics,USB Hub | 7-Port,6,34.99')

# Row where the date is DD/MM/YYYY but day > 12 so it can't be confused with MM/DD
# But this one has day=08 month=04 which IS ambiguous (could be April 8 or Aug 4)
# Since WEST uses DD/MM/YYYY, this should be 08-April-2024
lines.append('08/04/2024;West;Furniture;Desk Organizer;12;27.50')

# Row with quantity that has thousands separator (1,200 -> should be 1200? or invalid?)
# Since comma is the delimiter for EAST, this breaks parsing if not handled
# Put it in SOUTH (tab-delimited) so the comma is just in the number
lines.append('03-26-2024\tSouth\tStationery\tCopy Paper Box\t1,200\t0.05')

# Row with unicode RIGHT SINGLE QUOTATION MARK in product name (latin-1: 0x92 in cp1252 but not in iso-8859-1)
# Use a safe latin-1 char instead: multiplication sign \xd7
lines.append('2024-03-29,East,Furniture,Shelf 2\xd74,2,145.00')

# Row with price having trailing whitespace and tab mixed in
lines.append('07/03/2024;West;Electronics;Power Bank;8; 49.99\t')

# Row where region has leading/trailing spaces
lines.append('2024-03-17,  East  ,Stationery,Sticky Tabs,30,3.99')

# SOUTH row with date that looks valid but Feb 30 doesn't exist -> drop
lines.append('02-30-2024\tSouth\tElectronics\tUSB Drive\t50\t12.99')

# Row with quantity as float (3.5 units) - should this be valid? 
# Instructions say "valid positive numbers" so 3.5 is valid, keep it
lines.append('2024-03-23,East,Furniture,Drawer Unit,3.5,89.00')

# Row with price = 0 (free item) - price is valid positive? 0 is not positive -> drop
lines.append('2024-03-24,East,Stationery,Free Sample,10,0.00')

# Row that has an extra column (7 fields instead of 6) in comma-delimited
lines.append('2024-03-31,East,Electronics,Cable,USB-C,5,12.99')

# Write as latin-1 encoded with UTF-8 BOM prefix
with open('/app/data/sales_raw.csv', 'wb') as f:
    f.write(b'\xef\xbb\xbf')
    for i, line in enumerate(lines):
        encoded_line = line.encode('latin-1')
        f.write(encoded_line)
        f.write(b'\n')

print("Generated corrupted CSV at /app/data/sales_raw.csv")
