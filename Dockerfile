FROM python:3.10-slim

WORKDIR /app

RUN apt-get update && apt-get install -y git build-essential && rm -rf /var/lib/apt/lists/*

RUN git clone https://github.com/deinname/pyarmor-app.git .

RUN pip install --no-cache-dir httpx h2 flask requests

ENV PYARMOR_RUNTIME_PATH=/app/pyarmor_runtime_00000

# Starte deine App
CMD ["python", "main.py"]
