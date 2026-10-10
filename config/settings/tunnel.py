"""Testing via Cloudflare Tunnel. Use an exact trusted hostname, no wildcard."""
from .base import *  # noqa: F403
DEBUG = False
SECURE_PROXY_SSL_HEADER = ('HTTP_X_FORWARDED_PROTO', 'https')
SESSION_COOKIE_SECURE = True
CSRF_COOKIE_SECURE = True
CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']]
EMAIL_BACKEND = 'django.core.mail.backends.console.EmailBackend'
SECURE_CONTENT_TYPE_NOSNIFF = True
X_FRAME_OPTIONS = 'DENY'
