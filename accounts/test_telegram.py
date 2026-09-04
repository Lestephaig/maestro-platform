import json
from datetime import timedelta
from urllib.parse import parse_qs, urlparse

from django.conf import settings
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from .models import TelegramConnection, TelegramLinkToken, User
from notifications.models import NotificationChannelPreference

TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware not in {
        'core.middleware.RequiredLegalAcceptanceMiddleware',
        'core.middleware.RequiredProfileCompletionMiddleware',
    }
]


@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    TELEGRAM_BOT_NAME='MaestroTestBot',
    TELEGRAM_LINK_API_TOKEN='test-platform-api-token',
)
class TelegramLinkApiTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='telegram-user',
            email='telegram@example.com',
            password='test-password',
        )
        self.client.force_login(self.user)

    def _create_token(self, client=None):
        response = (client or self.client).post(reverse('telegram_link_create'))
        self.assertEqual(response.status_code, 201)
        url = response.json()['url']
        return parse_qs(urlparse(url).query)['start'][0]

    def _complete(self, token, chat_id, api_token='test-platform-api-token'):
        return self.client.post(
            reverse('telegram_link_complete'),
            data=json.dumps({'token': token, 'telegram_chat_id': chat_id}),
            content_type='application/json',
            HTTP_AUTHORIZATION=f'Bearer {api_token}',
        )

    def test_successful_link_status_and_one_time_use(self):
        token = self._create_token()
        stored_token = TelegramLinkToken.objects.get()

        self.assertNotEqual(stored_token.token_hash, token)
        self.assertEqual(len(stored_token.token_hash), 64)
        self.assertLessEqual(
            stored_token.expires_at - stored_token.created_at,
            timedelta(minutes=15),
        )

        response = self._complete(token, 123456789)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json()['status'], 'linked')
        self.assertTrue(
            TelegramConnection.objects.filter(
                user=self.user,
                telegram_chat_id=123456789,
            ).exists()
        )
        preference = NotificationChannelPreference.objects.get(user=self.user)
        self.assertTrue(preference.telegram_enabled)
        status = self.client.get(reverse('telegram_link_status'))
        self.assertEqual(status.status_code, 200)
        self.assertTrue(status.json()['linked'])

        repeated = self._complete(token, 123456789)
        self.assertEqual(repeated.status_code, 409)
        self.assertEqual(repeated.json()['status'], 'used_token')

    def test_expired_and_unknown_tokens_are_rejected(self):
        token = self._create_token()
        TelegramLinkToken.objects.update(expires_at=timezone.now() - timedelta(seconds=1))

        expired = self._complete(token, 123)
        unknown = self._complete('unknown-token', 123)

        self.assertEqual(expired.status_code, 410)
        self.assertEqual(expired.json()['status'], 'expired_token')
        self.assertEqual(unknown.status_code, 404)
        self.assertEqual(unknown.json()['status'], 'invalid_token')
        self.assertFalse(TelegramConnection.objects.exists())

    def test_chat_id_conflict_consumes_token_without_replacing_owner(self):
        other_user = User.objects.create_user(
            username='other-user',
            email='other@example.com',
            password='test-password',
        )
        TelegramConnection.objects.create(user=other_user, telegram_chat_id=987654321)
        token = self._create_token()

        response = self._complete(token, 987654321)

        self.assertEqual(response.status_code, 409)
        self.assertEqual(response.json()['status'], 'chat_id_conflict')
        self.assertEqual(
            TelegramConnection.objects.get(telegram_chat_id=987654321).user,
            other_user,
        )
        self.assertIsNotNone(TelegramLinkToken.objects.get().used_at)

    def test_unlink_and_relink_do_not_create_duplicates(self):
        token = self._create_token()
        self.assertEqual(self._complete(token, 444).status_code, 200)

        unlinked = self.client.post(reverse('telegram_link_unlink'))
        self.assertEqual(unlinked.status_code, 200)
        self.assertTrue(unlinked.json()['unlinked'])
        self.assertFalse(TelegramConnection.objects.exists())
        preference = NotificationChannelPreference.objects.get(user=self.user)
        self.assertFalse(preference.telegram_enabled)

        new_token = self._create_token()
        self.assertEqual(self._complete(new_token, 444).status_code, 200)
        self.assertEqual(TelegramConnection.objects.filter(user=self.user).count(), 1)

    def test_relink_updates_existing_connection(self):
        first_token = self._create_token()
        self.assertEqual(self._complete(first_token, 444).status_code, 200)

        second_token = self._create_token()
        self.assertEqual(self._complete(second_token, 555).status_code, 200)

        connection = TelegramConnection.objects.get(user=self.user)
        self.assertEqual(connection.telegram_chat_id, 555)
        self.assertEqual(TelegramConnection.objects.filter(user=self.user).count(), 1)

    def test_create_token_is_rate_limited(self):
        for _ in range(5):
            self.assertEqual(
                self.client.post(reverse('telegram_link_create')).status_code,
                201,
            )

        response = self.client.post(reverse('telegram_link_create'))

        self.assertEqual(response.status_code, 429)
        self.assertEqual(response.json()['error'], 'rate_limited')
        self.assertIn('Retry-After', response)

    def test_internal_endpoint_requires_valid_service_token(self):
        token = self._create_token()

        missing = self.client.post(
            reverse('telegram_link_complete'),
            data=json.dumps({'token': token, 'telegram_chat_id': 123}),
            content_type='application/json',
        )
        invalid = self._complete(token, 123, api_token='wrong-token')

        self.assertEqual(missing.status_code, 401)
        self.assertEqual(invalid.status_code, 401)
        self.assertIsNone(TelegramLinkToken.objects.get().used_at)

    def test_user_endpoints_require_login_and_unlink_only_current_user(self):
        TelegramConnection.objects.create(user=self.user, telegram_chat_id=111)
        other_user = User.objects.create_user(
            username='unlink-other',
            email='unlink-other@example.com',
            password='test-password',
        )
        TelegramConnection.objects.create(user=other_user, telegram_chat_id=222)
        self.client.logout()

        for url_name in ('telegram_link_status', 'telegram_link_create', 'telegram_link_unlink'):
            response = self.client.get(reverse(url_name)) if url_name.endswith('status') else self.client.post(reverse(url_name))
            self.assertEqual(response.status_code, 302)

        self.client.force_login(self.user)
        self.client.post(reverse('telegram_link_unlink'))
        self.assertFalse(TelegramConnection.objects.filter(user=self.user).exists())
        self.assertTrue(TelegramConnection.objects.filter(user=other_user).exists())

    def test_create_and_unlink_require_csrf(self):
        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)

        self.assertEqual(csrf_client.post(reverse('telegram_link_create')).status_code, 403)
        self.assertEqual(csrf_client.post(reverse('telegram_link_unlink')).status_code, 403)
        self.assertEqual(csrf_client.post(reverse('telegram_link_banner_dismiss')).status_code, 403)


@override_settings(
    MIDDLEWARE=TEST_MIDDLEWARE,
    TELEGRAM_BOT_NAME='MaestroTestBot',
)
class TelegramLinkBannerTemplateTests(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username='banner-user',
            email='banner@example.com',
            password='test-password',
        )

    def test_banner_is_only_rendered_for_authenticated_unlinked_user(self):
        anonymous = self.client.get(reverse('home'))
        self.assertNotContains(anonymous, 'id="telegramLinkBanner"')

        self.client.force_login(self.user)
        unlinked = self.client.get(reverse('home'))
        self.assertContains(unlinked, 'id="telegramLinkBanner"')
        self.assertContains(unlinked, 'оперативные уведомления о сообщениях и новых публикациях')
        self.assertContains(unlinked, reverse('telegram_link_create'))

        TelegramConnection.objects.create(user=self.user, telegram_chat_id=12345)
        linked = self.client.get(reverse('home'))
        self.assertNotContains(linked, 'id="telegramLinkBanner"')

    def test_banner_is_not_rendered_on_profile_linking_screen(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('profile'))

        self.assertNotContains(response, 'id="telegramLinkBanner"')
        self.assertContains(response, 'id="telegram-settings"')

    def test_dismissal_is_stored_for_current_authenticated_session(self):
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('home')), 'id="telegramLinkBanner"')

        response = self.client.post(reverse('telegram_link_banner_dismiss'))

        self.assertEqual(response.status_code, 200)
        self.assertTrue(response.json()['dismissed'])
        self.assertNotContains(self.client.get(reverse('home')), 'id="telegramLinkBanner"')

        self.client.logout()
        self.client.force_login(self.user)
        self.assertContains(self.client.get(reverse('home')), 'id="telegramLinkBanner"')

    @override_settings(TELEGRAM_BOT_NAME='')
    def test_banner_is_not_rendered_when_linking_is_unavailable(self):
        self.client.force_login(self.user)

        response = self.client.get(reverse('home'))

        self.assertNotContains(response, 'id="telegramLinkBanner"')
