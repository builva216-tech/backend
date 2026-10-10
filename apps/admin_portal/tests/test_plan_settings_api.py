from django.core.management import call_command
from rest_framework.test import APITestCase
from apps.accounts.models import User
from apps.accounts.services import register_agency
from apps.agencies.models import SubscriptionPlan


class PlanSettingsTests(APITestCase):
    @classmethod
    def setUpTestData(cls):
        call_command('seed_tunisia_governorates', verbosity=0)
        cls.admin = User.objects.create_superuser(email='plans-admin@example.com', password='StrongPassword123!', full_name='Admin', phone='+21690000888')
        cls.agency = register_agency(agency_name='Plan Agency', responsible_person_name='Manager', email='plan-agency@example.com', phone='+21690000889', password='StrongPassword123!', governorate_code='TN-11', city='Tunis')

    def setUp(self):
        self.client.force_authenticate(self.admin)

    def test_seeded_plans_and_admin_changes_reach_agency_and_limits(self):
        self.assertEqual(len(self.client.get('/api/v1/admin/plans/').data), 3)
        response = self.client.patch('/api/v1/admin/plans/medium/', {'revision': 0, 'name': 'Growth', 'monthlyTnd': '120.50', 'priceText': '120.50 TND monthly', 'description': 'Your growing fleet', 'cars': 42, 'branches': 4}, format='json')
        self.assertEqual(response.status_code, 200, response.data)
        self.client.force_authenticate(self.agency)
        subscription = self.client.get('/api/v1/agencies/subscription/').data
        self.assertEqual(subscription['plans']['medium']['name'], 'Growth')
        self.assertEqual(subscription['plans']['medium']['monthlyTnd'], 120.5)
        self.assertEqual(subscription['plans']['medium']['priceText'], '120.50 TND monthly')
        self.assertEqual(subscription['limits']['cars'], 42)

    def test_stale_edit_does_not_overwrite_other_admin(self):
        endpoint = '/api/v1/admin/plans/small/'
        self.assertEqual(self.client.patch(endpoint, {'revision': 0, 'name': 'Changed'}, format='json').status_code, 200)
        self.assertEqual(self.client.patch(endpoint, {'revision': 0, 'name': 'Stale'}, format='json').status_code, 409)
        self.assertEqual(SubscriptionPlan.objects.get(code='small').name, 'Changed')

    def test_invalid_limits_and_prices_are_rejected(self):
        for values in ({'cars': 0}, {'branches': -1}, {'monthlyTnd': '-1.00'}, {'monthlyTnd': '12.345'}, {'name': ''}):
            response = self.client.patch('/api/v1/admin/plans/small/', dict(values, revision=0), format='json')
            self.assertEqual(response.status_code, 400, response.data)
        self.assertEqual(self.client.patch('/api/v1/admin/plans/small/', {'name': 'Missing revision'}, format='json').status_code, 400)

    def test_agencies_cannot_edit_prices_and_hidden_plans_cannot_be_requested(self):
        self.client.patch('/api/v1/admin/plans/small/', {'revision': 0, 'isActive': False}, format='json')
        self.client.force_authenticate(self.agency)
        self.assertEqual(self.client.patch('/api/v1/admin/plans/medium/', {'revision': 0, 'monthlyTnd': 1}, format='json').status_code, 403)
        self.assertNotIn('small', self.client.get('/api/v1/agencies/subscription/').data['plans'])
        self.assertEqual(self.client.post('/api/v1/agencies/subscription/request/', {'plan': 'small'}, format='json').status_code, 400)
