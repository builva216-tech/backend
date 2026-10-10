"""Retry saved reports without holding up the user's HTTP request."""
import logging
import threading
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMessage
from django.db import close_old_connections, transaction
from django.utils import timezone

from apps.core.models import BugReport

logger = logging.getLogger(__name__)
SUPPORT_EMAIL = 'builva.216@gmail.com'
NON_DELIVERY_BACKENDS = {
    'django.core.mail.backends.console.EmailBackend',
    'django.core.mail.backends.dummy.EmailBackend',
    'django.core.mail.backends.locmem.EmailBackend',
    'django.core.mail.backends.filebased.EmailBackend',
}


def deliver_next_report():
    now = timezone.now()
    with transaction.atomic():
        report = (BugReport.objects.select_for_update(skip_locked=True)
                  .filter(email_status='queued', next_delivery_at__lte=now)
                  .order_by('created_at').first())
        if report is None:
            return False
        report.email_attempts += 1
        try:
            if not settings.DEBUG and settings.EMAIL_BACKEND in NON_DELIVERY_BACKENDS:
                raise ValueError('Email backend does not deliver mail.')
            message = EmailMessage(
                subject=f'[CarRent TN bug] {report.title}',
                body=(f'Report ID: {report.pk}\nReporter: {report.reporter_name}\n'
                      f'Email: {report.reporter_email}\nRole: {report.reporter_role}\n'
                      f'Version: {report.app_version}\nPlatform: {report.platform}\n\n'
                      f'Title: {report.title}\n\nDescription:\n{report.description}\n\n'
                      f'Steps:\n{report.steps or "Not supplied"}\n'),
                from_email=settings.DEFAULT_FROM_EMAIL, to=[SUPPORT_EMAIL],
                reply_to=[report.reporter_email],
            )
            if message.send(fail_silently=False) != 1:
                raise OSError('Email was not accepted.')
        except Exception as exc:
            # Never log report text, credentials, email addresses or SMTP responses.
            logger.warning('Bug report delivery failed (%s).', type(exc).__name__)
            report.email_status = 'failed' if report.email_attempts >= 10 else 'queued'
            report.next_delivery_at = now + timedelta(seconds=min(3600, 30 * 2 ** report.email_attempts))
        else:
            report.email_status = 'sent'
            report.emailed_at = timezone.now()
        report.save(update_fields=['email_attempts', 'email_status', 'next_delivery_at', 'emailed_at'])
    return True


def start_report_worker():
    stop = threading.Event()

    def run():
        while not stop.wait(15):
            close_old_connections()
            try:
                for _ in range(5):
                    if stop.is_set() or not deliver_next_report():
                        break
            except Exception as exc:
                logger.warning('Bug report worker unavailable (%s).', type(exc).__name__)
            finally:
                close_old_connections()

    threading.Thread(target=run, name='bug-report-mail', daemon=True).start()
    return stop
