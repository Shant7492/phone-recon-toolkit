FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1

WORKDIR /app
COPY requirements.txt requirements-web.txt ./
RUN pip install -r requirements-web.txt

COPY . .
RUN useradd --create-home --uid 10001 app && chown -R app:app /app
USER app

# Render/Fly/Railway inject PORT; Hugging Face Spaces expects 7860.
ENV PORT=8000
EXPOSE 8000

# --no-access-log: request lines must never be persisted.
CMD ["sh", "-c", "exec uvicorn web.app:app --host 0.0.0.0 --port ${PORT} --no-access-log"]
