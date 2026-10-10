"""Private Cloudflare R2 media, enabled explicitly in the backend environment."""
import re
from botocore.config import Config
from django.core.exceptions import ImproperlyConfigured


def r2_options(env):
    account = env('R2_ACCOUNT_ID', default='').strip()
    bucket = env('R2_BUCKET_NAME', default='').strip()
    access = env('R2_ACCESS_KEY_ID', default='').strip()
    secret = env('R2_SECRET_ACCESS_KEY', default='').strip()
    if not re.fullmatch(r'[0-9a-fA-F]{32}', account):
        raise ImproperlyConfigured('Set a valid R2_ACCOUNT_ID in the backend environment.')
    if not bucket or not access or not secret:
        raise ImproperlyConfigured('Private R2 requires bucket name and backend-only credentials.')
    return {
        'bucket_name': bucket,
        'endpoint_url': f'https://{account}.r2.cloudflarestorage.com',
        'access_key': access, 'secret_key': secret,
        'region_name': 'auto', 'signature_version': 's3v4',
        'default_acl': None, 'querystring_auth': True, 'querystring_expire': 60,
        'file_overwrite': False, 'custom_domain': None,
        'client_config': Config(signature_version='s3v4', connect_timeout=5, read_timeout=20,
            retries={'max_attempts': 2, 'mode': 'standard'},
            request_checksum_calculation='when_required', response_checksum_validation='when_required'),
        'object_parameters': {'CacheControl': 'private, no-store'},
    }
