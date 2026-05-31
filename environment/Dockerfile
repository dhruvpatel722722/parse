FROM ghcr.io/laude-institute/t-bench/python-3-13:20250620

WORKDIR /app

RUN pip install pytest==8.3.4

COPY generate_data.py /app/generate_data.py
RUN python /app/generate_data.py && rm -f /app/generate_data.py

COPY instruction.md /app/instruction.md
COPY test.sh /app/tests/test.sh
COPY test_outputs.py /app/tests/test_outputs.py
RUN chmod +x /app/tests/test.sh

RUN test -f /app/readings.bin && \
    test -f /var/lib/tbench/.reference.json && \
    test ! -f /app/generate_data.py
