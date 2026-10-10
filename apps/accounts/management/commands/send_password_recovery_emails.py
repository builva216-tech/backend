import time

from django.core.management.base import BaseCommand
from django.db.models import Q
from django.utils import timezone

from apps.accounts.models import PasswordRecoveryChallenge
from apps.accounts.recovery import deliver_recovery_email


class Command(BaseCommand):
    help = "Deliver queued password recovery mail. Run --watch as a supervised worker, or schedule once per minute."

    def add_arguments(self, parser):
        parser.add_argument("--watch", action="store_true")
        parser.add_argument("--interval", type=int, default=5)

    def handle(self, *args, **options):
        while True:
            now = timezone.now()
            ids = (
                PasswordRecoveryChallenge.objects.filter(
                    user__isnull=False, delivery_attempts__lt=5
                )
                .filter(Q(next_delivery_at__lte=now) | Q(next_delivery_at__isnull=True))
                .filter(
                    Q(used_at__isnull=True, emailed_at__isnull=True, expires_at__gt=now)
                    | Q(used_at__isnull=False, notification_sent_at__isnull=True)
                )
                .order_by("created_at")
                .values_list("id", flat=True)[:100]
            )
            count = sum(deliver_recovery_email(value) for value in list(ids))
            if count:
                self.stdout.write(f"Delivered {count} recovery/security emails.")
            if not options["watch"]:
                break
            try:
                time.sleep(max(1, options["interval"]))
            except KeyboardInterrupt:
                break
