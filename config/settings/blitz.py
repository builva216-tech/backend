"""Django settings for Blitz HTTPS ingress."""
from .production import *  # noqa: F403

MIDDLEWARE = list(MIDDLEWARE)
MIDDLEWARE.insert(MIDDLEWARE.index("django.middleware.security.SecurityMiddleware") + 1,
                  "whitenoise.middleware.WhiteNoiseMiddleware")
CSRF_TRUSTED_ORIGINS = [x.strip() for x in env("CSRF_TRUSTED_ORIGINS", default="").split(",") if x.strip()]
SECURE_SSL_REDIRECT = env.bool("SECURE_SSL_REDIRECT", default=False)
SECURE_HSTS_SECONDS = 300
SECURE_HSTS_INCLUDE_SUBDOMAINS = False
SECURE_HSTS_PRELOAD = False
STORAGES = dict(globals().get("STORAGES", {"default": {"BACKEND": "django.core.files.storage.FileSystemStorage"}}))
STORAGES["staticfiles"] = {"BACKEND": "whitenoise.storage.CompressedManifestStaticFilesStorage"}
# Small uploads survive rebuilds without requiring a separate object-storage account.
# Existing R2 configurations retain their current storage and files.
if not env.bool('R2_ENABLED', default=False) and env.bool('DURABLE_UPLOADS_ENABLED', default=True):
    STORAGES['default'] = {'BACKEND': 'apps.core.storage.DurableUploadStorage'}
