FROM python:3.11-slim

WORKDIR /app

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
