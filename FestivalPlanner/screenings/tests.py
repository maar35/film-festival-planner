import datetime

from django.db import IntegrityError
from django.test import TestCase

from films.tests import create_film
from screenings.models import Screening
from theaters.models import Theater, Screen


class ScreeningModelTests(TestCase):
    def setUp(self):
        super().setUp()
        self.film = create_film(1, 'The Houses Look All the Same', 55)
        city = self.film.festival.base.home_city
        theater_kwargs = {
            'theater_id': 1,
            'city': city,
            'parse_name': 'Tuschinski',
            'abbreviation': 't',
            'priority': Theater.Priority.HIGH,
        }
        self.theater = Theater.theaters.create(**theater_kwargs)
        screen_kwargs = {
            'screen_id': 1,
            'theater': self.theater,
            'parse_name': 'Tuschinski 1',
            'abbreviation': 't1',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen = Screen.screens.create(**screen_kwargs)

    def test_unique_constraint(self):
        """t
        Screenings can not have the same film, screen and start time.
        """
        # Arrange.
        start_dt = datetime.datetime.fromisoformat('2022-10-31 20:00').replace(tzinfo=None)
        screening_kwargs = {
            'film': self.film,
            'screen': self.screen,
            'start_dt': start_dt,
            'subtitles': 'en',
            'q_and_a': True,
        }
        end_dt_1 = start_dt + datetime.timedelta(minutes=101)
        end_dt_2 = start_dt + datetime.timedelta(minutes=21)
        screening_1 = Screening(end_dt=end_dt_1, **screening_kwargs)
        screening_2 = Screening(end_dt=end_dt_2, **screening_kwargs)

        # Act.
        screening_1.save()

        # Assert.
        self.assertRaises(IntegrityError, screening_2.save)

    def test_overlapping_screenings_accepted(self):
        """
        Screenings with the same film and screen can overlap in time.
        -- THIS IS NOT DESIRABLE --
        """
        # Arrange.
        end_dt = datetime.datetime.fromisoformat('2024-02-06 23:14').replace(tzinfo=None)
        screening_kwargs = {
            'film': self.film,
            'screen': self.screen,
            'end_dt': end_dt,
            'subtitles': 'en',
            'q_and_a': True,
        }
        start_dt_1 = end_dt - datetime.timedelta(minutes=98)
        start_dt_2 = end_dt - datetime.timedelta(minutes=74)
        screening_1 = Screening(start_dt=start_dt_1, **screening_kwargs)
        screening_2 = Screening(start_dt=start_dt_2, **screening_kwargs)

        # Act.
        screening_1.save()
        screening_2.save()

        # Assert.
        self.assertEqual(Screening.screenings.count(), 2)
