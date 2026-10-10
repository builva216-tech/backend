import io
import tempfile
from pathlib import Path
from unittest.mock import Mock, patch

from botocore.exceptions import ClientError
from django.core.management import call_command
from django.test import TestCase, override_settings

from apps.core.models import StoredUpload


class R2ArchiveCopyTests(TestCase):
    def test_copy_includes_database_uploads_and_preserves_originals(self):
        remote = {}
        client = Mock()
        def read_object(**kwargs):
            key = kwargs['Key']
            if key not in remote:
                raise ClientError({'Error': {'Code': 'NoSuchKey'}}, 'GetObject')
            return {'Body': io.BytesIO(remote[key])}
        def upload(stream, bucket, key, ExtraArgs):
            self.assertEqual(ExtraArgs, {'CacheControl': 'private, no-store'})
            remote[key] = stream.read()
        client.get_object.side_effect = read_object
        client.upload_fileobj.side_effect = upload
        cfg = {'endpoint_url': 'https://example.invalid', 'bucket_name': 'private',
               'access_key': 'test-only', 'secret_key': 'test-only', 'client_config': None}
        with tempfile.TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root), \
            patch('apps.core.management.commands.migrate_media_to_r2.r2_options', return_value=cfg), \
            patch('apps.core.management.commands.migrate_media_to_r2.boto3.client', return_value=client):
            Path(root, 'old.png').write_bytes(b'old image')
            StoredUpload.objects.create(name='verification/doc.pdf', content=b'%PDF-test', size=9)
            call_command('migrate_media_to_r2', apply=True)
            self.assertEqual(remote, {'old.png': b'old image', 'verification/doc.pdf': b'%PDF-test'})
            self.assertEqual(Path(root, 'old.png').read_bytes(), b'old image')
            self.assertTrue(StoredUpload.objects.filter(name='verification/doc.pdf').exists())
            call_command('migrate_media_to_r2', apply=True)
            self.assertEqual(client.upload_fileobj.call_count, 2)

    def test_dry_run_does_not_contact_object_storage(self):
        with tempfile.TemporaryDirectory() as root, override_settings(MEDIA_ROOT=root), \
            patch('apps.core.management.commands.migrate_media_to_r2.boto3.client') as client:
            StoredUpload.objects.create(name='doc.pdf', content=b'%PDF-test', size=9)
            call_command('migrate_media_to_r2')
            client.assert_not_called()
