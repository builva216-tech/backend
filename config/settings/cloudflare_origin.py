"""Settings for a normal Python origin behind Cloudflare Tunnel, not Workers."""
from .production import *  # noqa: F403
MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(1, 'whitenoise.middleware.WhiteNoiseMiddleware')
CSRF_TRUSTED_ORIGINS = [f'https://{host}' for host in ALLOWED_HOSTS if host not in ['localhost', '127.0.0.1']]
SECURE_HSTS_SECONDS = 300  # Increase only after HTTPS/domain verification.
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False

SECURE_SSL_REDIRECT = True
if 'STORAGES' not in globals():
    STORAGES = {'default': {'BACKEND': 'django.core.files.storage.FileSystemStorage'}}
STORAGES['staticfiles'] = {'BACKEND': 'whitenoise.storage.CompressedManifestStaticFilesStorage'}
