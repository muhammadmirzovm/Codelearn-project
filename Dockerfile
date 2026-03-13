FROM python:3.12-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    libpq-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /code

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

RUN mkdir -p /code/static && \
    DJANGO_SETTINGS_MODULE=codelearn.settings.production \
    SECRET_KEY=build-time-dummy-key \
    DATABASE_URL=sqlite:///tmp/dummy.db \
    python manage.py collectstatic --no-input

EXPOSE 8000