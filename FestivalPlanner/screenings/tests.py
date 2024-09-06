import datetime
from http import HTTPStatus

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from authentication.models import FilmFan
from festival_planner import debug_tools
from festivals.models import FestivalBase, Festival, switch_festival, current_festival
from films.models import Film
from films.tests import create_film, ViewsTestCase, get_decoded_content
from screenings.models import Screening, Attendance
from theaters.models import Theater, Screen, City


def arrange_screening_attributes():
    film = create_film(1, 'The Houses Look All the Same', 55)
    city = film.festival.base.home_city
    theater_kwargs = {
        'theater_id': 1,
        'city': city,
        'parse_name': 'Tuschinski',
        'abbreviation': 't',
        'priority': Theater.Priority.HIGH,
    }
    theater = Theater.theaters.create(**theater_kwargs)
    screen_kwargs = {
        'screen_id': 1,
        'theater': theater,
        'parse_name': 'Tuschinski 1',
        'abbreviation': 't1',
        'address_type': Screen.ScreenAddressType.PHYSICAL,
    }
    screen = Screen.screens.create(**screen_kwargs)
    return film, theater, screen


class ScreeningModelTests(TestCase):
    def setUp(self):
        super().setUp()
        self.film, self.theater, self.screen = arrange_screening_attributes()

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


class AttendanceModelTests(TestCase):

    def setUp(self):
        debug_tools.SUPPRESS_DEBUG_PRINT = True
        self.film, self.theater, self.screen = arrange_screening_attributes()

    def _arrange_screening_kwargs(self, iso_dt=None, minutes=None):
        start_dt = datetime.datetime.fromisoformat(iso_dt or '2024-02-10 23:14').replace(tzinfo=None)
        minutes = minutes or 115
        end_dt = start_dt + datetime.timedelta(minutes=minutes)
        screening_kwargs = {
            'film': self.film,
            'screen': self.screen,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'subtitles': 'en',
            'q_and_a': True,
        }
        return screening_kwargs

    def test_attendance_string_leading_zero(self):
        # Arrange.
        jim = FilmFan.film_fans.create(name='Jim', seq_nr=1)
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2024-02-06 21:00')
        screening = Screening.screenings.create(**screening_kwargs)
        attendance = Attendance(fan=jim, screening=screening)

        # Act.
        string = str(attendance)

        # Assert.
        self.assertRegex(string, r'Tue 6Feb')

    def test_attendance_string_decimal_zero(self):
        # Arrange.
        fan = FilmFan.film_fans.create(name='Mick', seq_nr=1)
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2021-11-30 22:30')
        screening = Screening.screenings.create(**screening_kwargs)
        attendance = Attendance(fan=fan, screening=screening)

        # Act.
        string = str(attendance)

        # Assert.
        self.assertRegex(string, r'Tue 30Nov')


class ScreeningViewsTests(TestCase):

    def setUp(self):
        super().setUp()
        debug_tools.SUPPRESS_DEBUG_PRINT = True

        city = City.cities.create(city_id=2, name='Venezia', country='it')

        base_kwargs = {
            'mnemonic': 'Biennali',
            'name': 'La Biennale di Venezia',
            'home_city': city,
        }
        festival_base = FestivalBase.festival_bases.create(**base_kwargs)

        year = 2024
        festival_kwargs = {
            'base': festival_base,
            'year': year,
            'start_date': datetime.date(year, 8, 28),
            'end_date': datetime.date(year, 9, 7),
            'festival_color': 'red',
        }
        self.festival = Festival.festivals.create(**festival_kwargs)

        film_kwargs = {
            'festival': self.festival,
            'film_id': 7,
            'seq_nr': 15,
            'sort_title': 'babygirl',
            'title': 'Babygirl',
            'duration': datetime.timedelta(minutes=114),
            'medium_category': 'films',
            'url': 'https://www.labiennale.org/en/cinema/2024/venezia-81-competition/babygirl'
        }
        self.film = Film.films.create(**film_kwargs)

        theater_kwargs = {
            'theater_id': 1,
            'city': city,
            'parse_name': 'Palazzo del Cinema',
            'abbreviation': 'palazzo',
            'priority': Theater.Priority.HIGH,
        }
        theater = Theater.theaters.create(**theater_kwargs)

        screen_kwargs = {
            'screen_id': 1,
            'theater': theater,
            'parse_name': 'Sala Grande',
            'abbreviation': '-sg',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen_sg = Screen.screens.create(**screen_kwargs)

        screen_kwargs = {
            'screen_id': 2,
            'theater': theater,
            'parse_name': 'PalaBiennale',
            'abbreviation': '-sd',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen_b = Screen.screens.create(**screen_kwargs)

    def arrange_regular_user_client(self):
        views_testcase = ViewsTestCase()
        views_testcase.setUp()
        client = views_testcase.client
        session = client.session

        regular_credentials = views_testcase.regular_credentials
        request = views_testcase.get_regular_fan_request()
        fan_name = request.session['fan_name']
        fan = FilmFan.film_fans.get(name=fan_name)
        logged_in = views_testcase.login(regular_credentials)
        self.assertIs(logged_in, True)

        switch_festival(session, self.festival)

        return client, fan

    def arrange_create_screening(self, screen, start_dt):
        screening_kwargs = {
            'film': self.film,
            'screen': screen,
            'start_dt': start_dt,
            'end_dt': start_dt + self.film.duration,
            'subtitles': 'it, en',
            'q_and_a': True,
        }
        screening = Screening.screenings.create(**screening_kwargs)
        return screening

    def assert_screening_status(self, response, screening_status):
        def make_re_str(re_str):
            return str(re_str).replace('(', '\\(').replace(')', '\\)')

        content = get_decoded_content(response)
        color_pair = Screening.color_pair_by_screening_status[screening_status]
        background = make_re_str(color_pair['background'])
        color = make_re_str(color_pair['color'])
        re_screening = (r'<span\s+class="day-schema-screening"\s+'
                        + f'style="background: {background}; color: {color};')
        self.assertRegex(content, re_screening)


class DaySchemaViewTests(ScreeningViewsTests):
    def test_screening_in_day_schema(self):
        """
        A screening is found in the day schema of its start date.
        """
        # Arrange.
        client, _ = self.arrange_regular_user_client()
        session = client.session

        start_dt = datetime.datetime.fromisoformat('2024-08-30 11:15').replace(tzinfo=None)
        _ = self.arrange_create_screening(self.screen_sg, start_dt)

        # Act.
        response = client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.FREE)

    def test_attendance(self):
        # Arrange.
        client, fan = self.arrange_regular_user_client()
        session = client.session

        start_dt = datetime.datetime.fromisoformat('2024-08-31 11:30').replace(tzinfo=None)
        screening = self.arrange_create_screening(self.screen_b, start_dt)

        attendance = Attendance.attendances.create(fan=fan, screening=screening)

        # Act.
        response = client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.ATTENDS)


class DetailsViewTest(ScreeningViewsTests):
    pass
