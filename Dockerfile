FROM python:3.10-slim

RUN apt-get update && apt-get install -y \
    git \
    build-essential \
    && rm -rf /var/lib/apt/lists/*
WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

RUN git clone https://github.com/eAzTeA123/eazteascraper.git

COPY . .

EXPOSE 7860

CMD ["python", "app.py"]
