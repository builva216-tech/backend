FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.blitz PORT=8000
WORKDIR /app
COPY requirements ./requirements
COPY hosting/requirements.txt ./hosting/requirements.txt
RUN pip install --no-cache-dir -r hosting/requirements.txt
COPY . .
RUN useradd --uid 1000 --create-home appuser && mkdir -p media staticfiles && chown -R appuser:appuser /app && chmod +x blitz-entrypoint.sh
USER appuser
EXPOSE 8000
VOLUME ["/app/media"]
ENTRYPOINT ["/bin/sh", "/app/blitz-entrypoint.sh"]
CMD ["web"]
