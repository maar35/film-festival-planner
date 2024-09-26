import datetime
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from authentication.models import FilmFan
from availabilities.models import Availabilities
from films.tests import get_decoded_content
from screenings.tests import ScreeningViewsTests


class AvailabilitiesModelTests(TestCase):
    def test_str(self):
        """
        Test the string representation of a availability records.
        """
        # Arrange.
        screening_view_tests = ScreeningViewsTests()
        screening_view_tests.setUp()
        client, _ = screening_view_tests.arrange_get_regular_user_props()

        fan = FilmFan.film_fans.create(name='Jimmie', is_admin=False, seq_nr=3)
        # self.assertEqual(FilmFan.film_fans.count(), 1)
        print(f'\n{fan=}')

        start_dt_1 = datetime.datetime.fromisoformat('2024-09-30 00:00')
        end_dt_1 = datetime.datetime.fromisoformat('2024-10-06 00:00')
        availability_kwargs_1 = {'fan': fan, 'start_dt': start_dt_1, 'end_dt': end_dt_1}
        availability_1 = Availabilities.availabilities.create(**availability_kwargs_1)

        start_dt_2 = datetime.datetime.fromisoformat('2024-09-29 14:59')
        end_dt_2 = datetime.datetime.fromisoformat('2024-09-29 23:00')
        availability_kwargs_2 = {'fan': fan, 'start_dt': start_dt_2, 'end_dt': end_dt_2}
        availability_2 = Availabilities.availabilities.create(**availability_kwargs_2)

        # Act.
        print(f'\n{availability_1}')
        print(f'{availability_2}')
        response = client.get(reverse('availabilities:list'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        print(f'\n@@\n{get_decoded_content(response)}\n')
        self.assertEqual(Availabilities.availabilities.count(), 2)
