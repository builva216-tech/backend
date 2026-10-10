#!/bin/sh
set -eu
: "${DJANGO_SECRET_KEY:?Set DJANGO_SECRET_KEY in Blitz Environment}"
: "${DATABASE_URL:?Connect PostgreSQL to this app}"
case "${1:-web}" in
  web)
    python manage.py collectstatic --noinput
    exec gunicorn config.wsgi:application --config hosting/gunicorn_conf.py --bind "0.0.0.0:${PORT:-8000}" --workers "${WEB_CONCURRENCY:-1}" --timeout 60 --access-logfile - --error-logfile -
    ;;
  release)
    python manage.py migrate --noinput
    python manage.py seed_tunisia_governorates
    python manage.py preserve_local_uploads
    ;;
  mail) exec python manage.py send_password_recovery_emails --watch ;;
  push) exec python manage.py send_push_notifications --watch ;;
  *) exec "$@" ;;
esac
