from django.apps import apps
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand
from django.db.models import FileField

from apps.core.models import StoredUpload
from apps.core.storage import DurableUploadStorage, MAX_DATABASE_UPLOAD


class Command(BaseCommand):
    help = 'Copy referenced local uploads up to 10 MB into durable database storage; never deletes originals.'

    def handle(self, *args, **options):
        if not isinstance(default_storage, DurableUploadStorage):
            self.stdout.write('Durable database uploads are disabled; existing storage retained.')
            return
        names = set()
        for model in apps.get_models():
            for field in model._meta.fields:
                if isinstance(field, FileField):
                    names.update(model.objects.exclude(**{field.name: ''}).values_list(field.name, flat=True))
        saved = missing = large = 0
        for name in names:
            if not name or StoredUpload.objects.filter(pk=name).exists():
                continue
            try:
                if default_storage.local.size(name) > MAX_DATABASE_UPLOAD:
                    large += 1
                    continue
                with default_storage.local.open(name, 'rb') as source:
                    payload = source.read(MAX_DATABASE_UPLOAD + 1)
                if len(payload) > MAX_DATABASE_UPLOAD:
                    large += 1
                    continue
                _, created = StoredUpload.objects.get_or_create(name=name, defaults={'content': payload, 'size': len(payload)})
                saved += int(created)
            except FileNotFoundError:
                missing += 1
        self.stdout.write(f'Preserved {saved} uploads; {missing} missing originals; {large} large files remain in persistent media.')
