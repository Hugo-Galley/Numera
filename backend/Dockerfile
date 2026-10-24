FROM python:3.12-slim

WORKDIR /app

# Install build dependencies and curl for healthchecks
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    python3-dev \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt /app/requirements.txt
RUN pip install --no-cache-dir -r /app/requirements.txt \
    && apt-get purge -y --auto-remove gcc python3-dev

COPY . /app
