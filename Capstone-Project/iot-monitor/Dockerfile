FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/app/src

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY alembic.ini .
COPY src/ ./src
COPY db/ ./db
COPY scripts/ ./scripts

# run as a normal user, not root
RUN useradd --create-home --uid 10001 app \
    && mkdir -p /app/reports_output \
    && chown -R app:app /app
USER app

EXPOSE 8000

HEALTHCHECK --interval=30s --timeout=5s --start-period=40s --retries=3 \
    CMD python -c "import urllib.request,sys; sys.exit(0 if urllib.request.urlopen('http://localhost:8000/health', timeout=4).status == 200 else 1)"

# 1) apply database migrations  2) optionally seed (SEED_ON_START=true)  3) start the server
CMD ["sh", "-c", "alembic upgrade head && if [ \"$SEED_ON_START\" = \"true\" ]; then python scripts/seed.py; fi && exec uvicorn app.main:app --host 0.0.0.0 --port 8000 --workers ${WEB_CONCURRENCY:-1}"]
