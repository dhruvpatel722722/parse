FROM ghcr.io/laude-institute/t-bench/python-3-13:20250620

RUN apt-get update && apt-get install -y curl xxd && rm -rf /var/lib/apt/lists/*

RUN pip install pytest==8.4.2

WORKDIR /app

COPY generate_data.py /app/generate_data.py

RUN python /app/generate_data.py && rm -f /app/generate_data.py
