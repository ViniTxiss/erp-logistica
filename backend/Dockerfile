FROM python:3.11-slim AS base

# Evita bytecode e buffer no stdout
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# Dependências do sistema (psycopg2 precisa de libpq)
RUN apt-get update && apt-get install -y --no-install-recommends \
    libpq-dev \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# ─── Estágio de desenvolvimento ───────────────────────────────────────────────
FROM base AS development

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/development.txt

COPY . .

EXPOSE 8000
CMD ["python", "manage.py", "runserver", "0.0.0.0:8000"]

# ─── Estágio de produção ──────────────────────────────────────────────────────
FROM base AS production

ARG SECRET_KEY
ARG DATABASE_URL

COPY requirements/ ./requirements/
RUN pip install --no-cache-dir -r requirements/production.txt

COPY . .

RUN DJANGO_SETTINGS_MODULE=config.settings.production python manage.py collectstatic --noinput

EXPOSE 8000
CMD ["sh", "-c", "export DJANGO_SETTINGS_MODULE=config.settings.production && python manage.py migrate --noinput && python manage.py create_admin --email=\"$DJANGO_SUPERUSER_EMAIL\" --password=\"$DJANGO_SUPERUSER_PASSWORD\" && gunicorn config.wsgi:application --bind 0.0.0.0:8000 --workers 3"]
