import json
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.db import transaction
from django.test import TestCase, override_settings

from accounts.models import TelegramConnection
from chat.models import ChatRoom, Message, MessageAttachment
from notifications.deliveries import (
    _send_telegram,
    build_message_preview,
    build_telegram_preview,
    enqueue_chat_message_deliveries,
    get_active_channels,
    process_pending_deliveries,
)
from notifications.models import Notification, NotificationDelivery, NotificationPreference


@override_settings(
    SITE_URL='https://maestro.example',
    TELEGRAM_BOT_TOKEN='test-token',
    TELEGRAM_SEND_TIMEOUT=4,
    NOTIFICATION_DELIVERY_MAX_ATTEMPTS=3,
    NOTIFICATION_DELIVERY_RETRY_SECONDS=60,
)
class ChatMessageDeliveryTests(TestCase):
    def setUp(self):
        user_model = get_user_model()
        self.sender = user_model.objects.create_user(
            username='sender',
            email='sender@example.com',
            display_name='<Маэстро & друг>',
        )
        self.recipient = user_model.objects.create_user(
            username='recipient',
            email='recipient@example.com',
            is_email_verified=True,
        )
        self.room = ChatRoom.objects.create(
            performer=self.sender,
            client=self.recipient,
        )
        self.preference = NotificationPreference.get_or_create_for(
            self.recipient,
            Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
        )

    def _message(self, text='Новое сообщение'):
        return Message.objects.create(room=self.room, sender=self.sender, text=text)

    def test_active_channel_matrix(self):
        TelegramConnection.objects.create(
            user=self.recipient,
            telegram_chat_id=123456,
        )
        cases = (
            (False, False, set()),
            (True, False, {'email'}),
            (False, True, {'telegram'}),
            (True, True, {'email', 'telegram'}),
        )
        for email_enabled, telegram_enabled, expected in cases:
            with self.subTest(email=email_enabled, telegram=telegram_enabled):
                self.preference.email_enabled = email_enabled
                self.preference.telegram_enabled = telegram_enabled
                self.preference.save()
                self.assertEqual(
                    get_active_channels(
                        self.recipient,
                        Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
                    ),
                    expected,
                )

        self.recipient.telegram_connection.delete()
        self.preference.email_enabled = False
        self.preference.telegram_enabled = True
        self.preference.save()
        self.assertEqual(
            get_active_channels(
                self.recipient,
                Notification.NOTIFICATION_TYPE_CHAT_MESSAGE,
            ),
            set(),
        )

    def test_delivery_event_is_created_only_after_commit(self):
        self.preference.email_enabled = True
        self.preference.telegram_enabled = False
        self.preference.save()

        with self.captureOnCommitCallbacks(execute=True):
            with transaction.atomic():
                self._message()
                self.assertFalse(NotificationDelivery.objects.exists())

        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.channel, NotificationDelivery.CHANNEL_EMAIL)
        self.assertEqual(delivery.recipient, self.recipient)

    def test_both_disabled_creates_no_external_delivery(self):
        self.preference.email_enabled = False
        self.preference.telegram_enabled = False
        self.preference.save()
        message = self._message()

        self.assertEqual(enqueue_chat_message_deliveries(message.pk), 0)
        self.assertFalse(NotificationDelivery.objects.exists())

    def test_sender_is_never_notified_about_own_message(self):
        own_room = ChatRoom.objects.create(
            performer=self.sender,
            client=self.sender,
        )
        message = Message.objects.create(
            room=own_room,
            sender=self.sender,
            text='Заметка себе',
        )

        self.assertEqual(enqueue_chat_message_deliveries(message.pk), 0)
        self.assertFalse(
            NotificationDelivery.objects.filter(message=message).exists()
        )

    def test_telegram_payload_escapes_preview_and_links_to_room(self):
        self.preference.email_enabled = False
        self.preference.telegram_enabled = True
        self.preference.save()
        TelegramConnection.objects.create(user=self.recipient, telegram_chat_id=777)
        message = self._message('<b>опасно & "важно"</b>')
        enqueue_chat_message_deliveries(message.pk)
        delivery = NotificationDelivery.objects.get()

        class Response:
            def __enter__(self):
                return self

            def __exit__(self, *args):
                return False

            def read(self):
                return b'{"ok": true}'

        with patch('notifications.deliveries.urllib_request.urlopen', return_value=Response()) as urlopen:
            self.assertTrue(_send_telegram(delivery))

        request = urlopen.call_args.args[0]
        payload = json.loads(request.data.decode('utf-8'))
        self.assertEqual(payload['chat_id'], 777)
        self.assertEqual(payload['parse_mode'], 'HTML')
        self.assertIn('&lt;Маэстро &amp; друг&gt;', payload['text'])
        self.assertIn(
            '<i>«&lt;b&gt;опасно &amp; &quot;важно&quot;&lt;/b&gt;»</i>',
            payload['text'],
        )
        self.assertNotIn('<b>опасно', payload['text'])
        button = payload['reply_markup']['inline_keyboard'][0][0]
        self.assertEqual(button['text'], 'Открыть сообщение')
        self.assertEqual(button['url'], f'https://maestro.example/chat/{self.room.pk}/')
        self.assertEqual(urlopen.call_args.kwargs['timeout'], 4)

    def test_attachment_only_preview(self):
        message = self._message('')
        MessageAttachment.objects.create(
            message=message,
            file=SimpleUploadedFile('photo.jpg', b'image'),
            original_name='photo.jpg',
            content_type='image/jpeg',
            size=5,
        )
        loaded = Message.objects.prefetch_related('attachments').get(pk=message.pk)
        self.assertEqual(build_message_preview(loaded), '[Изображение]')

    def test_telegram_preview_is_truncated_after_50_characters(self):
        text = '1234567890' * 6
        message = self._message(text)

        preview = build_telegram_preview(message)

        self.assertEqual(preview, text[:50] + '...')
        self.assertEqual(len(preview), 53)

    def test_short_telegram_preview_has_no_ellipsis(self):
        message = self._message('Короткое сообщение')

        self.assertEqual(build_telegram_preview(message), 'Короткое сообщение')

    @patch('notifications.deliveries._send_telegram', return_value=True)
    @patch('notifications.deliveries._send_email', return_value=True)
    def test_repeat_enqueue_and_processing_do_not_duplicate(self, send_email, send_telegram):
        self.preference.telegram_enabled = True
        self.preference.save()
        TelegramConnection.objects.create(user=self.recipient, telegram_chat_id=123)
        message = self._message()

        self.assertEqual(enqueue_chat_message_deliveries(message.pk), 2)
        self.assertEqual(enqueue_chat_message_deliveries(message.pk), 0)
        self.assertEqual(NotificationDelivery.objects.count(), 2)

        first = process_pending_deliveries()
        second = process_pending_deliveries()
        self.assertEqual(first, {'processed': 2, 'sent': 2})
        self.assertEqual(second, {'processed': 0, 'sent': 0})
        send_email.assert_called_once()
        send_telegram.assert_called_once()

    @patch('notifications.deliveries._send_telegram', side_effect=RuntimeError('API unavailable'))
    def test_telegram_failure_is_retried_without_affecting_message(self, send_telegram):
        self.preference.email_enabled = False
        self.preference.telegram_enabled = True
        self.preference.save()
        TelegramConnection.objects.create(user=self.recipient, telegram_chat_id=123)
        message = self._message('Секретный полный текст сообщения')
        enqueue_chat_message_deliveries(message.pk)

        result = process_pending_deliveries()

        self.assertEqual(result, {'processed': 1, 'sent': 0})
        self.assertTrue(Message.objects.filter(pk=message.pk).exists())
        delivery = NotificationDelivery.objects.get()
        self.assertEqual(delivery.status, NotificationDelivery.STATUS_PENDING)
        self.assertEqual(delivery.attempts, 1)
        self.assertEqual(delivery.last_error, 'RuntimeError')
        send_telegram.assert_called_once()
