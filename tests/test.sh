#!/bin/bash
cd /app

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
if [ "$SCRIPT_DIR" != "/app/tests" ]; then
    mkdir -p /app/tests
    cp "$SCRIPT_DIR"/*.py /app/tests/ 2>/dev/null || true
fi

mkdir -p /logs/verifier
uv run pytest tests/ -v
if [ $? -eq 0 ]; then
    echo "1" > /logs/verifier/reward.txt
else
    echo "0" > /logs/verifier/reward.txt
fi
exit 0
