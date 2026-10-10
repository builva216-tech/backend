FROM python:3.12-slim
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 DJANGO_SETTINGS_MODULE=config.settings.cloudflare_origin
WORKDIR /app
COPY requirements ./requirements
COPY hosting ./hosting
RUN pip install --no-cache-dir -r hosting/requirements.txt
COPY . .
RUN cp hosting/cloudflare_origin.py config/settings/cloudflare_origin.py && useradd --create-home appuser && mkdir -p media staticfiles && chown -R appuser:appuser /app
USER appuser
EXPOSE 8000
CMD ["gunicorn", "config.wsgi:application", "--bind", "0.0.0.0:8000", "--workers", "2", "--timeout", "60", "--access-logfile", "-"]
