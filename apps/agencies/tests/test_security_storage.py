from unittest.mock import patch
from django.test import SimpleTestCase
from django.core.exceptions import ImproperlyConfigured
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.exceptions import ValidationError
from apps.agencies.api.serializers import validate_document, validate_image
from config.r2_storage import r2_options

class StorageSecurityTests(SimpleTestCase):
    def test_r2_is_private_and_server_credentials_are_required(self):
        values={'R2_ACCOUNT_ID':'a'*32,'R2_BUCKET_NAME':'private-documents','R2_ACCESS_KEY_ID':'test-access','R2_SECRET_ACCESS_KEY':'test-secret'}
        options=r2_options(lambda key,default='':values.get(key,default))
        self.assertTrue(options['querystring_auth']);self.assertIsNone(options['default_acl'])
        self.assertIsNone(options['custom_domain']);self.assertFalse(options['file_overwrite'])
        self.assertTrue(options['endpoint_url'].startswith('https://'))
        with self.assertRaises(ImproperlyConfigured):r2_options(lambda key,default='': '')
        values['R2_ACCOUNT_ID']='attacker.example/path'
        with self.assertRaises(ImproperlyConfigured):r2_options(lambda key,default='':values.get(key,default))

    def test_uploads_validate_contents_and_reset_stream(self):
        valid=SimpleUploadedFile('document.pdf',b'%PDF-1.4\n test',content_type='application/pdf')
        validate_document(valid);self.assertEqual(valid.tell(),0)
        for bad in [SimpleUploadedFile('fake.pdf',b'<html>secret</html>'),SimpleUploadedFile('fake.jpg',b'<script>bad</script>')]:
            with self.assertRaises(ValidationError):validate_document(bad)
