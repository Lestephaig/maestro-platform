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

from .models import (
    Announcement,
    AnnouncementResponse,
    AnnouncementResponseAttachment,
)


class AnnouncementDetailTests(TestCase):
    def test_description_url_is_clickable_and_html_is_escaped(self):
        author = get_user_model().objects.create_user(
            username='author',
            email='author@example.com',
            password='test-pass',
        )
        announcement = Announcement.objects.create(
            author=author,
            title='Announcement with link',
            description='Details: https://example.com\n<script>alert("xss")</script>',
            status=Announcement.STATUS_PUBLISHED,
            is_approved=True,
        )

        response = self.client.get(
            reverse('announcements:detail', args=[announcement.id])
        )

        self.assertContains(response, '<a href="https://example.com"', html=False)
        self.assertContains(response, 'https://example.com')
        self.assertContains(response, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert("xss")</script>')


class AnnouncementLocationFilterTests(TestCase):
    def test_filters_by_country_and_city(self):
        author = get_user_model().objects.create_user(
            username='location-author', email='location@example.com'
        )
        Announcement.objects.create(
            author=author,
            title='Концерт в Москве',
            description='Описание',
            country='Россия',
            city='Москва',
        )
        Announcement.objects.create(
            author=author,
            title='Концерт в Минске',
            description='Описание',
            country='Беларусь',
            city='Минск',
        )

        response = self.client.get(reverse('announcements:list'), {
            'country': 'Россия',
            'city': 'Москва',
        })

        self.assertContains(response, 'Концерт в Москве')
        self.assertNotContains(response, 'Концерт в Минске')


class AnnouncementResponseAttachmentTests(TestCase):
    @classmethod
    def setUpClass(cls):
        super().setUpClass()
        cls.media_directory = tempfile.TemporaryDirectory()
        cls.media_override = override_settings(
            MEDIA_ROOT=Path(cls.media_directory.name) / 'media',
            PRIVATE_MEDIA_ROOT=Path(cls.media_directory.name) / 'private',
        )
        cls.media_override.enable()

    @classmethod
    def tearDownClass(cls):
        cls.media_override.disable()
        cls.media_directory.cleanup()
        super().tearDownClass()

    def setUp(self):
        self.author = get_user_model().objects.create_user(
            username='announcement-author',
            email='announcement-author@example.com',
            password='test-pass',
        )
        self.responder = get_user_model().objects.create_user(
            username='announcement-responder',
            email='announcement-responder@example.com',
            password='test-pass',
        )
        self.outsider = get_user_model().objects.create_user(
            username='announcement-outsider',
            email='announcement-outsider@example.com',
            password='test-pass',
        )
        self.staff = get_user_model().objects.create_user(
            username='announcement-staff',
            email='announcement-staff@example.com',
            password='test-pass',
            is_staff=True,
        )
        for user in (self.author, self.responder, self.outsider, self.staff):
            for slug in REQUIRED_LEGAL_DOCUMENT_SLUGS:
                LegalAcceptance.objects.create(
                    user=user,
                    document_slug=slug,
                    document_title=LEGAL_DOCUMENTS[slug]['title'],
                    document_version=LEGAL_DOCUMENTS[slug]['version'],
                )
        self.announcement = Announcement.objects.create(
            author=self.author,
            title='Нужен исполнитель',
            description='Описание',
            status=Announcement.STATUS_PUBLISHED,
            is_approved=True,
        )

    def test_multiple_attachments_can_be_added_to_response(self):
        self.client.force_login(self.responder)

        response = self.client.post(
            reverse('announcements:detail', args=[self.announcement.id]),
            {
                'message': 'Мой отклик',
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

        self.assertRedirects(
            response,
            reverse('announcements:detail', args=[self.announcement.id]),
        )
        announcement_response = AnnouncementResponse.objects.get()
        self.assertEqual(announcement_response.attachments.count(), 2)
        attachments = list(announcement_response.attachments.all())
        self.assertEqual(attachments[0].original_name, 'score.pdf')
        self.assertEqual(attachments[1].extension, 'PNG')
        self.assertNotIn('score.pdf', attachments[0].file.name)

    def test_disallowed_attachment_rejects_whole_response(self):
        self.client.force_login(self.responder)

        response = self.client.post(
            reverse('announcements:detail', args=[self.announcement.id]),
            {
                'message': 'Мой отклик',
                'attachments': SimpleUploadedFile(
                    'malware.exe',
                    b'MZ executable',
                    content_type='application/octet-stream',
                ),
            },
        )

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, 'не разрешён')
        self.assertFalse(AnnouncementResponse.objects.exists())

    def test_attachments_are_shown_to_responder_and_announcement_author(self):
        announcement_response = AnnouncementResponse.objects.create(
            announcement=self.announcement,
            responder=self.responder,
            message='',
        )
        attachment = AnnouncementResponseAttachment.objects.create(
            response=announcement_response,
            file=SimpleUploadedFile('stored.pdf', b'%PDF-private'),
            original_name='<score & parts>.pdf',
            content_type='application/pdf',
            size=2048,
        )

        self.client.force_login(self.responder)
        detail_response = self.client.get(
            reverse('announcements:detail', args=[self.announcement.id])
        )
        self.assertContains(detail_response, '&lt;score &amp; parts&gt;.pdf')
        self.assertContains(detail_response, f'PDF · {filesizeformat(2048)}')

        self.client.force_login(self.author)
        responses_response = self.client.get(
            reverse('announcements:responses', args=[self.announcement.id])
        )
        self.assertContains(responses_response, '&lt;score &amp; parts&gt;.pdf')
        self.assertContains(
            responses_response,
            reverse('announcements:download_response_attachment', args=[attachment.id]),
        )

    def test_only_participants_and_staff_can_access_attachment(self):
        announcement_response = AnnouncementResponse.objects.create(
            announcement=self.announcement,
            responder=self.responder,
        )
        attachment = AnnouncementResponseAttachment.objects.create(
            response=announcement_response,
            file=SimpleUploadedFile('document.pdf', b'%PDF-private'),
            original_name='document.pdf',
            content_type='application/pdf',
            size=12,
        )
        download_url = reverse(
            'announcements:download_response_attachment',
            args=[attachment.id],
        )

        self.client.force_login(self.outsider)
        self.assertEqual(self.client.get(download_url).status_code, 404)

        for user in (self.responder, self.author, self.staff):
            self.client.force_login(user)
            response = self.client.get(download_url)
            self.assertEqual(response.status_code, 200)
            self.assertEqual(b''.join(response.streaming_content), b'%PDF-private')
            self.assertIn('attachment;', response['Content-Disposition'])
            self.assertEqual(response['X-Content-Type-Options'], 'nosniff')

    def test_responder_can_see_response_text(self):
        AnnouncementResponse.objects.create(
            announcement=self.announcement,
            responder=self.responder,
            message='Мой отклик\n<script>alert("xss")</script>',
        )
        self.client.force_login(self.responder)

        response = self.client.get(
            reverse('announcements:detail', args=[self.announcement.id])
        )

        self.assertContains(response, 'Текст вашего отклика')
        self.assertContains(response, 'Мой отклик')
        self.assertContains(response, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert("xss")</script>')

    def test_responder_can_delete_response_and_respond_again(self):
        announcement_response = AnnouncementResponse.objects.create(
            announcement=self.announcement,
            responder=self.responder,
            message='Старый отклик',
        )
        attachment = AnnouncementResponseAttachment.objects.create(
            response=announcement_response,
            file=SimpleUploadedFile('document.pdf', b'%PDF-private'),
            original_name='document.pdf',
            content_type='application/pdf',
            size=12,
        )
        storage = attachment.file.storage
        stored_name = attachment.file.name
        self.assertTrue(storage.exists(stored_name))
        self.client.force_login(self.responder)

        with self.captureOnCommitCallbacks(execute=True):
            response = self.client.post(
                reverse(
                    'announcements:delete_response',
                    args=[announcement_response.id],
                )
            )

        self.assertRedirects(
            response,
            reverse('announcements:detail', args=[self.announcement.id]),
        )
        self.assertFalse(AnnouncementResponse.objects.exists())
        self.assertFalse(storage.exists(stored_name))

        detail_response = self.client.get(
            reverse('announcements:detail', args=[self.announcement.id])
        )
        self.assertContains(detail_response, 'Откликнуться на объявление')
        self.assertContains(detail_response, 'enctype="multipart/form-data"')

        repeat_response = self.client.post(
            reverse('announcements:detail', args=[self.announcement.id]),
            {'message': 'Новый отклик'},
        )
        self.assertRedirects(
            repeat_response,
            reverse('announcements:detail', args=[self.announcement.id]),
        )
        self.assertTrue(
            AnnouncementResponse.objects.filter(
                announcement=self.announcement,
                responder=self.responder,
                message='Новый отклик',
            ).exists()
        )

    def test_another_user_cannot_delete_response(self):
        announcement_response = AnnouncementResponse.objects.create(
            announcement=self.announcement,
            responder=self.responder,
            message='Мой отклик',
        )
        delete_url = reverse(
            'announcements:delete_response',
            args=[announcement_response.id],
        )

        self.client.force_login(self.outsider)
        self.assertEqual(self.client.post(delete_url).status_code, 404)
        self.assertTrue(AnnouncementResponse.objects.filter(id=announcement_response.id).exists())

        self.client.force_login(self.responder)
        self.assertEqual(self.client.get(delete_url).status_code, 405)
        self.assertTrue(AnnouncementResponse.objects.filter(id=announcement_response.id).exists())
