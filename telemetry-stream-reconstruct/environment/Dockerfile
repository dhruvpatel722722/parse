FROM ghcr.io/laude-institute/t-bench/python-3-13:20250620

WORKDIR /app

# Install test dependencies (pinned)
RUN pip install pytest==8.3.4

# Copy and run data generator, then delete it
COPY generate_data.py /app/generate_data.py
RUN python /app/generate_data.py && rm -f /app/generate_data.py

# Copy instruction
COPY instruction.md /app/instruction.md

# Copy test files
COPY test.sh /app/tests/test.sh
COPY test_outputs.py /app/tests/test_outputs.py
RUN chmod +x /app/tests/test.sh

# Verify data files are in place and generator is removed
RUN test -f /app/telemetry.bin && \
    test -f /var/lib/tbench/.reference.json && \
    test ! -f /app/generate_data.py
