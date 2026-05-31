#!/bin/bash
# Test harness for telemetry stream recovery
# Writes reward to /logs/verifier/reward.txt

mkdir -p /logs/verifier

# Run the Python test suite
python3 /app/tests/test_outputs.py
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "1.0" > /logs/verifier/reward.txt
    echo "ALL TESTS PASSED"
else
    echo "0.0" > /logs/verifier/reward.txt
    echo "TESTS FAILED"
fi

exit 0
