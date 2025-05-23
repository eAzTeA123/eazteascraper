FROM python:3.12-slim

WORKDIR /app

RUN apt-get update && apt-get install -y \
    build-essential \
    git \
    curl \
    libcurl4-openssl-dev \
    libssl-dev \
    && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/eAzTeA123/eazteascraper .

RUN pip install flask curl-cffi requests gunicorn httpx h2

CMD ["gunicorn", "app:app"]
