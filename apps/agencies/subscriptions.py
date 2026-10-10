from django.db import transaction
from django.utils import timezone
from rest_framework.exceptions import APIException
from .models import AgencyProfile, AgencySubscription, SubscriptionPlan
from .subscription_policy import evaluate, may_finish_booking


def plan_catalog():
    return {row.code: {'name': row.name, 'monthlyTnd': float(row.monthly_tnd),
                      'priceText': row.price_text or f'{row.monthly_tnd:g} TND / month',
                      'description': row.description, 'cars': row.cars, 'branches': row.branches,
                      'isActive': row.is_active, 'recommended': row.recommended}
            for row in SubscriptionPlan.objects.all()}


class SubscriptionRequired(APIException):
    status_code = 403
    default_code = 'subscription_required'

    def __init__(self, message='Subscription required. Existing records remain readable.', code='SUBSCRIPTION_REQUIRED'):
        super().__init__({'code': code, 'detail': message})


def entitlement(profile, plans=None):
    row, _ = AgencySubscription.objects.get_or_create(agency=profile)
    registered_at = AgencyProfile.objects.values_list('created_at', flat=True).get(pk=profile.pk)
    return evaluate(registered_at=registered_at, now=timezone.now(), plan=row.plan,
                    paid_until=row.paid_until, suspended=row.suspended,
                    plans=plan_catalog() if plans is None else plans)


def public_entitlement(profile):
    plans = plan_catalog()
    result = entitlement(profile, plans)
    result.pop('cutoff')
    result['usage'] = {'cars': profile.cars.exclude(status='archived').count(),
                       'branches': profile.branches.filter(is_active=True).count()}
    result['plans'] = {code: plan for code, plan in plans.items() if plan['isActive']}
    result['agencyId'] = str(profile.user_id)
    result['paymentMode'] = 'admin_activation'  # No unverified purchase/self-activation.
    return result


def require_management(profile):
    state = entitlement(profile)
    if not profile.user.is_active or not state['canManage']:
        raise SubscriptionRequired()
    return state


def require_capacity(profile, kind):
    # Caller must be inside transaction.atomic; serializes concurrent creation per agency.
    locked = AgencyProfile.objects.select_for_update().get(pk=profile.pk)
    state = require_management(locked)
    count = locked.cars.exclude(status='archived').count() if kind == 'cars' else locked.branches.filter(is_active=True).count()
    if count >= state['limits'][kind]:
        raise SubscriptionRequired(f'Your plan allows {state["limits"][kind]} {kind}.', 'PLAN_LIMIT_REACHED')


def require_booking_action(profile, booking, action):
    state = entitlement(profile)
    if state['canManage']:
        return
    if booking.agency_id != profile.pk or not may_finish_booking(
        created_at=booking.created_at, approved_at=booking.agency_responded_at,
        cutoff=state['cutoff'], action=action, suspended=state['state'] == 'suspended',
    ):
        raise SubscriptionRequired('Trial ended. Only completion of previously approved bookings is allowed.')
