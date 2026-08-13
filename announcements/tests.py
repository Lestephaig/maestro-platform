from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .models import Announcement


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
