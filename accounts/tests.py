from django.test import TestCase
from django.urls import reverse

from .models import CookieConsent, LegalAcceptance, User


class LegalDocumentsTests(TestCase):
    def test_legal_document_page_is_public(self):
        response = self.client.get('/legal/privacy-policy/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Политика обработки персональных данных')
        self.assertContains(response, 'Версия: v1-2026')


class RegistrationLegalAcceptanceTests(TestCase):
    def _registration_data(self, **overrides):
        data = {
            'email': 'new@example.com',
            'display_name': 'Новый пользователь',
            'password1': 'StrongPassword123!',
            'password2': 'StrongPassword123!',
            'role': 'performer',
        }
        data.update(overrides)
        return data

    def test_registration_requires_both_legal_checkboxes(self):
        response = self.client.post(reverse('register'), self._registration_data())

        self.assertEqual(response.status_code, 200)
        self.assertFalse(User.objects.filter(email='new@example.com').exists())
        self.assertContains(response, 'Необходимо принять пользовательское соглашение')
        self.assertContains(response, 'Необходимо дать согласие на обработку персональных данных')

    def test_registration_records_each_required_acceptance(self):
        response = self.client.post(
            reverse('register'),
            self._registration_data(accept_terms='on', accept_personal_data='on'),
        )

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='new@example.com')
        self.assertEqual(LegalAcceptance.objects.filter(user=user).count(), 4)
        self.assertTrue(
            LegalAcceptance.objects.filter(
                user=user,
                document_slug='terms-of-use',
                document_version='v1-2026',
            ).exists()
        )


class RequiredLegalAcceptanceGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='old@example.com',
            email='old@example.com',
            password='StrongPassword123!',
            display_name='Старый пользователь',
        )

    def test_authenticated_user_without_acceptances_is_redirected_to_gate(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('profile'))

        self.assertEqual(response.status_code, 302)
        self.assertTrue(response['Location'].startswith('/legal/acceptance-required/'))

    def test_gate_records_acceptances_and_allows_profile(self):
        self.client.force_login(self.user)

        response = self.client.post(
            reverse('accept_required_legal'),
            {'accept_terms': 'on', 'accept_personal_data': 'on'},
        )

        self.assertEqual(response.status_code, 302)
        self.assertEqual(LegalAcceptance.objects.filter(user=self.user).count(), 4)
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)


class CookieConsentTests(TestCase):
    def test_authenticated_cookie_acceptance_is_stored(self):
        user = User.objects.create_user(
            username='cookie@example.com',
            email='cookie@example.com',
            password='StrongPassword123!',
        )
        self.client.force_login(user)

        response = self.client.post(reverse('accept_cookie_policy'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(CookieConsent.objects.filter(user=user, policy_version='v1-2026').exists())
