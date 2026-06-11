FROM python:3.12-slim

WORKDIR /app

RUN pip install --no-cache-dir "uptime-kuma-api==1.2.1" "PyYAML==6.0.2"

COPY provision.py /app/provision.py

CMD ["python", "/app/provision.py"]
