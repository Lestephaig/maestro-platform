from django.contrib.auth import get_user_model
from django.test import TestCase
from django.urls import reverse

from .forms import PerformerProfileForm
from .models import MusicInstrument, PerformerProfile


class PerformerDirectoryFilterTests(TestCase):
    def setUp(self):
        user = get_user_model().objects.create_user('artist', email='artist@example.com')
        PerformerProfile.objects.create(
            user=user,
            full_name='Анна Иванова',
            country='Россия',
            city='Москва',
        )

    def test_filters_by_country_and_city(self):
        response = self.client.get(reverse('performers:specialists'), {
            'country': 'Россия',
            'city': 'Москва',
        })

        self.assertContains(response, 'Анна Иванова')
        self.assertEqual(response.context['total_count'], 1)


class MusicInstrumentTests(TestCase):
    def test_profile_form_orders_admin_managed_instruments_alphabetically(self):
        MusicInstrument.objects.create(name='Янгчин')
        MusicInstrument.objects.create(name='Гусли')
        user = get_user_model().objects.create_user('instrumentalist', email='i@example.com')
        profile = PerformerProfile.objects.create(user=user, full_name='Музыкант')

        choices = [value for value, _label in PerformerProfileForm(instance=profile).fields['instrument'].choices if value]

        self.assertEqual(choices, sorted(choices, key=str.casefold))

# Create your tests here.
