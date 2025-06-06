FROM python:3.11-slim

RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc python3-dev \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY . .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE 5000

CMD python -c "from app import app as application; application.run(host='0.0.0.0', port=5000, threaded=True)"
