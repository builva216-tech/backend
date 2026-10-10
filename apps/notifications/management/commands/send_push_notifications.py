import time
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from apps.notifications.delivery import deliver_one


class Command(BaseCommand):
    help = 'Deliver queued FCM messages. The inbox works independently.'

    def add_arguments(self, parser):
        parser.add_argument('--watch', action='store_true')

    def handle(self, *args, **options):
        if not settings.FCM_ENABLED:
            raise CommandError('FCM is disabled. Configure FCM_ENABLED and FCM_CREDENTIALS_FILE first.')
        if not settings.FCM_CREDENTIALS_FILE:
            raise CommandError('Set FCM_CREDENTIALS_FILE to a mounted service-account JSON file.')
        self.stdout.write('Push worker started. Tokens and credentials are never printed.')
        try:
            while True:
                if not deliver_one():
                    if not options['watch']: break
                    time.sleep(5)
        except KeyboardInterrupt:
            pass
