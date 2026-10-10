"""Copy local media preserving DB object keys; never remove or overwrite files."""
import hashlib
import io
from pathlib import Path
import boto3
import environ
from botocore.exceptions import ClientError
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from config.r2_storage import r2_options
from apps.core.models import StoredUpload


def digest(stream):
    value = hashlib.sha256()
    for chunk in iter(lambda: stream.read(1024*1024), b''): value.update(chunk)
    return value.hexdigest()

class Command(BaseCommand):
    help = 'Dry-run by default. --apply copies local media to private R2, verifies hashes, and preserves local files.'

    def add_arguments(self, parser):
        parser.add_argument('--apply', action='store_true')

    def handle(self, *args, **options):
        root = Path(settings.MEDIA_ROOT).resolve()
        files = [p for p in root.rglob('*') if p.is_file() and not p.is_symlink()]
        db_count = StoredUpload.objects.count()
        self.stdout.write(f'{len(files)} local files and {db_count} durable uploads found. Originals and database paths will be preserved.')
        if not options['apply']:
            self.stdout.write('Dry run. Back up DB/media, then use --apply with backend R2 credentials.')
            return
        cfg = r2_options(environ.Env())
        client = boto3.client('s3', endpoint_url=cfg['endpoint_url'], region_name='auto',
            aws_access_key_id=cfg['access_key'], aws_secret_access_key=cfg['secret_key'],
            config=cfg['client_config'])
        verified = 0
        try:
            def sources():
                for path in files:
                    yield path.relative_to(root).as_posix(), path.open('rb')
                for row in StoredUpload.objects.iterator(chunk_size=1):
                    yield row.name, io.BytesIO(bytes(row.content))
            for key, stream in sources():
                with stream as source:
                    local_hash = digest(source)
                    source.seek(0)
                    try:
                        existing = client.get_object(Bucket=cfg['bucket_name'], Key=key)
                    except ClientError as exc:
                        if exc.response['Error']['Code'] not in ['NoSuchKey', '404']: raise
                        client.upload_fileobj(source, cfg['bucket_name'], key, ExtraArgs={'CacheControl':'private, no-store'})
                        existing = client.get_object(Bucket=cfg['bucket_name'], Key=key)
                body = existing['Body']
                try: remote_hash = digest(body)
                finally: body.close()
                if remote_hash != local_hash:
                    raise CommandError('An existing remote key has different content. No overwrite performed. Investigate before enabling R2.')
                verified += 1
        except CommandError:
            raise
        except Exception:
            raise CommandError('R2 copy failed. Originals remain available. Check credentials/network and retry; matching objects are reused.') from None
        self.stdout.write(self.style.SUCCESS(f'{verified} files verified. Enable R2_ENABLED=true and test protected file access before changing traffic.'))
