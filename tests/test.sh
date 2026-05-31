#!/bin/bash
cd /app
python -m pytest /app/tests/test_outputs.py -v
