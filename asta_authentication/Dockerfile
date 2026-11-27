FROM python:3.11-slim

WORKDIR /app

# System deps for psycopg2-binary's runtime libpq and building any wheels
# that lack prebuilt manylinux binaries.
RUN apt-get update && apt-get install -y --no-install-recommends \
        libpq5 \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# instance/ holds the local SQLite file - only relevant for local/dev runs
# (DATABASE_URL should point at Postgres in real deployments) but the
# directory must exist so a SQLite fallback doesn't crash on first write.
RUN mkdir -p instance

ENV FLASK_DEBUG=false \
    PYTHONUNBUFFERED=1

EXPOSE 5000

# eventlet worker class is required: Flask-SocketIO's chat namespace
# (chat_socket.py) needs an async worker to hold open long-lived WebSocket
# connections. The default sync worker would block one worker process per
# connected socket client and starve normal HTTP requests. -w 1 because
# eventlet's own greenlets handle concurrency within a single worker;
# running multiple eventlet workers needs a shared pub/sub (e.g. Redis) for
# Socket.IO's message queue, which this app does not yet have configured.
CMD ["gunicorn", "--worker-class", "eventlet", "-w", "1", "--bind", "0.0.0.0:5000", "app:app"]
