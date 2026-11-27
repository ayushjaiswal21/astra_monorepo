# Production image for astra (AstraLearn). Not build-tested in this sandbox
# (Docker isn't installed here) - syntax/structure verified by hand against
# the Dockerfile reference; see the deployment report for what to re-check
# on the first real build.
FROM python:3.11-slim

# Prevent .pyc files and force stdout/stderr to be unbuffered (so `docker logs`
# shows gunicorn/celery output immediately instead of being stdio-buffered).
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# psycopg2-binary doesn't need libpq-dev at runtime, but build-essential/libpq-dev
# are kept for any package here that compiles from source; remove if you trim
# requirements.txt to pure-wheel packages only.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# collectstatic needs real settings (SECRET_KEY, DATABASE_URL, etc.) at
# runtime, but only *reads* STATIC_URL/STATIC_ROOT/STATICFILES_STORAGE and
# writes to staticfiles/ - it does not touch the database. DJANGO_SETTINGS
# values unrelated to static files are irrelevant here, but SECRET_KEY must
# still be set to something (any string) for settings.py to import when
# DEBUG=False. Using a build-time dummy keeps real secrets out of image layers.
ENV DEBUG=False
ENV SECRET_KEY=build-time-only-placeholder-not-used-at-runtime
RUN python manage.py collectstatic --noinput

# Real runtime SECRET_KEY, DATABASE_URL, ALLOWED_HOSTS, etc. are injected as
# environment variables when the container is run (docker run -e / docker
# compose env_file / Oracle Cloud instance config) - never baked into the image.

EXPOSE 8000

# gunicorn, not manage.py runserver - the dev server is single-threaded and
# not meant to face real traffic. Run `python manage.py migrate` as a
# separate startup step (entrypoint script or orchestrator "release" hook)
# before this starts, since this image doesn't run migrations itself.
CMD ["gunicorn", "astralearn.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "3"]
