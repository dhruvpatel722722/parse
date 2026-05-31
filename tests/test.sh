#!/bin/bash
mkdir -p /logs/verifier
pytest /app/tests/test_outputs.py -v
if [ $? -eq 0 ]; then
    echo "1.0" > /logs/verifier/reward.txt
    echo "ALL TESTS PASSED"
else
    echo "0.0" > /logs/verifier/reward.txt
    echo "TESTS FAILED"
fi
exit 0
