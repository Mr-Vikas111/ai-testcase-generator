FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app

COPY requirements.txt ./
RUN pip install --upgrade pip && pip install -r requirements.txt

COPY app ./app
COPY .github ./.github
COPY webhook_server.py ./
COPY run_app.sh ./

EXPOSE 5055

CMD ["python", "webhook_server.py", "--host", "0.0.0.0", "--port", "5055"]
