from .base import *  # noqa: F403

DEBUG = True

EMAIL_BACKEND = "django.core.mail.backends.console.EmailBackend"

# Flutter Web is served from a random localhost development port.
# Only local browser origins are allowed here. Production settings do not
# inherit this file, so this does not open the production API to all origins.
CORS_ALLOWED_ORIGIN_REGEXES = [
    r"^http://localhost:\d+$",
    r"^http://127\.0\.0\.1:\d+$",
]
