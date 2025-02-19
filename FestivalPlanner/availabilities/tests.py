import datetime
from http import HTTPStatus

from django.test import TestCase
from django.urls import reverse

from authentication.models import FilmFan
from availabilities.models import Availabilities
from festivals.models import current_festival
from screenings.models import Screening
from screenings.tests import ScreeningViewsTests


class AvailabilitiesModelTests(TestCase):
    def test_str(self):
        """
        Test the string representation of a availability records.
        """
        # Arrange.
        screening_view_tests = ScreeningViewsTests()
        screening_view_tests.setUp()
        _ = screening_view_tests.arrange_regular_user_props()
        client = screening_view_tests.client

        fan = FilmFan.film_fans.create(name='Jimmie', is_admin=False, seq_nr=3)

        start_dt_1 = datetime.datetime.fromisoformat('2024-09-30 00:00')
        end_dt_1 = datetime.datetime.fromisoformat('2024-10-06 00:00')
        availability_kwargs_1 = {'fan': fan, 'start_dt': start_dt_1, 'end_dt': end_dt_1}
        availability_1 = Availabilities.availabilities.create(**availability_kwargs_1)

        start_dt_2 = datetime.datetime.fromisoformat('2024-09-29 14:59')
        end_dt_2 = datetime.datetime.fromisoformat('2024-09-29 23:00')
        availability_kwargs_2 = {'fan': fan, 'start_dt': start_dt_2, 'end_dt': end_dt_2}
        availability_2 = Availabilities.availabilities.create(**availability_kwargs_2)

        # Act.
        response = client.get(reverse('availabilities:list'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(str(availability_1), 'Jimmie is available between 2024-09-30 00:00 and 2024-10-06 00:00')
        self.assertEqual(str(availability_2), 'Jimmie is available between 2024-09-29 14:59 and 2024-09-29 23:00')
        self.assertEqual(Availabilities.availabilities.count(), 2)


class AvailabilityViewTestCase(TestCase):
    """
    TODO: Create a few tests here, created issue #392 for it.
    """
    pass


class DaySchemaViewTests(ScreeningViewsTests):
    def test_screening_in_day_schema_available(self):
        """
        A screening is found in the day schema of its start date.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()

        start_dt = datetime.datetime.fromisoformat('2024-08-30 11:15').replace(tzinfo=None)
        _ = self.arrange_create_screening(self.screen_sg, start_dt)

        end_dt = start_dt + datetime.timedelta(hours=8)
        availability_kwargs = {'fan': fan, 'start_dt': start_dt, 'end_dt': end_dt}
        Availabilities.availabilities.create(**availability_kwargs)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.FREE)
        self.assertContains(response, f'{fan.name} 11:15 - 19:15')

    def test_screening_in_day_schema_unavailable(self):
        """
        A screening is found in the day schema of its start date, but our fan is unavailable.
        """
        # Arrange.
        _ = self.arrange_regular_user_props()

        start_dt = datetime.datetime.fromisoformat('2024-08-30 11:15').replace(tzinfo=None)
        _ = self.arrange_create_screening(self.screen_sg, start_dt)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.UNAVAILABLE)

    def test_availability_in_day_schema_daybreak(self):
        """
        Availability is displayed in the day schema till day-break-time.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()

        start_dt = datetime.datetime.fromisoformat('2024-08-30 20:45').replace(tzinfo=None)
        _ = self.arrange_create_screening(self.screen_sg, start_dt)

        end_dt = start_dt + datetime.timedelta(hours=12)
        availability_kwargs = {'fan': fan, 'start_dt': start_dt, 'end_dt': end_dt}
        Availabilities.availabilities.create(**availability_kwargs)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.FREE)
        self.assertContains(response, f'{fan.name} {start_dt:%H:%M} - 06:00')
