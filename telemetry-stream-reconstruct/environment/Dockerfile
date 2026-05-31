FROM ghcr.io/laude-institute/t-bench/python-3-13:20250620

WORKDIR /app

# Copy and run data generator, then delete it
COPY generate_data.py /app/generate_data.py
RUN python /app/generate_data.py && rm -f /app/generate_data.py

# Verify data files are in place and generator is removed
RUN test -f /app/telemetry.bin && \
    test -f /var/lib/tbench/.reference.json && \
    test ! -f /app/generate_data.py
