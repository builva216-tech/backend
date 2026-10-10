import uuid
from django.core.files.base import ContentFile
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.conf import settings

class Command(BaseCommand):
    help = 'Verify private R2 upload/read/delete; credentials and signed URLs are never printed.'

    def handle(self, *args, **options):
        if settings.STORAGES['default']['BACKEND'] != 'storages.backends.s3.S3Storage':
            raise CommandError('R2 is not enabled. Set R2_ENABLED=true in the backend environment.')
        name = None
        try:
            name = default_storage.save(f'_connectivity/{uuid.uuid4()}.txt', ContentFile(b'carrent-r2-check'))
            with default_storage.open(name, 'rb') as file:
                if file.read() != b'carrent-r2-check': raise CommandError('R2 read-back mismatch.')
        except CommandError:
            raise
        except Exception:
            raise CommandError('R2 connection failed. Check bucket, scoped credentials and network.') from None
        finally:
            if name:
                try: default_storage.delete(name)
                except Exception: self.stderr.write('Cleanup failed; remove the temporary _connectivity object from the bucket.')
        self.stdout.write(self.style.SUCCESS('Private R2 upload/read/delete passed.'))
