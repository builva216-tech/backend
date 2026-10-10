from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError
from django.core.exceptions import ValidationError
from apps.notifications.models import AppRelease
from apps.notifications.services import notify


class Command(BaseCommand):
    help = 'Publish a release and optionally create user update notifications. Does not upload or install an APK.'

    def add_arguments(self, parser):
        parser.add_argument('--app', choices=['main', 'admin'], required=True)
        parser.add_argument('--platform', choices=['android', 'ios'], default='android')
        parser.add_argument('--version-code', type=int, required=True)
        parser.add_argument('--version-name', required=True)
        parser.add_argument('--url', required=True)
        parser.add_argument('--notes', default='')
        parser.add_argument('--notify', action='store_true', help='Explicitly enqueue announcements for active users.')

    def handle(self, *args, **o):
        release, _ = AppRelease.objects.get_or_create(app=o['app'], platform=o['platform'],
            version_code=o['version_code'], defaults={'version_name': o['version_name'], 'update_url': o['url'], 'notes': o['notes']})
        release.version_name, release.update_url, release.notes = o['version_name'], o['url'], o['notes']
        release.published = True
        try: release.full_clean()
        except ValidationError as e: raise CommandError(str(e)) from e
        release.save()
        if o['notify']:
            users = get_user_model().objects.filter(is_active=True)
            users = users.filter(is_staff=True) if o['app'] == 'admin' else users.filter(is_staff=False)
            for user in users.iterator():
                notify(user=user, event_key=f'release:{release.pk}', kind='app_update',
                    title='A new version is available', body='Open notifications to review and install the update.')
        self.stdout.write(self.style.SUCCESS(f'Published {release.version_name} (build {release.version_code}).'))
