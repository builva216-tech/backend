import tempfile

from django.core.files.base import ContentFile
from django.core.cache import cache
from django.core.management import call_command
from django.test import TestCase, override_settings
from django.urls import reverse

from apps.core.models import StoredUpload
from apps.core.storage import DurableUploadStorage
from apps.admin_portal.tests import test_agency_verification_api as verification_tests

DURABLE_STORAGES = {
    'default': {'BACKEND': 'apps.core.storage.DurableUploadStorage'},
    'staticfiles': {'BACKEND': 'django.contrib.staticfiles.storage.StaticFilesStorage'},
}


class DurableStorageTests(TestCase):
    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_saved_bytes_survive_a_new_empty_media_folder(self):
        storage = DurableUploadStorage()
        name = storage.save('private/test.pdf', ContentFile(b'%PDF-1.4 test'))
        self.assertEqual(StoredUpload.objects.get(pk=name).size, 13)
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp()):
            other = DurableUploadStorage()
            self.assertTrue(other.exists(name))
            with other.open(name) as document:
                self.assertEqual(document.read(), b'%PDF-1.4 test')
        self.assertTrue(storage.url(name).startswith('/api/v1/admin/uploads/'))

    @override_settings(MEDIA_ROOT=tempfile.mkdtemp())
    def test_existing_local_files_are_readable_and_duplicates_preserved(self):
        storage = DurableUploadStorage()
        storage.local.save('legacy.png', ContentFile(b'legacy image'))
        with storage.open('legacy.png') as document:
            self.assertEqual(document.read(), b'legacy image')
        name = storage.save('new.pdf', ContentFile(b'%PDF-one'))
        second = storage.save('new.pdf', ContentFile(b'%PDF-two'))
        self.assertNotEqual(name, second)
        self.assertEqual(StoredUpload.objects.get(pk=name).content, b'%PDF-one')


@override_settings(STORAGES=DURABLE_STORAGES, MEDIA_ROOT=tempfile.mkdtemp())
class DurableDocumentApiTests(verification_tests.AdminAgencyVerificationApiTests):
    def setUp(self):
        super().setUp()
        cache.clear()

    def test_pdf_and_png_download_with_binary_accept_and_cors_after_restart(self):
        self._submit_agency_documents()
        self.assertEqual(StoredUpload.objects.count(), 5)
        self._authenticate_admin()
        agency = self.agency_user.agency_profile
        endpoint = lambda kind: reverse('admin-portal-api:agency-document', kwargs={'agency_profile_id': agency.pk, 'document_type': kind})
        with override_settings(MEDIA_ROOT=tempfile.mkdtemp(), CORS_ALLOWED_ORIGINS=['http://localhost:7358']):
            pdf = self.client.get(endpoint('business-registration'), HTTP_ACCEPT='application/pdf', HTTP_ORIGIN='http://localhost:7358')
            self.assertEqual(pdf.status_code, 200)
            self.assertTrue(pdf.content.startswith(b'%PDF'))
            self.assertEqual(pdf['Content-Type'], 'application/pdf')
            self.assertEqual(pdf['Access-Control-Allow-Origin'], 'http://localhost:7358')
            image = self.client.get(endpoint('responsible-person-cin-recto'), HTTP_ACCEPT='image/*')
            self.assertEqual(image.status_code, 200)
            self.assertEqual(image['Content-Type'], 'image/png')
            self.assertTrue(image.content.startswith(b'\x89PNG'))
        self.assertEqual(self.client.post(reverse('admin-portal-api:agency-approve', kwargs={'agency_profile_id': agency.pk}), {}, format='json').status_code, 200)

    def test_missing_upload_has_clear_error_blocks_approval_but_allows_rejection(self):
        self._submit_agency_documents()
        StoredUpload.objects.all().delete()
        self._authenticate_admin()
        agency = self.agency_user.agency_profile
        response = self.client.get(reverse('admin-portal-api:agency-document', kwargs={'agency_profile_id': agency.pk, 'document_type': 'business-registration'}))
        self.assertEqual(response.status_code, 404)
        self.assertIn('upload it again', str(response.data['detail']))
        self.assertEqual(self.client.post(reverse('admin-portal-api:agency-approve', kwargs={'agency_profile_id': agency.pk}), {}, format='json').status_code, 409)
        self.assertEqual(self.client.post(reverse('admin-portal-api:agency-reject', kwargs={'agency_profile_id': agency.pk}), {'reason': 'Files missing. Please upload the documents again.'}, format='json').status_code, 200)
        self._submit_agency_documents()
        self._authenticate_admin()
        self.assertEqual(self.client.post(reverse('admin-portal-api:agency-approve', kwargs={'agency_profile_id': agency.pk}), {}, format='json').status_code, 200)

    def test_private_uploads_cannot_be_downloaded_by_agency(self):
        self._submit_agency_documents()
        agency = self.agency_user.agency_profile
        self.client.force_authenticate(self.agency_user)
        response = self.client.get(reverse('admin-portal-api:agency-document', kwargs={'agency_profile_id': agency.pk, 'document_type': 'responsible-person-cin-recto'}), HTTP_ACCEPT='image/*')
        self.assertEqual(response.status_code, 403)

    def test_release_import_preserves_referenced_local_files(self):
        self._submit_agency_documents()
        for upload in StoredUpload.objects.all():
            DurableUploadStorage().local.save(upload.name, ContentFile(bytes(upload.content)))
        StoredUpload.objects.all().delete()
        call_command('preserve_local_uploads', verbosity=0)
        self.assertEqual(StoredUpload.objects.count(), 5)

    def test_django_admin_links_are_authenticated_and_no_public_media_route_exists(self):
        self._submit_agency_documents()
        upload = StoredUpload.objects.first()
        url = DurableUploadStorage().url(upload.name)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.get(url, HTTP_ACCEPT='image/*').status_code, 401)
        self.assertEqual(self.client.get('/media/' + upload.name).status_code, 404)
        self.client.force_authenticate(self.agency_user)
        self.assertEqual(self.client.get(url).status_code, 403)
        self.client.force_authenticate(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
        self.client.force_authenticate(None)
        self.client.force_login(self.admin)
        self.assertEqual(self.client.get(url).status_code, 200)
