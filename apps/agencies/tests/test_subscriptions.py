from datetime import timedelta
from types import SimpleNamespace
from django.core.management import call_command
from django.utils import timezone
from rest_framework.test import APITestCase
from apps.accounts.services import register_agency
from apps.agencies.models import AgencyProfile, AgencySubscription
from apps.agencies.subscription_policy import evaluate, may_finish_booking
from apps.agencies.subscriptions import require_booking_action, SubscriptionRequired

class SubscriptionTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_tunisia_governorates', verbosity=0)
        cls.user = register_agency(agency_name='Trial Agency', responsible_person_name='Manager', email='trial@example.com', phone='+21692000911', password='StrongPassword123!', governorate_code='TN-11', city='Tunis')
        cls.user.account_status = 'active'
        cls.user.save()
        cls.profile = cls.user.agency_profile
        cls.profile.verification_status = 'approved'
        cls.profile.save()

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_boundary_and_paid_activation(self):
        now = timezone.now()
        self.assertTrue(evaluate(registered_at=now-timedelta(days=14)+timedelta(seconds=1), now=now)['canManage'])
        self.assertFalse(evaluate(registered_at=now-timedelta(days=14), now=now)['canManage'])
        self.assertEqual(evaluate(registered_at=now-timedelta(days=30), now=now, plan='small', paid_until=now+timedelta(days=1))['limits']['cars'], 10)
        self.assertFalse(evaluate(registered_at=now, now=now, suspended=True)['canManage'])

    def test_expiry_preserves_reads_but_blocks_management(self):
        AgencyProfile.objects.filter(pk=self.profile.pk).update(created_at=timezone.now()-timedelta(days=15))
        self.assertEqual(self.client.get('/api/v1/agencies/subscription/').data['state'], 'expired')
        self.assertEqual(self.client.get('/api/v1/agencies/branches/').status_code, 200)
        r = self.client.post('/api/v1/agencies/branches/', {'name':'Main','address':'Street','governorateCode':'TN-11','city':'Tunis'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(str(r.data['code']), 'SUBSCRIPTION_REQUIRED')
        AgencySubscription.objects.filter(agency=self.profile).update(paid_until=timezone.now()+timedelta(days=30), plan='small')
        self.assertTrue(self.client.get('/api/v1/agencies/subscription/').data['canManage'])

    def test_branch_limits_validation_and_ownership(self):
        for i in range(3):
            r = self.client.post('/api/v1/agencies/branches/', {'name':f'Branch {i}','address':'Street','governorateCode':'TN-11','city':'Tunis','latitude':'36.8000000','longitude':'10.1800000'}, format='json')
            self.assertEqual(r.status_code, 201, r.data)
        r = self.client.post('/api/v1/agencies/branches/', {'name':'Fourth','address':'Street','governorateCode':'TN-11','city':'Tunis'}, format='json')
        self.assertEqual(r.status_code, 403)
        self.assertEqual(str(r.data['code']), 'PLAN_LIMIT_REACHED')
        branches = self.client.get('/api/v1/agencies/branches/').data
        from apps.agencies.models import AgencyBranch
        inactive=AgencyBranch.objects.create(agency=self.profile,name='Inactive',governorate=self.profile.governorate,is_active=False)
        r=self.client.patch(f'/api/v1/agencies/branches/{inactive.id}/', {'isActive':'true'},format='json')
        self.assertEqual(r.status_code,403)
        invalid = self.client.patch(f"/api/v1/agencies/branches/{branches[0]['id']}/", {'latitude':'91'}, format='json')
        self.assertEqual(invalid.status_code, 400)
        other = register_agency(agency_name='Other',responsible_person_name='Other',email='other@example.com',phone='+21692000912',password='StrongPassword123!',governorate_code='TN-11',city='Tunis')
        other.account_status='active'; other.save()
        p=other.agency_profile; p.verification_status='approved';p.save()
        self.client.force_authenticate(other)
        r=self.client.patch(f"/api/v1/agencies/branches/{branches[0]['id']}/", {'name':'Stolen'},format='json')
        self.assertEqual(r.status_code,404)

    def test_completion_only_previously_approved_bookings(self):
        now=timezone.now(); cutoff=now-timedelta(days=1)
        AgencyProfile.objects.filter(pk=self.profile.pk).update(created_at=cutoff-timedelta(days=14))
        profile=AgencyProfile.objects.get(pk=self.profile.pk)
        booking=SimpleNamespace(agency_id=profile.pk,created_at=cutoff-timedelta(days=2),agency_responded_at=cutoff-timedelta(days=1))
        for action in ['pickup','return','mark-paid']:
            require_booking_action(profile,booking,action)
        with self.assertRaises(SubscriptionRequired): require_booking_action(profile,booking,'approve')
        booking.agency_responded_at=None
        with self.assertRaises(SubscriptionRequired): require_booking_action(profile,booking,'pickup')
        self.assertTrue(may_finish_booking(created_at=booking.created_at,approved_at=None,cutoff=cutoff,action='reject'))
        self.assertFalse(may_finish_booking(created_at=cutoff,approved_at=cutoff,cutoff=cutoff,action='return'))
