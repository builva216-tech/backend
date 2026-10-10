"""Durable storage for small uploads on hosts with disposable containers.

Files up to 10 MB live in PostgreSQL. Existing local files remain readable;
larger videos use the persistent media folder. R2 remains the preferred option
for a large media library and is never overridden by this backend.
"""
import io
import logging

from django.core.files import File
from django.core.files.storage import FileSystemStorage, Storage
from django.utils.deconstruct import deconstructible
from django.urls import reverse

from apps.core.models import StoredUpload

logger = logging.getLogger(__name__)
MAX_DATABASE_UPLOAD = 10 * 1024 * 1024


@deconstructible
class DurableUploadStorage(Storage):
    def __init__(self):
        self.local = FileSystemStorage()

    def _open(self, name, mode='rb'):
        if mode not in ('r', 'rb'):
            raise ValueError('Uploads are read-only after saving.')
        row = StoredUpload.objects.filter(pk=name).first()
        if row is not None:
            return File(io.BytesIO(bytes(row.content)), name=name)
        return self.local.open(name, mode)

    def _save(self, name, content):
        if content.size > MAX_DATABASE_UPLOAD:
            return self.local.save(name, content)
        content.seek(0)
        payload = content.read(MAX_DATABASE_UPLOAD + 1)
        if len(payload) > MAX_DATABASE_UPLOAD:
            raise ValueError('Upload exceeds the database storage limit.')
        StoredUpload.objects.create(name=name, content=payload, size=len(payload))
        return name

    def exists(self, name):
        return StoredUpload.objects.filter(pk=name).exists() or self.local.exists(name)

    def size(self, name):
        size = StoredUpload.objects.filter(pk=name).values_list('size', flat=True).first()
        return self.local.size(name) if size is None else size

    def delete(self, name):
        StoredUpload.objects.filter(pk=name).delete()
        self.local.delete(name)

    def url(self, name):
        # Django Admin's file widget needs a link. This endpoint requires admin
        # authentication, including the existing Django Admin session cookie.
        return reverse('admin-portal-api:stored-upload', kwargs={'upload_name': name})
