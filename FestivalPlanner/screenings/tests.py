import datetime
from http import HTTPStatus

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from authentication.models import FilmFan
from availabilities.models import Availabilities
from festival_planner import debug_tools
from festivals.models import FestivalBase, Festival, switch_festival, current_festival
from films.models import Film, FAN_NAMES_BY_FESTIVAL_BASE, LOWEST_PLANNABLE_RATING, FilmFanFilmRating, set_current_fan
from films.tests import create_film, ViewsTestCase, get_decoded_content
from films.views import MAX_SHORT_MINUTES
from screenings.models import Screening, Attendance
from theaters.models import Theater, Screen, City


def arrange_get_datetime(dt_string):
    return datetime.datetime.fromisoformat(dt_string).replace(tzinfo=None)


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
        start_dt = arrange_get_datetime('2022-10-31 20:00')
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
        end_dt = arrange_get_datetime('2024-02-06 23:14')
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
        self.assertRegex(string, r'Tue 6 Feb')

    def test_attendance_string_decimal_zero(self):
        # Arrange.
        fan = FilmFan.film_fans.create(name='Mick', seq_nr=1)
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2021-11-30 22:30')
        screening = Screening.screenings.create(**screening_kwargs)
        attendance = Attendance(fan=fan, screening=screening)

        # Act.
        string = str(attendance)

        # Assert.
        self.assertRegex(string, r'Tue 30 Nov')


class ScreeningViewsTests(ViewsTestCase):

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
            'abbreviation': '-g',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen_sg = Screen.screens.create(**screen_kwargs)

        screen_kwargs = {
            'screen_id': 2,
            'theater': theater,
            'parse_name': 'PalaBiennale',
            'abbreviation': '-b',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen_b = Screen.screens.create(**screen_kwargs)

    def arrange_regular_user_props(self):
        fan = self.regular_fan
        logged_in = self.login(self.regular_credentials)
        self.assertIs(logged_in, True)

        request = self.get_regular_fan_request()
        set_current_fan(request)

        switch_festival(self.session, self.festival)
        FAN_NAMES_BY_FESTIVAL_BASE[self.festival.base.mnemonic] = [fan.name]

        return fan

    def arrange_create_screening(self, screen, start_dt, film=None):
        film = film or self.film
        screening_kwargs = {
            'film': film,
            'screen': screen,
            'start_dt': start_dt,
            'end_dt': start_dt + film.duration,
            'subtitles': 'it, en',
            'q_and_a': True,
        }
        screening = Screening.screenings.create(**screening_kwargs)
        return screening

    def assert_screening_status(self, response, screening_status, view='day_schema'):
        def make_re_str(re_str):
            return str(re_str).replace('(', '\\(').replace(')', '\\)')

        prefix_by_view = {
            'day_schema': r'<span\s+class="day-schema-screening"\s+',
            'details': r'<td\s+',
        }
        prefix = prefix_by_view[view]

        content = get_decoded_content(response)
        color_pair = Screening.color_pair_by_screening_status[screening_status]
        background = make_re_str(color_pair['background'])
        color = make_re_str(color_pair['color'])
        re_screening = (f'{prefix}' + f'style="background: {background}; color: {color};')
        self.assertRegex(content, re_screening)


class DaySchemaViewTests(ScreeningViewsTests):
    def test_screening_in_day_schema(self):
        """
        A screening is found in the day schema of its start date.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-30 11:15')
        _ = self.arrange_create_screening(self.screen_sg, start_dt)

        kwargs = {'fan': fan, 'start_dt': start_dt, 'end_dt': start_dt + datetime.timedelta(hours=8)}
        Availabilities.availabilities.create(**kwargs)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.FREE)

    def test_attendance(self):
        """
        An attended screening has the correct colors in the day schema.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-31 11:30')
        screening = self.arrange_create_screening(self.screen_b, start_dt)

        _ = Attendance.attendances.create(fan=fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.ATTENDS)


class DetailsViewTest(ScreeningViewsTests):
    def test_attendance(self):
        """
        An attended screening is correctly displayed in the screening details view.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-30 11:15')
        screening = self.arrange_create_screening(self.screen_sg, start_dt)

        _ = Attendance.attendances.create(fan=fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:details', args=[screening.pk]))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.ATTENDS, view='details')

    def test_attends_film(self):
        """
        If a screening is attended, other screenings of the same film are marked 'attends film'.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()

        start_dt_1 = arrange_get_datetime('2024-08-30 11:15')
        screening_1 = self.arrange_create_screening(self.screen_sg, start_dt_1)
        start_dt_2 = arrange_get_datetime('2024-08-31 11:30')
        screening_2 = self.arrange_create_screening(self.screen_b, start_dt_2)

        kwargs = {'fan': fan, 'start_dt': start_dt_1, 'end_dt': start_dt_2 + datetime.timedelta(hours=8)}
        Availabilities.availabilities.create(**kwargs)

        _ = Attendance.attendances.create(fan=fan, screening=screening_1)

        # Act.
        response = self.client.get(reverse('screenings:details', args=[screening_2.pk]))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 2)
        self.assert_screening_status(response, Screening.ScreeningStatus.ATTENDS_FILM, view='details')

    def test_details(self):
        """
        Details in the details view correspond with the screening.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-31 11:30')
        screening = self.arrange_create_screening(self.screen_b, start_dt)
        film = screening.film

        _ = Attendance.attendances.create(fan=fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:details', args=[screening.pk]))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assertContains(response, f'<li>Screen: {screening.screen}</li>')
        self.assertContains(response, f'<li>Time: Sat 31 Aug 11:30 - 13:24</li>')
        film_list_item = f'<li>Film details: <a href="/films/{film.pk}/details/">{film.title} details</a></li>'
        self.assertContains(response, film_list_item)
        self.assertContains(response, '<li>Film description: None</li>')


class PlannerViewTests(ScreeningViewsTests):
    def setUp(self):
        super().setUp()

        film_kwargs = {
            'festival': self.festival,
            'film_id': 8,
            'seq_nr': 16,
            'sort_title': 'portraits in life and death',
            'title': 'Portraits in Life and Death',
            'duration': datetime.timedelta(minutes=MAX_SHORT_MINUTES + 1),
            'medium_category': 'events',
            'url': 'https://edition.cnn.com/2024/04/18/style/venice-biennale-2024-what-to-see/index.html'
        }
        self.film_2 = Film.films.create(**film_kwargs)

    @staticmethod
    def arrange_get_film_rating(film, fan, rating):
        kwargs = {
            'film': film,
            'film_fan': fan,
            'rating': rating,
        }
        film_rating = FilmFanFilmRating.film_ratings.create(**kwargs)
        return film_rating

    @staticmethod
    def arrange_get_screening_kwargs(film, screen, start_dt):
        screening_kwargs = {
            'film': film,
            'screen': screen,
            'start_dt': start_dt,
        }
        return screening_kwargs

    def arrange_good_and_bad_screening(self, fan, set_availability=False):
        good_rating = LOWEST_PLANNABLE_RATING
        start_dt_good = arrange_get_datetime('2024-02-08 11:30')
        self.good_film = self.film
        self.good_film_rating = self.arrange_get_film_rating(self.good_film, fan, good_rating)
        self.good_screening_kwargs = self.arrange_get_screening_kwargs(self.good_film, self.screen_b, start_dt_good)
        self.good_screening = self.arrange_create_screening(**self.good_screening_kwargs)

        bad_rating = LOWEST_PLANNABLE_RATING - 1
        start_dt_bad = arrange_get_datetime('2024-02-08 23:14')
        self.bad_film = self.film_2
        self.bad_rating = self.arrange_get_film_rating(self.bad_film, fan, bad_rating)
        self.bad_screening_kwargs = self.arrange_get_screening_kwargs(self.bad_film, self.screen_sg, start_dt_bad)
        self.bad_screening = self.arrange_create_screening(**self.bad_screening_kwargs)

        if set_availability:
            start_dt = arrange_get_datetime('2024-02-08 09:30')
            end_dt = arrange_get_datetime('2024-02-09 21:00')
            Availabilities.availabilities.create(fan=fan, start_dt=start_dt, end_dt=end_dt)

    def test_only_eligible_rating_can_be_planned(self):
        """
        A screening of a film with eligible rating will be listed in the Planner View.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()
        self.arrange_good_and_bad_screening(fan)

        # Act.
        response = self.client.get(reverse('screenings:planner'))

        # Assert.
        self.assertGreaterEqual(self.good_film_rating.rating, LOWEST_PLANNABLE_RATING)
        self.assertLess(self.bad_rating.rating, LOWEST_PLANNABLE_RATING)
        self.assertEqual(Screening.screenings.count(), 2)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.good_film.title)
        self.assertNotContains(response, self.bad_film.title)

    def test_only_eligible_rating_is_planned(self):
        """
        A screening will be marked as auto-planned when planned.
        """
        # Arrange.
        fan = self.arrange_regular_user_props()
        self.arrange_good_and_bad_screening(fan, set_availability=True)

        get_response = self.client.get(reverse('screenings:planner'))

        # Act.
        post_data = {'plan': ['Plan screenings']}
        post_response = self.client.post(reverse('screenings:planner'), data=post_data)
        self.good_screening = Screening.screenings.get(**self.good_screening_kwargs)
        self.bad_screening = Screening.screenings.get(**self.bad_screening_kwargs)

        # Assert.
        self.assertGreaterEqual(self.good_film_rating.rating, LOWEST_PLANNABLE_RATING)
        self.assertLess(self.bad_rating.rating, LOWEST_PLANNABLE_RATING)
        self.assertEqual(Screening.screenings.count(), 2)
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        redirect_response = self.client.get(post_response.url)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.filter(auto_planned=True).count(), 1)
        self.assertFalse(self.bad_screening.auto_planned)
        self.assertTrue(self.good_screening.auto_planned)
