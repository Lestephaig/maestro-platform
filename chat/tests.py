import tempfile
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.template.defaultfilters import filesizeformat
from django.test import TestCase
from django.test.utils import override_settings
from django.urls import reverse

from accounts.models import LegalAcceptance
from core.legal import LEGAL_DOCUMENTS, REQUIRED_LEGAL_DOCUMENT_SLUGS
from .models import ChatRoom, Message, MessageAttachment


class ChatRoomTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_directory = tempfile.TemporaryDirectory()
        cls.media_override = override_settings(
            MEDIA_ROOT=Path(cls.media_directory.name),
            PRIVATE_MEDIA_ROOT=Path(cls.media_directory.name) / 'private',
            CHANNEL_LAYERS={
                'default': {
                    'BACKEND': 'channels.layers.InMemoryChannelLayer',
                },
            },
        )
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        cls.media_directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.user = get_user_model().objects.create_user(
            username='sender',
            email='sender@example.com',
            password='test-pass',
        )
        self.other_user = get_user_model().objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='test-pass',
        )
        self.outsider = get_user_model().objects.create_user(
            username='outsider',
            email='outsider@example.com',
            password='test-pass',
        )
        for account in (self.user, self.other_user, self.outsider):
            self._accept_legal_documents(account)
        self.room = ChatRoom.objects.create(
            performer=self.user,
            client=self.other_user,
        )

    def _accept_legal_documents(self, user):
        for slug in REQUIRED_LEGAL_DOCUMENT_SLUGS:
            LegalAcceptance.objects.create(
                user=user,
                document_slug=slug,
                document_title=LEGAL_DOCUMENTS[slug]['title'],
                document_version=LEGAL_DOCUMENTS[slug]['version'],
            )

    def test_message_url_is_clickable_and_html_is_escaped(self):
        Message.objects.create(
            room=self.room,
            sender=self.other_user,
            text='Link: https://example.com\n<script>alert("xss")</script>',
        )

        self.client.force_login(self.user)
        response = self.client.get(reverse('chat_room', args=[self.room.id]))

        self.assertContains(response, '<a href="https://example.com"', html=False)
        self.assertContains(response, 'https://example.com')
        self.assertContains(response, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert("xss")</script>')

    def test_multiple_attachments_can_be_sent_without_text(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('send_message', args=[self.room.id]),
            {
                'text': '',
                'attachments': [
                    SimpleUploadedFile(
                        'score.pdf',
                        b'%PDF-1.7\nexample',
                        content_type='application/pdf',
                    ),
                    SimpleUploadedFile(
                        'photo.PNG',
                        b'image contents are not inspected',
                        content_type='image/png',
                    ),
                ],
            },
        )

        self.assertEqual(response.status_code, 201)
        message = Message.objects.get()
        self.assertEqual(message.text, '')
        self.assertEqual(message.attachments.count(), 2)
        self.assertEqual(response.json()['attachments'][0]['name'], 'score.pdf')
        self.assertEqual(response.json()['attachments'][1]['extension'], 'PNG')
        self.assertNotIn('score.pdf', message.attachments.first().file.name)

    def test_disallowed_extension_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('send_message', args=[self.room.id]),
            {
                'attachments': SimpleUploadedFile(
                    'malware.exe',
                    b'MZ executable',
                    content_type='application/octet-stream',
                ),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('не разрешён', response.json()['error'])
        self.assertFalse(Message.objects.exists())

    def test_allowed_extension_does_not_require_matching_file_signature(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('send_message', args=[self.room.id]),
            {
                'attachments': SimpleUploadedFile(
                    'photo.JpG',
                    b'contents without a JPEG signature',
                    content_type='image/jpeg',
                ),
            },
        )

        self.assertEqual(response.status_code, 201)
        attachment = MessageAttachment.objects.get()
        self.assertEqual(attachment.original_name, 'photo.JpG')
        self.assertEqual(attachment.extension, 'JPG')
        self.assertTrue(attachment.file.name.endswith('.jpg'))

    @override_settings(CHAT_ATTACHMENT_MAX_SIZE_MB=1)
    def test_attachment_over_size_limit_is_rejected(self):
        self.client.force_login(self.user)
        response = self.client.post(
            reverse('send_message', args=[self.room.id]),
            {
                'attachments': SimpleUploadedFile(
                    'large.pdf',
                    b'%PDF-' + b'a' * (1024 * 1024),
                    content_type='application/pdf',
                ),
            },
        )

        self.assertEqual(response.status_code, 400)
        self.assertIn('превышает лимит 1 МБ', response.json()['error'])
        self.assertFalse(Message.objects.exists())

    def test_attachment_is_visible_in_room_with_name_type_and_size(self):
        message = Message.objects.create(
            room=self.room,
            sender=self.other_user,
            text='',
        )
        MessageAttachment.objects.create(
            message=message,
            file=SimpleUploadedFile('stored.pdf', b'%PDF-test'),
            original_name='<score & parts>.pdf',
            content_type='application/pdf',
            size=2048,
        )
        self.client.force_login(self.user)

        response = self.client.get(reverse('chat_room', args=[self.room.id]))

        self.assertContains(response, '&lt;score &amp; parts&gt;.pdf')
        self.assertContains(response, f'PDF · {filesizeformat(2048)}')
        self.assertContains(response, 'bi-download')

    def test_only_room_participants_can_open_or_download_attachment(self):
        message = Message.objects.create(
            room=self.room,
            sender=self.user,
            text='file',
        )
        attachment = MessageAttachment.objects.create(
            message=message,
            file=SimpleUploadedFile('document.pdf', b'%PDF-private'),
            original_name='document.pdf',
            content_type='application/pdf',
            size=12,
        )

        self.client.force_login(self.outsider)
        forbidden_response = self.client.get(
            reverse('open_chat_attachment', args=[attachment.id])
        )
        self.assertEqual(forbidden_response.status_code, 404)

        self.client.force_login(self.other_user)
        response = self.client.get(
            reverse('download_chat_attachment', args=[attachment.id])
        )
        self.assertEqual(response.status_code, 200)
        self.assertEqual(b''.join(response.streaming_content), b'%PDF-private')
        self.assertIn('attachment;', response['Content-Disposition'])
        self.assertEqual(response['X-Content-Type-Options'], 'nosniff')
