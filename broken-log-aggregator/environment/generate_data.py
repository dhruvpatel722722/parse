#!/usr/bin/env python3
"""Generate a ~1MB corpus with structured repeating patterns.

The corpus is designed so that:
- Simple Huffman alone won't hit 2.5x (gets ~1.8x on English text)
- Simple RLE alone won't work (not enough consecutive repeats)
- LZ77/LZ78 + Huffman or a good dictionary approach is needed
- The patterns are structured enough that a well-tuned approach CAN hit 2.5x
"""
import os
import random
import struct

random.seed(2024)

os.makedirs("/app/data", exist_ok=True)
os.makedirs("/app/output", exist_ok=True)

# Build corpus from templates with repeating structures
templates = [
    "ERROR [{service}] {timestamp} - Connection to {host}:{port} failed after {n} retries\n",
    "INFO [{service}] {timestamp} - Request completed in {ms}ms status={status}\n",
    "WARN [{service}] {timestamp} - Memory usage at {pct}% threshold={thresh}%\n",
    "DEBUG [{service}] {timestamp} - Cache hit ratio: {ratio} keys={keys}\n",
    "ERROR [{service}] {timestamp} - Timeout waiting for response from {host}\n",
    "INFO [{service}] {timestamp} - Health check passed latency={ms}ms\n",
    "WARN [{service}] {timestamp} - Disk usage {pct}% on volume {vol}\n",
    "INFO [{service}] {timestamp} - User {user} authenticated via {method}\n",
    "ERROR [{service}] {timestamp} - Failed to parse config: {reason}\n",
    "DEBUG [{service}] {timestamp} - Query executed in {ms}ms rows={rows}\n",
    "INFO [{service}] {timestamp} - Batch job {job} completed {n} items\n",
    "WARN [{service}] {timestamp} - Rate limit {n}/s exceeded for client {client}\n",
    "ERROR [{service}] {timestamp} - Database connection pool exhausted ({n}/{max})\n",
    "INFO [{service}] {timestamp} - Deployed version {ver} to {env}\n",
    "DEBUG [{service}] {timestamp} - TLS handshake with {host}:{port} cipher={cipher}\n",
]

services = ["auth-api", "gateway", "payment-svc", "user-svc", "order-svc",
            "inventory", "notification", "scheduler", "analytics", "cache-mgr"]
hosts = ["db-primary.internal", "db-replica-01.internal", "redis-cluster.internal",
         "kafka-broker-1.internal", "s3-gateway.internal", "vault.internal"]
ports = ["5432", "6379", "9092", "8443", "3306", "27017"]
methods = ["oauth2", "jwt", "api-key", "mTLS", "saml", "ldap"]
envs = ["production", "staging", "canary", "us-east-1", "eu-west-2"]
ciphers = ["TLS_AES_256_GCM_SHA384", "TLS_CHACHA20_POLY1305_SHA256", "ECDHE-RSA-AES128"]
reasons = ["invalid JSON at line 42", "missing required field 'timeout'",
           "unexpected token in section [database]", "duplicate key 'port'",
           "schema version mismatch (expected 3, got 2)"]
jobs = ["daily-report", "cleanup-sessions", "sync-inventory", "rebuild-index",
        "export-metrics", "rotate-logs", "backup-db", "prune-cache"]
users = ["admin", "service-account", "deploy-bot", "monitoring", "readonly-user"]
clients = ["10.0.1.100", "10.0.2.55", "192.168.1.200", "172.16.0.42"]
volumes = ["/data", "/var/log", "/tmp", "/mnt/storage", "/opt/app"]
versions = ["v2.14.3", "v2.14.4", "v2.15.0-rc1", "v3.0.0-beta", "v2.13.9"]

corpus_parts = []
target_size = 1024 * 1024  # ~1MB
current_size = 0

while current_size < target_size:
    template = random.choice(templates)
    day = random.randint(1, 28)
    month = random.randint(1, 12)
    hour = random.randint(0, 23)
    minute = random.randint(0, 59)
    second = random.randint(0, 59)
    
    line = template.format(
        service=random.choice(services),
        timestamp=f"2024-{month:02d}-{day:02d}T{hour:02d}:{minute:02d}:{second:02d}Z",
        host=random.choice(hosts),
        port=random.choice(ports),
        n=random.randint(1, 100),
        ms=random.randint(1, 5000),
        status=random.choice([200, 201, 204, 301, 400, 401, 403, 404, 500, 502, 503]),
        pct=random.randint(50, 99),
        thresh=random.choice([75, 80, 85, 90, 95]),
        ratio=f"0.{random.randint(60, 99)}",
        keys=random.randint(100, 99999),
        vol=random.choice(volumes),
        user=random.choice(users),
        method=random.choice(methods),
        reason=random.choice(reasons),
        job=random.choice(jobs),
        client=random.choice(clients),
        max=random.choice([20, 50, 100]),
        ver=random.choice(versions),
        env=random.choice(envs),
        cipher=random.choice(ciphers),
        rows=random.randint(0, 50000),
    )
    corpus_parts.append(line)
    current_size += len(line)

corpus = "".join(corpus_parts).encode("utf-8")

# Pad or trim to exactly target
if len(corpus) > target_size:
    corpus = corpus[:target_size]

with open("/app/data/corpus.bin", "wb") as f:
    f.write(corpus)

print(f"Generated corpus: {len(corpus)} bytes ({len(corpus)/1024:.1f} KB)")
print(f"Target compressed size: < {int(len(corpus) * 0.4)} bytes ({len(corpus)*0.4/1024:.1f} KB)")
