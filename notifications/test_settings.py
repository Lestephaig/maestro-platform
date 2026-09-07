import json
import re

from django.conf import settings
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from django.test import Client, TestCase, TransactionTestCase, override_settings
from django.urls import reverse

from accounts.models import TelegramConnection

from .channels import get_active_channels
from .models import NotificationChannelPreference


TEST_MIDDLEWARE = [
    middleware
    for middleware in settings.MIDDLEWARE
    if middleware not in {
        'core.middleware.RequiredLegalAcceptanceMiddleware',
        'core.middleware.RequiredProfileCompletionMiddleware',
    }
]


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class NotificationChannelServiceTests(TestCase):
    def setUp(self):
        user_model = NotificationChannelPreference._meta.get_field(
            'user'
        ).remote_field.model
        self.user = user_model.objects.create_user(
            username='channel-user',
            email='channel@example.com',
            is_email_verified=True,
        )

    def test_missing_preference_keeps_email_enabled_for_existing_user(self):
        self.assertFalse(
            NotificationChannelPreference.objects.filter(user=self.user).exists()
        )

        self.assertEqual(get_active_channels(self.user, 'chat_message'), {'email'})

        preference = NotificationChannelPreference.objects.get(user=self.user)
        self.assertTrue(preference.email_enabled)
        self.assertFalse(preference.telegram_enabled)

    def test_active_channels_are_global_for_every_switch_combination(self):
        TelegramConnection.objects.create(
            user=self.user,
            telegram_chat_id=123456,
        )
        preference = NotificationChannelPreference.get_or_create_for(self.user)
        cases = (
            (False, False, set()),
            (True, False, {'email'}),
            (False, True, {'telegram'}),
            (True, True, {'email', 'telegram'}),
        )

        for email_enabled, telegram_enabled, expected in cases:
            with self.subTest(
                email_enabled=email_enabled,
                telegram_enabled=telegram_enabled,
            ):
                preference.email_enabled = email_enabled
                preference.telegram_enabled = telegram_enabled
                preference.save()
                self.assertEqual(
                    get_active_channels(self.user, 'chat_message'),
                    expected,
                )
                self.assertEqual(
                    get_active_channels(self.user, 'announcement_tag_match'),
                    expected,
                )

    def test_telegram_is_not_active_without_connection(self):
        preference = NotificationChannelPreference.get_or_create_for(self.user)
        preference.email_enabled = False
        preference.telegram_enabled = True
        preference.save()

        self.assertEqual(get_active_channels(self.user, 'chat_message'), set())


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class NotificationSettingsApiTests(TestCase):
    def setUp(self):
        user_model = NotificationChannelPreference._meta.get_field(
            'user'
        ).remote_field.model
        self.user = user_model.objects.create_user(
            username='settings-user',
            email='settings@example.com',
            password='test-password',
            is_email_verified=True,
        )
        self.client.force_login(self.user)
        self.url = reverse('notifications:settings_api')

    def _update(self, payload):
        return self.client.patch(
            self.url,
            data=json.dumps(payload),
            content_type='application/json',
        )

    def test_get_returns_two_global_switches(self):
        response = self.client.get(self.url)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(response.json(), {
            'email_enabled': True,
            'telegram_enabled': False,
            'telegram_linked': False,
        })

    def test_api_persists_every_switch_combination_independently(self):
        connection_object = TelegramConnection.objects.create(
            user=self.user,
            telegram_chat_id=987654,
        )
        original_email = self.user.email
        cases = (
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        )

        for email_enabled, telegram_enabled in cases:
            with self.subTest(
                email_enabled=email_enabled,
                telegram_enabled=telegram_enabled,
            ):
                response = self._update({
                    'email_enabled': email_enabled,
                    'telegram_enabled': telegram_enabled,
                })
                self.assertEqual(response.status_code, 200)
                preference = NotificationChannelPreference.objects.get(
                    user=self.user,
                )
                self.assertEqual(preference.email_enabled, email_enabled)
                self.assertEqual(preference.telegram_enabled, telegram_enabled)
                self.assertEqual(
                    self.client.get(self.url).json()['email_enabled'],
                    email_enabled,
                )
                self.assertEqual(
                    self.client.get(self.url).json()['telegram_enabled'],
                    telegram_enabled,
                )

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, original_email)
        self.assertTrue(
            TelegramConnection.objects.filter(pk=connection_object.pk).exists()
        )

    def test_api_rejects_telegram_without_link_atomically(self):
        response = self._update({
            'email_enabled': False,
            'telegram_enabled': True,
        })

        self.assertEqual(response.status_code, 400)
        self.assertEqual(response.json()['error'], 'validation_error')
        self.assertIn('telegram_enabled', response.json()['fields'])
        self.assertFalse(
            NotificationChannelPreference.objects.filter(user=self.user).exists()
        )

    def test_api_validates_json_boolean_values_and_unknown_fields(self):
        malformed = self.client.patch(
            self.url,
            data='{',
            content_type='application/json',
        )
        invalid = self._update({
            'email_enabled': 'yes',
            'unexpected': False,
        })

        self.assertEqual(malformed.status_code, 400)
        self.assertEqual(malformed.json()['error'], 'invalid_json')
        self.assertEqual(invalid.status_code, 400)
        self.assertEqual(invalid.json()['error'], 'validation_error')

    def test_api_requires_authentication_and_csrf(self):
        self.client.logout()
        self.assertEqual(self.client.get(self.url).status_code, 302)
        self.assertEqual(
            self._update({'email_enabled': False}).status_code,
            302,
        )

        csrf_client = Client(enforce_csrf_checks=True)
        csrf_client.force_login(self.user)
        response = csrf_client.patch(
            self.url,
            data=json.dumps({'email_enabled': False}),
            content_type='application/json',
        )
        self.assertEqual(response.status_code, 403)


@override_settings(MIDDLEWARE=TEST_MIDDLEWARE)
class NotificationSettingsUiTests(TestCase):
    def setUp(self):
        user_model = NotificationChannelPreference._meta.get_field(
            'user'
        ).remote_field.model
        self.user = user_model.objects.create_user(
            username='ui-user',
            email='ui@example.com',
        )
        self.client.force_login(self.user)
        self.list_url = reverse('notifications:list')
        self.update_url = reverse('notifications:channel_settings_update')

    def test_two_switches_are_shown_once_on_notification_page(self):
        response = self.client.get(self.list_url)

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'Получать уведомления по email', count=1)
        self.assertContains(response, 'Получать уведомления в Telegram', count=1)
        telegram_input = re.search(
            r'name="telegram_enabled"[^>]*',
            response.content.decode(),
            re.DOTALL,
        )
        self.assertIsNotNone(telegram_input)
        self.assertIn('disabled', telegram_input.group())
        self.assertContains(response, reverse('profile') + '#telegram-settings')

    def test_old_settings_page_redirects_to_notifications(self):
        response = self.client.get(reverse('notifications:settings'))

        self.assertRedirects(response, self.list_url)

    def test_form_persists_every_switch_combination_without_changing_accounts(self):
        connection_object = TelegramConnection.objects.create(
            user=self.user,
            telegram_chat_id=24680,
        )
        original_email = self.user.email
        cases = (
            (False, False),
            (True, False),
            (False, True),
            (True, True),
        )

        for email_enabled, telegram_enabled in cases:
            with self.subTest(
                email_enabled=email_enabled,
                telegram_enabled=telegram_enabled,
            ):
                data = {}
                if email_enabled:
                    data['email_enabled'] = 'on'
                if telegram_enabled:
                    data['telegram_enabled'] = 'on'

                response = self.client.post(self.update_url, data, follow=True)

                self.assertEqual(response.status_code, 200)
                preference = NotificationChannelPreference.objects.get(
                    user=self.user,
                )
                self.assertEqual(preference.email_enabled, email_enabled)
                self.assertEqual(preference.telegram_enabled, telegram_enabled)

        self.user.refresh_from_db()
        self.assertEqual(self.user.email, original_email)
        self.assertTrue(
            TelegramConnection.objects.filter(pk=connection_object.pk).exists()
        )


class NotificationChannelPreferenceMigrationTests(TransactionTestCase):
    migrate_from = [('notifications', '0007_enable_chat_telegram_for_linked_users')]
    migrate_to = [('notifications', '0008_notificationchannelpreference')]

    def setUp(self):
        super().setUp()
        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_from)
        old_apps = executor.loader.project_state(self.migrate_from).apps
        User = old_apps.get_model('accounts', 'User')
        TelegramConnection = old_apps.get_model('accounts', 'TelegramConnection')
        NotificationPreference = old_apps.get_model(
            'notifications',
            'NotificationPreference',
        )

        self.linked_user_id = User.objects.create(
            username='migration-linked',
            email='migration-linked@example.com',
        ).pk
        self.default_user_id = User.objects.create(
            username='migration-default',
            email='migration-default@example.com',
        ).pk
        TelegramConnection.objects.create(
            user_id=self.linked_user_id,
            telegram_chat_id=112233,
        )
        NotificationPreference.objects.create(
            user_id=self.linked_user_id,
            notification_type='chat_message',
            email_enabled=False,
            telegram_enabled=True,
        )
        NotificationPreference.objects.create(
            user_id=self.linked_user_id,
            notification_type='project_invitation',
            email_enabled=True,
            telegram_enabled=False,
        )

        executor = MigrationExecutor(connection)
        executor.migrate(self.migrate_to)
        self.apps = executor.loader.project_state(self.migrate_to).apps

    def tearDown(self):
        MigrationExecutor(connection).migrate(
            MigrationExecutor(connection).loader.graph.leaf_nodes()
        )
        super().tearDown()

    def test_migration_preserves_enabled_channels_and_safe_defaults(self):
        Preference = self.apps.get_model(
            'notifications',
            'NotificationChannelPreference',
        )

        linked = Preference.objects.get(user_id=self.linked_user_id)
        default = Preference.objects.get(user_id=self.default_user_id)
        self.assertTrue(linked.email_enabled)
        self.assertTrue(linked.telegram_enabled)
        self.assertTrue(default.email_enabled)
        self.assertFalse(default.telegram_enabled)
