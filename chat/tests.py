from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from accounts.models import LegalAcceptance
from core.legal import LEGAL_DOCUMENTS, REQUIRED_LEGAL_DOCUMENT_SLUGS
from .models import ChatRoom, Message


class ChatRoomTests(TestCase):
    def test_message_url_is_clickable_and_html_is_escaped(self):
        user = get_user_model().objects.create_user(
            username='sender',
            email='sender@example.com',
            password='test-pass',
        )
        other_user = get_user_model().objects.create_user(
            username='recipient',
            email='recipient@example.com',
            password='test-pass',
        )
        for slug in REQUIRED_LEGAL_DOCUMENT_SLUGS:
            LegalAcceptance.objects.create(
                user=user,
                document_slug=slug,
                document_title=LEGAL_DOCUMENTS[slug]['title'],
                document_version=LEGAL_DOCUMENTS[slug]['version'],
            )
        room = ChatRoom.objects.create(performer=user, client=other_user)
        Message.objects.create(
            room=room,
            sender=other_user,
            text='Link: https://example.com\n<script>alert("xss")</script>',
        )

        self.client.force_login(user)
        response = self.client.get(reverse('chat_room', args=[room.id]))

        self.assertContains(response, '<a href="https://example.com"', html=False)
        self.assertContains(response, 'https://example.com')
        self.assertContains(response, '&lt;script&gt;alert(&quot;xss&quot;)&lt;/script&gt;')
        self.assertNotContains(response, '<script>alert("xss")</script>')
