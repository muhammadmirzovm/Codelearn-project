FROM python:3.12-slim

# Install system deps + language runtimes
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    gcc \
    g++ \
    nodejs \
    npm \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Collect static files at build time
RUN mkdir -p /code/static && \
    DJANGO_SETTINGS_MODULE=codelearn.settings.production \
    SECRET_KEY=build-time-dummy-key \
    GOOGLE_CLIENT_ID=build-placeholder \
    GOOGLE_CLIENT_SECRET=build-placeholder \
    DATABASE_URL=sqlite:///tmp/dummy.db \
    python manage.py collectstatic --no-input

EXPOSE 8000

CMD ["sh", "-c", "python manage.py migrate --noinput && exec daphne -b 0.0.0.0 -p ${PORT:-8000} codelearn.asgi:application"]
