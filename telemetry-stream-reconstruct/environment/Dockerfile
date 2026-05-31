FROM ghcr.io/laude-institute/t-bench/python-3-13:20250620

WORKDIR /app

# Copy and run data generator, then delete it
COPY environment/generate_data.py /app/generate_data.py
RUN python /app/generate_data.py && rm -f /app/generate_data.py

# Copy instruction
COPY instruction.md /app/instruction.md

# Copy tests
COPY tests/test.sh /app/tests/test.sh
COPY tests/test_outputs.py /app/tests/test_outputs.py
RUN chmod +x /app/tests/test.sh

# Verify files are in place
RUN test -f /app/telemetry.bin && \
    test -f /var/lib/tbench/.reference.json && \
    test ! -f /app/generate_data.py
