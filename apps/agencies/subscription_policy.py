"""Pure policy, using authoritative timezone-aware server timestamps."""
from datetime import timedelta
from math import ceil

PLANS = {
    'small': {'name': 'Small', 'monthlyTnd': 49, 'cars': 10, 'branches': 1},
    'medium': {'name': 'Medium', 'monthlyTnd': 99, 'cars': 30, 'branches': 3},
    'enterprise': {'name': 'Enterprise', 'monthlyTnd': 199, 'cars': 100, 'branches': 10},
}


def evaluate(*, registered_at, now, plan='medium', paid_until=None, suspended=False, plans=None):
    plans = PLANS if plans is None else plans
    trial_end = registered_at + timedelta(days=14)
    paid = paid_until is not None and now < paid_until
    trial = now < trial_end
    enabled = not suspended and (paid or trial)
    effective_plan = plan if paid else 'medium'
    cutoff = max(trial_end, paid_until) if paid_until else trial_end
    return {
        'state': 'suspended' if suspended else 'active' if paid else 'trial' if trial else 'expired',
        'canManage': enabled, 'plan': effective_plan,
        'trialStartedAt': registered_at.isoformat(), 'trialEndsAt': trial_end.isoformat(),
        'paidUntil': paid_until.isoformat() if paid_until else None,
        'serverTime': now.isoformat(), 'daysRemaining': max(0, ceil((cutoff-now).total_seconds()/86400)),
        'limits': plans[effective_plan], 'cutoff': cutoff,
    }


def may_finish_booking(*, created_at, approved_at, cutoff, action, suspended=False):
    if suspended or created_at >= cutoff:
        return False
    if action == 'reject':
        return True  # Close an old pending request, never accept a new one.
    return action in {'pickup', 'return', 'mark-paid'} and approved_at is not None and approved_at < cutoff
