FROM python:3.11-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_DISABLE_PIP_VERSION_CHECK=1 \
    APP_ENV=production \
    AUTH_TRUST_UNVERIFIED_JWT=false \
    TRUST_PROXY_AUTH_HEADERS=false

WORKDIR /app
COPY requirements.txt ./requirements.txt
RUN pip install --no-cache-dir -r requirements.txt

RUN groupadd --gid 10001 edaverse \
    && useradd --uid 10001 --gid 10001 --no-create-home edaverse \
    && mkdir -p /app/data/datasets \
    && chown -R edaverse:edaverse /app/data
COPY --chown=edaverse:edaverse app ./app

USER 10001:10001
EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=30s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://127.0.0.1:8000/health', timeout=4)"
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
