import importlib

from django.apps import apps
from django.test import TestCase
from django.urls import reverse

from .models import CookieConsent, LegalAcceptance, User
from .profile_completion import get_profile_completion
from core.legal import get_required_documents
from performers.models import PerformerProfile


class LegalDocumentsTests(TestCase):
    def test_legal_document_page_is_public(self):
        response = self.client.get('/legal/privacy-policy/')

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Политика обработки персональных данных')
        self.assertContains(response, 'Версия: v1-2026')

    def test_login_fields_use_site_styling(self):
        response = self.client.get(reverse('login'))

        self.assertContains(response, '.login-body input[type="text"]')
        self.assertContains(response, 'background: rgba(255, 255, 255, 0.07)')
        self.assertContains(response, 'input:-webkit-autofill')


class RegistrationLegalAcceptanceTests(TestCase):
    def _registration_data(self, **overrides):
        data = {
            'email': 'new@example.com',
            'first_name': 'Анна',
            'last_name': 'Иванова',
            'country': 'Россия',
            'city': 'Москва',
            'bio': 'Профессиональная исполнительница.',
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

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Анна')
        self.assertEqual(user.last_name, 'Иванова')
        self.assertEqual(user.performer_profile.country, 'Россия')
        self.assertEqual(user.performer_profile.city, 'Москва')
        self.assertEqual(user.performer_profile.bio, 'Профессиональная исполнительница.')

    def test_registration_requires_fields_for_selected_role(self):
        response = self.client.post(
            reverse('register'),
            self._registration_data(last_name='', country='', bio=''),
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Укажите фамилию.')
        self.assertContains(response, 'Укажите страну.')
        self.assertContains(response, 'Заполните информацию о себе.')
        self.assertFalse(User.objects.filter(email='new@example.com').exists())

    def test_client_registration_creates_complete_venue_profile(self):
        response = self.client.post(reverse('register'), self._registration_data(
            role='client',
            first_name='',
            last_name='',
            bio='',
            company_name='Большой зал',
            address='Театральная площадь, 1',
            contact_person='Мария Петрова',
            accept_terms='on',
            accept_personal_data='on',
        ))

        self.assertEqual(response.status_code, 302)
        user = User.objects.get(email='new@example.com')
        self.assertEqual(user.display_name, 'Большой зал')
        self.assertEqual(user.client_profile.contact_person, 'Мария Петрова')

    def test_account_type_is_rendered_before_registration_fields(self):
        response = self.client.get(reverse('register'))

        content = response.content.decode()
        self.assertLess(content.index('Тип аккаунта'), content.index('Введите имя'))
        self.assertContains(response, 'class="role-card"')
        self.assertContains(response, 'Пароль')
        self.assertContains(response, 'Подтверждение пароля')
        self.assertContains(response, 'registrationForm.addEventListener')
        self.assertContains(response, 'Регистрация…')
        self.assertContains(response, 'Создаём аккаунт и отправляем письмо подтверждения')


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


class RequiredProfileCompletionGateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='performer@example.com',
            email='performer@example.com',
            password='StrongPassword123!',
            role='performer',
        )
        self.profile = PerformerProfile.objects.create(
            user=self.user,
            full_name='Старый артист',
            performer_type=PerformerProfile.PERFORMER_TYPE_CONDUCTOR,
        )
        LegalAcceptance.objects.bulk_create([
            LegalAcceptance(
                user=self.user,
                document_slug=slug,
                document_title=document['title'],
                document_version=document['version'],
            )
            for slug, document in get_required_documents().items()
        ])
        self.client.force_login(self.user)

    def test_incomplete_user_is_redirected_and_sees_blocking_banner(self):
        response = self.client.get(reverse('home'))
        self.assertRedirects(response, reverse('profile'), fetch_redirect_response=False)

        profile_response = self.client.get(reverse('profile'))
        self.assertContains(profile_response, 'До заполнения профиля остальные разделы сайта недоступны')
        self.assertContains(profile_response, 'Имя, Фамилия, Биография, Страна, Город')
        self.assertContains(profile_response, 'class="profile-completion-backdrop"')
        self.assertContains(profile_response, 'aria-modal="true"')
        self.assertContains(profile_response, 'backdrop-filter: blur(12px)')
        self.assertContains(profile_response, 'hx-get="/accounts/profile/edit/"')

        edit_response = self.client.get(reverse('profile_edit'))
        self.assertContains(edit_response, 'Сохранить изменения')
        self.assertNotContains(edit_response, 'hx-get="/accounts/profile/view/"')

    def test_invalid_profile_edit_includes_first_error_navigation(self):
        response = self.client.post(reverse('profile_edit'), {
            'first_name': '',
            'last_name': '',
            'performer_type': PerformerProfile.PERFORMER_TYPE_CONDUCTOR,
            'bio': '',
            'country': '',
            'city': '',
            'photo_position': 'center',
        })

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'scrollToFirstProfileError')
        self.assertContains(response, "scrollIntoView({ behavior: 'smooth', block: 'center' })")
        self.assertContains(response, "field?.focus({ preventScroll: true })")

    def test_profile_completion_percentage_counts_role_fields(self):
        self.user.first_name = 'Анна'
        self.user.last_name = 'Иванова'
        self.user.save(update_fields=['first_name', 'last_name'])
        self.profile.performer_type = PerformerProfile.PERFORMER_TYPE_VOCALIST
        self.profile.voice_type = 'Сопрано'
        self.profile.birth_date = '1990-01-01'
        self.profile.education = 'Консерватория'
        self.profile.achievements = 'Лауреат конкурса'
        self.profile.bio = 'Биография'
        self.profile.country = 'Россия'
        self.profile.city = 'Москва'
        self.profile.photo = 'performers/photos/photo.jpg'
        self.profile.video_url = 'https://example.com/video'
        self.profile.save()

        completion = get_profile_completion(self.user)
        self.assertEqual(completion, {
            'completed': 13,
            'total': 13,
            'percentage': 100,
            'level': 'complete',
        })

        self.profile.education = ''
        self.profile.save(update_fields=['education'])
        completion = get_profile_completion(self.user)
        self.assertEqual(completion['percentage'], 92)
        self.assertEqual(completion['level'], 'high')

        response = self.client.get(reverse('profile'))
        self.assertContains(response, 'Ваш профиль заполнен на 92%')

    def test_completing_required_fields_unlocks_site(self):
        response = self.client.post(reverse('profile_edit'), {
            'first_name': 'Анна',
            'last_name': 'Иванова',
            'performer_type': PerformerProfile.PERFORMER_TYPE_CONDUCTOR,
            'bio': 'Концертирующая исполнительница.',
            'country': 'Россия',
            'city': 'Москва',
            'photo_position': 'center',
        })

        self.assertEqual(response.status_code, 200)
        self.assertEqual(self.client.get(reverse('home')).status_code, 200)
        self.user.refresh_from_db()
        self.profile.refresh_from_db()
        self.assertEqual(self.user.first_name, 'Анна')
        self.assertEqual(self.profile.full_name, 'Анна Иванова')


class ExistingUserNameMigrationTests(TestCase):
    def test_current_full_name_is_copied_entirely_to_first_name(self):
        user = User.objects.create_user(
            username='legacy@example.com',
            email='legacy@example.com',
            role='performer',
            first_name='Анна',
            last_name='Иванова',
        )
        PerformerProfile.objects.create(user=user, full_name='Иванова Анна Сергеевна')

        migration = importlib.import_module(
            'accounts.migrations.0008_copy_existing_full_name_to_first_name'
        )
        migration.copy_existing_full_names(apps, None)

        user.refresh_from_db()
        self.assertEqual(user.first_name, 'Иванова Анна Сергеевна')
        self.assertEqual(user.last_name, '')


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
