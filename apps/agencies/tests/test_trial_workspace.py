from datetime import timedelta
from django.utils import timezone
from django.core.management import call_command
from rest_framework.test import APITestCase
from apps.accounts.services import register_agency
from apps.agencies.models import AgencyProfile, AgencySubscription, AgencySubscriptionRequest

class TrialWorkspaceTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_tunisia_governorates', verbosity=0)
        cls.user = register_agency(agency_name='Immediate trial',responsible_person_name='Manager',email='newtrial@example.com',phone='+21692009111',password='StrongPassword123!',governorate_code='TN-11',city='Tunis')

    def setUp(self):
        self.client.force_authenticate(self.user)

    def test_new_unverified_agency_can_manage_but_is_not_public(self):
        s=self.client.get('/api/v1/agencies/subscription/').data
        self.assertEqual(s['state'],'trial');self.assertTrue(s['canManage'])
        self.assertEqual(self.client.get('/api/v1/fleet/cars/').status_code,200)
        payload={'brand':'Toyota','model':'Yaris','year':2024,'category':'economy','transmission':'manual','fuelType':'petrol','seats':5,'doors':5,'dailyPrice':'100.000','governorateCode':'TN-11','city':'Tunis'}
        car=self.client.post('/api/v1/fleet/cars/',payload,format='multipart')
        self.assertEqual(car.status_code,201,car.data)
        self.assertEqual(self.client.get('/api/v1/cars/').data, [])
        self.assertEqual(self.client.get(f'/api/v1/agencies/{self.user.id}/public/').status_code,404)
        b=self.client.post('/api/v1/agencies/branches/',{'name':'Main','address':'Street','governorateCode':'TN-11','city':'Tunis'},format='json')
        self.assertEqual(b.status_code,201,b.data)
        r=self.client.patch(f"/api/v1/agencies/branches/{b.data['id']}/cars/{car.data['id']}/",{},format='json')
        self.assertEqual(r.status_code,200)
        self.assertEqual(self.client.get('/api/v1/bookings/agency/').status_code,200)
        self.assertEqual(self.client.get('/api/v1/payments/agency/').status_code,200)

    def test_expired_trial_is_read_only_and_request_does_not_unlock(self):
        AgencyProfile.objects.filter(user=self.user).update(created_at=timezone.now()-timedelta(days=14))
        self.assertEqual(self.client.get('/api/v1/fleet/cars/').status_code,200)
        self.assertEqual(self.client.post('/api/v1/fleet/cars/',{},format='json').status_code,403)
        r=self.client.post('/api/v1/agencies/subscription/request/',{'plan':'medium','paidUntil':'2099-01-01','canManage':True},format='json')
        self.assertEqual(r.status_code,201)
        self.assertFalse(self.client.get('/api/v1/agencies/subscription/').data['canManage'])
        again=self.client.post('/api/v1/agencies/subscription/request/',{'plan':'small'},format='json')
        self.assertEqual(again.status_code,200)
        self.assertEqual(AgencySubscriptionRequest.objects.filter(agency__user=self.user).count(),1)
        self.assertEqual(self.client.post('/api/v1/agencies/subscription/request/',{'plan':{}},format='json').status_code,400)

    def test_suspension_and_nonagency_cannot_bypass_access(self):
        AgencySubscription.objects.create(agency=self.user.agency_profile,suspended=True)
        self.assertEqual(self.client.post('/api/v1/agencies/branches/',{},format='json').status_code,403)
        self.client.force_authenticate(None)
        self.assertEqual(self.client.post('/api/v1/agencies/subscription/request/',{'plan':'small'},format='json').status_code,401)
