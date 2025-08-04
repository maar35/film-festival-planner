import datetime
import re
from http import HTTPStatus

from django.db import IntegrityError
from django.test import TestCase
from django.urls import reverse

from authentication.models import FilmFan
from availabilities.models import Availabilities
from availabilities.views import DAY_START_TIME
from festival_planner import debug_tools
from festival_planner.screening_status_getter import ScreeningWarning, ScreeningStatusGetter
from festivals.models import FestivalBase, Festival, switch_festival, current_festival
from films.models import Film, FAN_NAMES_BY_FESTIVAL_BASE, LOWEST_PLANNABLE_RATING, FilmFanFilmRating, set_current_fan
from films.tests import create_film, ViewsTestCase, get_decoded_content
from films.views import MAX_SHORT_MINUTES
from screenings.models import Screening, Attendance, Ticket
from sections.models import Section, Subsection
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

    def _arrange_screening_kwargs(self, iso_dt=None, minutes=None):
        start_dt = arrange_get_datetime(iso_dt or '2024-02-10 23:14')
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

    def test_unique_constraint(self):
        """t
        Screenings can not have the same film, screen and start time.
        """
        # Arrange.
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2022-10-31 20:00')
        start_dt = screening_kwargs['start_dt']
        end_dt_1 = start_dt + datetime.timedelta(minutes=101)
        end_dt_2 = start_dt + datetime.timedelta(minutes=21)

        screening_kwargs['end_dt'] = end_dt_1
        screening_1 = Screening(**screening_kwargs)
        screening_kwargs['end_dt'] = end_dt_2
        screening_2 = Screening(**screening_kwargs)

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

    def test_short_string_leading_zero(self):
        # Arrange.
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2024-02-06 21:00')
        screening = Screening.screenings.create(**screening_kwargs)

        # Act.
        string = screening.str_short()

        # Assert.
        self.assertRegex(string, r'Tue 6 Feb')

    def test_short_string_decimal_zero(self):
        # Arrange.
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2021-11-30 22:30')
        screening = Screening.screenings.create(**screening_kwargs)

        # Act.
        string = screening.str_short()

        # Assert.
        self.assertRegex(string, r'Tue 30 Nov')


class AttendanceModelTests(ScreeningModelTests):

    def setUp(self):
        super().setUp()

    def test_unique_constraint(self):
        """
        Attendances can not have the same fan and screening.
        """
        # Arrange.
        fan = FilmFan.film_fans.create(name='Neil', seq_nr=1)
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2022-10-31 20:00')
        screening = Screening(**screening_kwargs)
        attendance_1 = Attendance(fan=fan, screening=screening)
        attendance_2 = Attendance(fan=fan, screening=screening)

        # Act.
        screening.save()
        attendance_1.save()

        # Assert.
        self.assertRaises(IntegrityError, attendance_2.save)

    def test_attendance_string_contains_fan(self):
        # Arrange.
        jim = FilmFan.film_fans.create(name='Jim', seq_nr=1)
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2024-02-06 21:00')
        screening = Screening.screenings.create(**screening_kwargs)
        attendance = Attendance(fan=jim, screening=screening)

        # Act.
        string = str(attendance)

        # Assert.
        self.assertRegex(string, f'{jim} attends')


class TicketModelTests(ScreeningModelTests):
    def setUp(self):
        super().setUp()

    def test_unique_constraint(self):
        """
        Tickets can not have the same fan and screening.
        """
        # Arrange.
        fan = FilmFan.film_fans.create(name='Eric', seq_nr=1)
        screening_kwargs = self._arrange_screening_kwargs(iso_dt='2025-03-29 16:15')
        screening = Screening(**screening_kwargs)
        ticket_1 = Ticket(fan=fan, screening=screening, confirmed=False)
        ticket_2 = Ticket(fan=fan, screening=screening, confirmed=True)

        # Act.
        screening.save()
        ticket_1.save()

        # Assert.
        self.assertRaises(IntegrityError, ticket_2.save)


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

        theater_kwargs = {
            'theater_id': 2,
            'city': city,
            'parse_name': 'PalaBiennale',
            'abbreviation': 'palabi',
            'priority': Theater.Priority.HIGH,
        }
        theater_2 = Theater.theaters.create(**theater_kwargs)

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

        screen_kwargs = {
            'screen_id': 3,
            'theater': theater,
            'parse_name': 'Sala Perla',
            'abbreviation': '-sp',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen_sp = Screen.screens.create(**screen_kwargs)

        screen_kwargs = {
            'screen_id': 4,
            'theater': theater_2,
            'parse_name': 'PalaBiennale',
            'abbreviation': '-pb',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen_pb = Screen.screens.create(**screen_kwargs)

        screen_kwargs = {
            'screen_id': 5,
            'theater': theater_2,
            'parse_name': 'Sala Corinto',
            'abbreviation': '-sc',
            'address_type': Screen.ScreenAddressType.PHYSICAL,
        }
        self.screen_sc = Screen.screens.create(**screen_kwargs)

    def arrange_regular_user_props(self):
        self.fan = self.regular_fan
        logged_in = self.login(self.regular_credentials)
        self.assertIs(logged_in, True)

        request = self.get_regular_fan_request()
        set_current_fan(request)
        self.session = request.session

        switch_festival(self.session, self.festival)
        FAN_NAMES_BY_FESTIVAL_BASE[self.festival.base.mnemonic] = [self.fan.name]

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

    def arrange_create_std_screening(self):
        start_dt = arrange_get_datetime('2024-08-30 11:15')
        screening = self.arrange_create_screening(self.screen_sg, start_dt)
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
    def setUp(self):
        super().setUp()
        self.re_warning = r'<span[^>]*>!</span>'

    def test_screening_in_day_schema(self):
        """
        A screening is found in the day schema of its start date.
        """
        # Arrange.
        self.arrange_regular_user_props()
        screening = self.arrange_create_std_screening()

        Availabilities.availabilities.create(
            fan=self.fan,
            start_dt=screening.start_dt,
            end_dt=screening.start_dt + datetime.timedelta(hours=8),
        )

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.FREE)

    def test_screening_with_uninteresting_rating_has_dull_color(self):
        """
        An uninteresting rating is displayed in grey on its screening in the day schema.
        """
        # Arrange.
        self.arrange_regular_user_props()
        film_rating = FilmFanFilmRating.film_ratings.create(
            film=self.film,
            film_fan=self.fan,
            rating=FilmFanFilmRating.Rating.MEDIOCRE,
        )
        dull_color = Screening.uninteresting_rating_color
        _ = self.arrange_create_std_screening()

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'"color: {dull_color}">{film_rating.rating}<')
        self.assertLess(film_rating.rating, LOWEST_PLANNABLE_RATING)

    def test_film_section_is_indicated(self):
        """
        The subsection of the film of a screening is indicated in the day schema by its color.
        """
        # Arrange.
        self.arrange_regular_user_props()
        section_color = 'chartreuse'
        section = Section.sections.create(
            festival=self.festival,
            section_id=27,
            name='Onda olandese',
            color=section_color,
        )
        subsection = Subsection.subsections.create(
            subsection_id=1,
            section=section,
            name='Film per bambini',
            description='These films always have a young child as the main character.',
            url='https://en.wikipedia.org/wiki/National_pavilions_at_the_Venice_Biennale',
        )
        self.film.subsection = subsection
        self.film.save()
        _ = self.arrange_create_std_screening()

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f'border-right: 1px solid {section_color};')

    def test_attendance(self):
        """
        A screening attended by a fan with a ticket is correctly displayed in the day schema.
        """
        # Arrange.
        self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-31 11:30')
        screening = self.arrange_create_screening(self.screen_b, start_dt)

        _ = Attendance.attendances.create(fan=self.fan, screening=screening)
        _ = Ticket.tickets.create(fan=self.fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.ATTENDS)
        self.assertNotRegex(get_decoded_content(response), self.re_warning)

    def test_needs_ticket(self):
        """
        A screening attended by a fan without a ticket is correctly displayed in the day schema.
        """
        # Arrange.
        self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-31 11:30')
        screening = self.arrange_create_screening(self.screen_b, start_dt)

        _ = Attendance.attendances.create(fan=self.fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.NEEDS_TICKETS)
        self.assertRegex(get_decoded_content(response), self.re_warning)

    def test_warning_ticket_while_not_attending(self):
        """
        In the Day Schema, a warning symbol is displayed if a fan has a ticket for a screening but doesn't attend it.
        """
        # Arrange.
        self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-31 11:30')
        screening = self.arrange_create_screening(self.screen_b, start_dt)

        _ = Ticket.tickets.create(fan=self.fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:day_schema'))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assertRegex(get_decoded_content(response), self.re_warning)


class DetailsViewTest(ScreeningViewsTests):
    def test_attendance(self):
        """
        A screening attended by a fan with a ticket is correctly displayed in the screening details view.
        """
        # Arrange.
        self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-30 11:15')
        screening = self.arrange_create_screening(self.screen_sg, start_dt)

        _ = Attendance.attendances.create(fan=self.fan, screening=screening)
        _ = Ticket.tickets.create(fan=self.fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:details', args=[screening.pk]))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.ATTENDS, view='details')

    def test_needs_ticket(self):
        """
        A screening attended by a fan without a ticket is correctly displayed in the screening details view.
        """
        # Arrange.
        self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-30 11:15')
        screening = self.arrange_create_screening(self.screen_sg, start_dt)

        _ = Attendance.attendances.create(fan=self.fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:details', args=[screening.pk]))

        # Assert.
        self.assertEqual(current_festival(self.session), self.festival)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.count(), 1)
        self.assert_screening_status(response, Screening.ScreeningStatus.NEEDS_TICKETS, view='details')

    def test_attends_film(self):
        """
        If a screening is attended, other screenings of the same film are marked 'attends film'.
        """
        # Arrange.
        self.arrange_regular_user_props()

        start_dt_1 = arrange_get_datetime('2024-08-30 11:15')
        screening_1 = self.arrange_create_screening(self.screen_sg, start_dt_1)
        start_dt_2 = arrange_get_datetime('2024-08-31 11:30')
        screening_2 = self.arrange_create_screening(self.screen_b, start_dt_2)

        kwargs = {'fan': self.fan, 'start_dt': start_dt_1, 'end_dt': start_dt_2 + datetime.timedelta(hours=8)}
        Availabilities.availabilities.create(**kwargs)

        _ = Attendance.attendances.create(fan=self.fan, screening=screening_1)

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
        self.arrange_regular_user_props()

        start_dt = arrange_get_datetime('2024-08-31 11:30')
        screening = self.arrange_create_screening(self.screen_b, start_dt)
        film = screening.film

        _ = Attendance.attendances.create(fan=self.fan, screening=screening)

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
        re_description = r'<li>Film description:\s+-\s*</li>'
        self.assertRegex(get_decoded_content(response), re_description)


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
        self.arrange_regular_user_props()
        self.arrange_good_and_bad_screening(self.fan)

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
        self.arrange_regular_user_props()
        self.arrange_good_and_bad_screening(self.fan, set_availability=True)
        get_response = self.client.get(reverse('screenings:planner'))
        post_data = {'plan': ['Plan screenings']}

        # Act.
        post_response = self.client.post(reverse('screenings:planner'), data=post_data)

        # Assert.
        self.assertGreaterEqual(self.good_film_rating.rating, LOWEST_PLANNABLE_RATING)
        self.assertLess(self.bad_rating.rating, LOWEST_PLANNABLE_RATING)
        self.assertEqual(Screening.screenings.count(), 2)
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        redirect_response = self.client.get(post_response.url)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertEqual(Screening.screenings.filter(auto_planned=True).count(), 1)
        self.good_screening = Screening.screenings.get(**self.good_screening_kwargs)
        self.bad_screening = Screening.screenings.get(**self.bad_screening_kwargs)
        self.assertFalse(self.bad_screening.auto_planned)
        self.assertTrue(self.good_screening.auto_planned)


class WarningsViewTests(ScreeningViewsTests):
    re_warning_count = re.compile(
        r'<div class="[^"]*\bfloating-warning-box\b[^"]*"[^>]*>\s*<a[^>]*>\s*(\d+)\s*warnings</a>'
    )
    re_fan_warning = re.compile(r'<td>\s*(\w+)\s*</td>\s*<td[^>]*>([\w ]+)</td>')
    re_dropdown = re.compile(
        r'(<div class="sticky-modest-drop-t-head-content".*?Select ([\w ]+).*?</div>)',
        re.DOTALL
    )
    re_enabled = re.compile(r'<a href="[^"]+">\s*([\w ]+)\s*</a>')
    re_disabled = re.compile(r'<td>\s*<span class="[^"]*\bno-select\b[^"]*"[^>]*>\s*([\w ]+)\s*</span>')

    def setUp(self):
        super().setUp()
        film_kwargs = {
            'festival': self.festival,
            'film_id': 16,
            'seq_nr': 32,
            'sort_title': 'dark globe',
            'title': 'Dark Globe',
            'duration': datetime.timedelta(minutes=4),
            'medium_category': 'events',
            'url': 'https://www.sicvenezia.it/en/films/dark-globe/',
        }
        self.film_2 = Film.films.create(**film_kwargs)

        film_kwargs = {
            'festival': self.festival,
            'film_id': 17,
            'seq_nr': 37,
            'sort_title': 'blood and sand',
            'title': 'Blood and Sand',
            'duration': datetime.timedelta(minutes=125),
            'medium_category': 'films',
            'url': 'https://www.labiennale.org/en/cinema/2024/venice-classics/blood-and-sand',
        }
        self.film_3 = Film.films.create(**film_kwargs)

        film_kwargs = {
            'festival': self.festival,
            'film_id': 18,
            'seq_nr': 16,
            'sort_title': 'no sleep till',
            'title': 'No Sleep Till',
            'duration': datetime.timedelta(minutes=93),
            'medium_category': 'films',
            'url': 'https://www.sicvenezia.it/en/films/no-sleep-till/',
        }
        self.film_4 = Film.films.create(**film_kwargs)

    def _get_dropdown_content(self, _content, header):
        dropdown_groups = self.re_dropdown.findall(_content)
        dropdown_contents = [g[0] for g in dropdown_groups if g[1] == header]
        dropdown_content = dropdown_contents[0] if dropdown_contents else None
        return dropdown_content

    @staticmethod
    def _arrange_availability(fan, screenings):
        dates = {screening.start_dt.date() for screening in screenings}
        for availability_date in dates:
            availability_kwargs = {
                'fan': fan,
                'start_dt': datetime.datetime.combine(availability_date, DAY_START_TIME),
                'end_dt': datetime.datetime.combine(availability_date, datetime.time(hour=23)),
            }
            Availabilities.availabilities.create(**availability_kwargs)

    def _assert_enabled(self, _content, header, choices):
        dropdown_content = self._get_dropdown_content(_content, header)
        matches = set(self.re_enabled.findall(dropdown_content))
        self.assertEqual(matches, set(choices))

    def _assert_disabled(self, _content, header, choices):
        dropdown_content = self._get_dropdown_content(_content, header)
        matches = set(self.re_disabled.findall(dropdown_content))
        self.assertEqual(matches, set(choices))

    def _assert_warning_count(self, content, warning_count):
        m = self.re_warning_count.search(content)
        warnings = m.group(1) if m else '0'
        self.assertEqual(int(warnings), warning_count)

    def _assert_fan_warnings(self, content, fans, warning_types):
        fan_warnings = set()
        for fan in fans:
            for warning_type in warning_types:
                fan_warnings.add((fan.name, ScreeningWarning.wording_by_warning[warning_type]))
        matches = set(self.re_fan_warning.findall(content))
        self.assertEqual(fan_warnings, matches)

    def test_attendance_without_ticket(self):
        """
        Attendance without ticket is displayed in the Warnings view.
        """
        # Arrange.
        self.arrange_regular_user_props()
        screening = self.arrange_create_std_screening()
        _ = Attendance.attendances.create(fan=self.fan, screening=screening)

        # Act.
        response = self.client.get(reverse('screenings:warnings'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        displayed_warning_types = [
            ScreeningWarning.WarningType.NEEDS_TICKET,
            ScreeningWarning.WarningType.ATTENDS_WHILE_UNAVAILABLE,
        ]
        for warning_type in displayed_warning_types:
            self.assertContains(response, self.fan.name)
            self.assertContains(response, ScreeningWarning.wording_by_warning[warning_type])
            self.assertContains(response, ScreeningWarning.symbol_by_warning[warning_type])
            self.assertContains(response, ScreeningWarning.fix_by_warning[warning_type])

    def test_row_colors(self):
        """
        In each row, the warning wording has the designated color,
        and the warning symbol has the background color associated with the screening status.
        """
        def _get_coloring_regex():
            attendants = status_getter.get_attendants(screening)
            status = status_getter.get_screening_status(screening, attendants)
            symbol_background = Screening.color_pair_by_screening_status[status]['background']
            wording_color = ScreeningWarning.color_by_warning[warning_type]
            re_wording_color = wording_color.replace('(', r'\(').replace(')', r'\)')
            re_symbol_background = symbol_background.replace('(', r'\(').replace(')', r'\)')
            re_symbol = symbol.replace('?', r'\?')
            re_coloring = ((f'{self.fan.name}' + r'\s*</td>\s*<td[^>]*color:\s'
                            + re_wording_color + r'[^>]*>' + f'{wording}' + r'</td>\s*<td[^>]*background:\s')
                           + re_symbol_background + r'[^>]*>') + r'(\s*<[^/][^>]*>\s*)+' + re_symbol
            return re_coloring

        # Arrange.
        self.arrange_regular_user_props()
        screening = self.arrange_create_std_screening()
        status_getter = ScreeningStatusGetter(self.session, [screening])
        kwargs = {'fan': self.fan, 'screening': screening}
        _ = Attendance.attendances.create(**kwargs)
        _ = Ticket.tickets.create(**kwargs)

        # Act.
        response = self.client.get(reverse('screenings:warnings'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        displayed_warning_types = [
            ScreeningWarning.WarningType.AWAITS_CONFIRMATION,
            ScreeningWarning.WarningType.ATTENDS_WHILE_UNAVAILABLE,
        ]
        for warning_type in displayed_warning_types:
            wording = ScreeningWarning.wording_by_warning[warning_type]
            symbol = ScreeningWarning.symbol_by_warning[warning_type]
            self.assertContains(response, self.fan.name)
            self.assertContains(response, wording)
            self.assertContains(response, symbol)
            self.assertContains(response, ScreeningWarning.fix_by_warning[warning_type])
            self.assertRegex(get_decoded_content(response), _get_coloring_regex())

    def test_greyed_out_choices(self):
        """
        The Warnings view can be filtered per screening by fan.
        """
        # Arrange.
        self.arrange_regular_user_props()
        ozzy = FilmFan.film_fans.create(name='Ozzy', seq_nr=2)
        neil = FilmFan.film_fans.create(name='Neil', seq_nr=3)
        screening = self.arrange_create_std_screening()

        kwargs_list = [{'fan': fan, 'screening': screening} for fan in [neil, ozzy]]
        for kwargs in kwargs_list:
            _ = Attendance.attendances.create(**kwargs)

        displayed_warning_types = [
            ScreeningWarning.WarningType.NEEDS_TICKET,
            ScreeningWarning.WarningType.ATTENDS_WHILE_UNAVAILABLE,
        ]
        enabled_wordings = [ScreeningWarning.wording_by_warning[w] for w in displayed_warning_types]
        disabled_warning_types = set(ScreeningWarning.WarningType) - set(displayed_warning_types)
        disabled_wordings = [ScreeningWarning.wording_by_warning[w] for w in disabled_warning_types]

        # Act.
        response = self.client.get(reverse('screenings:warnings'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        content = get_decoded_content(response)
        self._assert_enabled(content, 'fan', [ozzy.name, neil.name])
        self._assert_disabled(content, 'fan', [self.fan.name, self.admin_fan.name])
        self._assert_enabled(content, 'warning', enabled_wordings)
        self._assert_disabled(content, 'warning', disabled_wordings)

    def test_buy_tickets(self):
        """
        When needing tickets, a popup menu lets you getting them.
        """
        # Arrange.
        self.arrange_regular_user_props()
        screening = self.arrange_create_std_screening()
        fans = [self.fan, self.admin_fan]

        kwargs_list = [{'fan': fan, 'screening': screening} for fan in fans]
        for kwargs in kwargs_list:
            _ = Attendance.attendances.create(**kwargs)

        warning_types_get = [
            ScreeningWarning.WarningType.NEEDS_TICKET,
            ScreeningWarning.WarningType.ATTENDS_WHILE_UNAVAILABLE,
        ]
        warning_types_redirect = [
            ScreeningWarning.WarningType.AWAITS_CONFIRMATION,
            ScreeningWarning.WarningType.ATTENDS_WHILE_UNAVAILABLE,
        ]

        get_response = self.client.get(reverse('screenings:warnings'))
        post_data = {'NEEDS_TICKET::1:': ['Buy ticket for all attendants']}

        # Act.
        post_response = self.client.post(reverse('screenings:warnings'), data=post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        get_content = get_decoded_content(get_response)
        redirect_content = get_decoded_content(redirect_response)
        self._assert_fan_warnings(get_content, fans, warning_types_get)
        self._assert_warning_count(get_content, 4)
        self._assert_fan_warnings(redirect_content, fans, warning_types_redirect)
        self._assert_warning_count(redirect_content, 4)

    def test_confirm_tickets(self):
        """
        When tickets need to be confirmed, a popup menu helps a fan to confirm all tickets.
        """
        # Arrange.
        self.arrange_regular_user_props()
        screening_1 = self.arrange_create_std_screening()
        start_dt_2 = arrange_get_datetime('2024-08-30 19:15')
        start_dt_3 = arrange_get_datetime('2024-09-02 14:15')
        screening_2 = self.arrange_create_screening(self.screen_sc, start_dt_2, film=self.film_2)
        screening_3 = self.arrange_create_screening(self.screen_sc, start_dt_3, film=self.film_3)
        screenings = [screening_1, screening_2, screening_3]
        eric = FilmFan.film_fans.create(name='Eric', seq_nr=4)

        kwargs_list = [{'fan': eric, 'screening': screening} for screening in screenings]
        for kwargs in kwargs_list:
            _ = Attendance.attendances.create(**kwargs)
            _ = Ticket.tickets.create(**kwargs)

        self._arrange_availability(eric, screenings)

        warning_types_get = [ScreeningWarning.WarningType.AWAITS_CONFIRMATION]
        warning_types_redirect = []

        get_response = self.client.get(reverse('screenings:warnings'))
        post_data = {'AWAITS_CONFIRMATION:Eric::': ['Confirm all tickets for Eric']}

        # Act.
        post_response = self.client.post(reverse('screenings:warnings'), data=post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        get_content = get_decoded_content(get_response)
        redirect_content = get_decoded_content(redirect_response)
        self._assert_fan_warnings(get_content, [eric], warning_types_get)
        self._assert_warning_count(get_content, 3)
        self._assert_fan_warnings(redirect_content, [eric], warning_types_redirect)
        self._assert_warning_count(redirect_content, 0)

    def test_fix_attends_overlapping_screenings(self):
        """
        When attending overlapping screenings, a popup menu allows you to unattend one.
        """
        # Arrange.
        self.arrange_regular_user_props()
        start_dt_3 = arrange_get_datetime('2024-09-02 14:15')
        start_dt_4 = arrange_get_datetime('2024-09-02 14:00')
        screening_3 = self.arrange_create_screening(self.screen_sc, start_dt_3, film=self.film_3)
        screening_4 = self.arrange_create_screening(self.screen_sc, start_dt_4, film=self.film_4)
        screenings = [screening_3, screening_4]

        kwargs_list = [{'fan': self.fan, 'screening': screening} for screening in screenings]
        for kwargs in kwargs_list:
            _ = Attendance.attendances.create(**kwargs)
            _ = Ticket.tickets.create(**kwargs)

        self._arrange_availability(self.fan, screenings)

        warning_types_get = [
            ScreeningWarning.WarningType.ATTENDS_OVERLAPPING,
            ScreeningWarning.WarningType.AWAITS_CONFIRMATION,
        ]
        warning_types_redirect = [
            ScreeningWarning.WarningType.SHOULD_SELL_TICKET,
            ScreeningWarning.WarningType.AWAITS_CONFIRMATION,
        ]
        fix_wording = ScreeningWarning.fix_by_warning[warning_types_get[0]]

        get_response = self.client.get(reverse('screenings:warnings'))
        post_data = {f'ATTENDS_OVERLAPPING:{self.fan.name}:{screening_4.id}:': [fix_wording]}

        # Act.
        post_response = self.client.post(reverse('screenings:warnings'), data=post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        get_content = get_decoded_content(get_response)
        redirect_content = get_decoded_content(redirect_response)
        self._assert_fan_warnings(get_content, [self.fan], warning_types_get)
        self._assert_warning_count(get_content, 4)
        self._assert_fan_warnings(redirect_content, [self.fan], warning_types_redirect)
        self._assert_warning_count(redirect_content, 2)

    def test_fix_attends_same_film(self):
        """
        When fans attend a film more than once, the fix popup menu helps them out.
        """
        # Arrange.
        self.arrange_regular_user_props()
        start_dt_1 = arrange_get_datetime('2024-08-30 20:00')
        start_dt_2 = arrange_get_datetime('2024-08-31 11:30')
        screening_1 = self.arrange_create_screening(self.screen_sg, start_dt_1, film=self.film)
        screening_2 = self.arrange_create_screening(self.screen_pb, start_dt_2, film=self.film)
        screenings = [screening_1, screening_2]
        fan = self.admin_fan

        kwargs_list = [{'fan': fan, 'screening': screening} for screening in screenings]
        for kwargs in kwargs_list:
            _ = Attendance.attendances.create(**kwargs)
            ticket = Ticket(confirmed=True, **kwargs)
            ticket.save()

        self._arrange_availability(fan, screenings)

        warning_types_get = [ScreeningWarning.WarningType.ATTENDS_SAME_FILM]
        warning_types_redirect = [ScreeningWarning.WarningType.SHOULD_SELL_TICKET]
        wording = ScreeningWarning.fix_by_warning[warning_types_get[0]]

        get_response = self.client.get(reverse('screenings:warnings'))
        post_data = {f'ATTENDS_SAME_FILM:{fan.name}::{screening_2.id}': [f'{wording} {screening_2.str_short()}']}

        # Act.
        post_response = self.client.post(reverse('screenings:warnings'), data=post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        get_content = get_decoded_content(get_response)
        redirect_content = get_decoded_content(redirect_response)
        self._assert_fan_warnings(get_content, [fan], warning_types_get)
        self._assert_warning_count(get_content, 2)
        self._assert_fan_warnings(redirect_content, [fan], warning_types_redirect)
        self._assert_warning_count(redirect_content, 1)
