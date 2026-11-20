# syntax=docker/dockerfile:1
# Build (from the repository root):
#   docker build -t poll-backend:1.0 app/backend
#   docker build --build-arg APP_VERSION=1.1 -t poll-backend:1.1 app/backend
#   docker build --build-arg APP_VERSION=1.2 --build-arg BROKEN=true -t poll-backend:1.2-broken app/backend
FROM python:3.12-slim

ARG APP_VERSION=1.0
ARG BROKEN=false
ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    APP_VERSION=${APP_VERSION} \
    BROKEN=${BROKEN}

# A fixed numeric user, so Kubernetes can verify it is not root.
RUN groupadd -g 10001 app && useradd -u 10001 -g app -M -s /usr/sbin/nologin app

WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py tools.py ./

USER 10001:10001
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
