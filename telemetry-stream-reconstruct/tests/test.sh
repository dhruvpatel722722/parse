#!/bin/bash
# Test harness for telemetry stream recovery
# Writes reward to /logs/verifier/reward.txt

mkdir -p /logs/verifier

# Install test dependencies
pip install pytest==8.3.4 -q

# Run the Python test suite
pytest /app/tests/test_outputs.py -v
exit_code=$?

if [ $exit_code -eq 0 ]; then
    echo "1.0" > /logs/verifier/reward.txt
    echo "ALL TESTS PASSED"
else
    echo "0.0" > /logs/verifier/reward.txt
    echo "TESTS FAILED"
fi

exit 0
