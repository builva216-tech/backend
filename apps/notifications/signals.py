from django.contrib.auth import get_user_model
from django.db.models.signals import post_save
from django.dispatch import receiver
from apps.bookings.models import BookingStatusEvent
from apps.agencies.models import AgencyVerificationSubmission
from apps.customer_verifications.models import CustomerVerificationSubmission
from .services import booking_event, notify


@receiver(post_save, sender=BookingStatusEvent)
def status_changed(sender, instance, created, **kwargs):
    if created:
        # Inbox + outbox rows share the booking transaction; rollback removes both.
        booking_event(instance)


@receiver(post_save, sender=AgencyVerificationSubmission)
@receiver(post_save, sender=CustomerVerificationSubmission)
def verification_submitted(sender, instance, created, **kwargs):
    if created:
        for staff in get_user_model().objects.filter(is_staff=True, is_active=True).iterator():
            notify(user=staff, event_key=f'verification:{sender._meta.label_lower}:{instance.pk}',
                kind='verification', title='New verification request',
                body='Open the verification dashboard to review the request.')
