FROM python:3.11-slim

WORKDIR /app

# python:3.11-slim's baked-in openssl/ca-certificates can be stale enough to
# fail MongoDB Atlas's TLS handshake with a cryptic TLSV1_ALERT_INTERNAL_ERROR
# (confirmed in production: failed identically on every retry, against every
# shard, so not transient - a certifi CA bundle alone wasn't enough because
# the underlying system OpenSSL itself was the problem). Refreshing both to
# the image's current Debian package versions is the documented fix.
RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates openssl \
    && rm -rf /var/lib/apt/lists/*

# Install deps first for better layer caching. requirements.txt already pins
# --extra-index-url https://download.pytorch.org/whl/cpu so pip pulls the
# small CPU-only torch wheel instead of the much larger default CUDA build.
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8001

# Production ASGI invocation: multiple worker processes, no --reload.
# Each worker is a separate process and lazy-loads its own copy of the
# simplify-text transformer (~48MB) on first use - expected and safe.
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8001", "--workers", "4"]
