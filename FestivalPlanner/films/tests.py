import re
from datetime import timedelta, date
from http import HTTPStatus
from importlib import import_module
from unittest import skip
from urllib.parse import urlparse, urlunparse

from django.conf import settings
from django.db import IntegrityError
from django.http import HttpRequest
from django.test import TestCase, Client
from django.urls import reverse

from authentication.models import me, FilmFan
from authentication.tests import set_up_user_with_fan
from festival_planner import debug_tools
from festival_planner.cache import FilmRatingCache
from festival_planner.cookie import Filter
from festivals.models import current_festival, FestivalBase, Festival
from festivals.tests import create_festival
from films import views, models
from films.forms.film_forms import PickRating
from films.models import Film, FilmFanFilmRating, get_rating_name, FilmFanFilmVote, UNRATED_STR
from films.views import FilmsView, FilmDetailView, MAX_SHORT_MINUTES, BaseFilmsFormView, FilmsListView
from loader.views import RatingDumperView
from sections.models import Subsection, Section
from theaters.models import City


def arrange_film_fans():
    _ = FilmFan.film_fans.create(name='john', seq_nr=1, is_admin=True)
    _ = FilmFan.film_fans.create(name='paul', seq_nr=4)
    _ = FilmFan.film_fans.create(name='jimi', seq_nr=3)
    _ = FilmFan.film_fans.create(name='frank', seq_nr=2)


def tear_down_film_fans():
    fans = FilmFan.film_fans.all()
    fans.delete()


def create_std_festival():
    """
    Create a new festival in the database.
    """
    city = City.cities.create(city_id=2, name='Cannes', country='fr')
    festival = create_festival('FdC', city, '2021-01-27', '2021-02-06')
    return festival


def new_std_festival():
    """
    Create a festival if it isn't already in the database.
    """
    # Create a city.
    city_kwargs = {'city_id': 14795, 'name': 'Patience', 'country': 'us'}
    (city, _) = City.cities.get_or_create(**city_kwargs)

    # Create a festival base.
    base_kwargs = {'mnemonic': 'PFF', 'name': 'Patience Film Festival', 'home_city': city}
    (festival_base, _) = FestivalBase.festival_bases.get_or_create(**base_kwargs)

    # Create a festival.
    start_date = date.fromisoformat('2021-04-02')
    end_date = date.fromisoformat('2024-04-03')
    festival_kwargs = {'base': festival_base, 'year': 2021, 'start_date': start_date,
                       'end_date': end_date}
    (festival, _) = Festival.festivals.get_or_create(**festival_kwargs)

    return festival


def create_film(film_id, title, minutes, seq_nr=-1, festival=None, sort_title=None, subsection=None):
    """
    Create a film with the given arguments in the database.
    """
    festival = festival or create_std_festival()
    duration = timedelta(minutes=minutes)
    sort_title = sort_title or title
    return Film.films.create(festival_id=festival.id, film_id=film_id, seq_nr=seq_nr,
                             title=title, duration=duration, subsection=subsection,
                             sort_title=sort_title.lower())


def new_film(film_id, title, minutes, seq_nr=-1, festival=None):
    """
    Create a film instance with the given arguments.
    """
    festival = festival or new_std_festival()
    duration = timedelta(minutes=minutes)
    film = Film(festival=festival, film_id=film_id, seq_nr=seq_nr, title=title, duration=duration,
                sort_title=title, title_language='en', medium_category='films',
                reviewer='kijA', url='https://pff.us/film/title-from-parameters/')
    return film


def get_session_with_fan(fan):
    session_store = import_module(settings.SESSION_ENGINE).SessionStore
    session = session_store()
    session['fan_name'] = fan.name
    session.create()
    return session


def get_request_with_session(request_with_session, method_is_post=False, post_data=None):
    request = HttpRequest()
    request.method = 'POST' if method_is_post else 'GET'
    request.user = request_with_session.user
    request.session = request_with_session.session
    request.POST = post_data
    return request


def get_decoded_content(response):
    return response.content.decode('utf-8')


class FilmModelTests(TestCase):
    def setUp(self):
        super().setUp()
        self.festival = new_std_festival()

    def tearDown(self):
        super().tearDown()

    def test_reviewer_can_be_created_blank(self):
        """
        The reviewer of a film shouldn't be a blank string,
        but unfortunately this is accepted.
        Fortunately reviewers are only fed into the database with the loader.
        See test loader.RatingLoaderViewsTests.test_reviewer_cannot_be_loaded_blank.
        """
        # Arrange.
        film = new_film(3319, 'The Renewables', 110)
        film.reviewer = ' '

        # Act.
        film.save()

        # Assert.
        film_count = Film.films.count()
        self.assertEqual(film_count, 1, 'There should be 1 film in the database')


class FilmFanModelTests(TestCase):
    def setUp(self):
        super().setUp()
        arrange_film_fans()

    def tearDown(self):
        super().tearDown()
        tear_down_film_fans()

    def test_film_fan_me_is_number_one(self):
        """
        me() always has sequence number 1.
        """
        # Arrange.
        fan_number_one = FilmFan.film_fans.get(seq_nr=1)

        # Act.
        fan = me()

        # Assert.
        self.assertIs(fan.seq_nr, fan_number_one.seq_nr)

    def test_film_fan_me_has_lowest_sequence_number(self):
        """
        me() always has the lowest sequence number from all fans.
        """
        # Arrange.
        first_fan = FilmFan.film_fans.order_by('seq_nr')[0]

        # Act.
        maarten = me()

        # Assert.
        self.assertEqual(maarten, first_fan)


class BaseJudgementModelTests(TestCase):
    def setUp(self) -> None:
        super().setUp()
        arrange_film_fans()
        self.city = City.cities.create(city_id=1, name='Gent', country='be')

    def tearDown(self) -> None:
        super().tearDown()
        tear_down_film_fans()
        self.city.delete()


class RatingModelTests(BaseJudgementModelTests):
    def test_rating_has_correct_meaning(self):
        """
        Rating 7 has meaning INDECISIVE.
        """
        # Arrange.
        rating_value = 7
        rating_meaning = 'Indecisive'
        festival = create_festival('IDFA', self.city, '2022-07-17', '2022-07-27')
        film = Film(festival_id=festival.id, film_id=-1, seq_nr=-1, title='A Test Movie',
                    duration=timedelta(minutes=666))
        film.save()
        fan = me()
        rating = FilmFanFilmRating(film=film, film_fan=fan, rating=rating_value)
        rating.save()

        # Act.
        rating_name = FilmFanFilmRating.Rating(rating.rating).label

        # Assert.
        self.assertEqual(rating_meaning, rating_name)

    def test_ratings_can_have_same_film_id_but_not_same_festival_id(self):
        """
        Two ratings can only have films with identical film_id if
        festivals are different.
        """
        # Arrange.
        fan = me()
        rating_value = 7
        festival_1 = create_festival('IDFA', self.city, '2021-07-17', '2021-07-27')
        festival_2 = create_festival('MTMF', self.city, '2022-04-17', '2022-04-27')
        film_1 = Film(festival_id=festival_1.id, film_id=1, seq_nr=1, title='Test Movie', duration=timedelta(minutes=6))
        film_2 = Film(festival_id=festival_2.id, film_id=1, seq_nr=1, title='Movie Two', duration=timedelta(minutes=77))
        film_1.save()
        film_2.save()
        rating_1 = FilmFanFilmRating(film=film_1, film_fan=fan, rating=rating_value)
        rating_2 = FilmFanFilmRating(film=film_2, film_fan=fan, rating=rating_value)
        rating_1.save()

        # Act.
        rating_2.save()

        # Assert.
        self.assertEqual(rating_1.film.film_id, rating_2.film.film_id)


class VoteModelTests(BaseJudgementModelTests):
    @staticmethod
    def arrange_get_vote_label(vote_value):
        return [label for value, label in FilmFanFilmVote.choices if value == vote_value][0]

    def test_vote_has_correct_meaning(self):
        """ Vote 3 has meaning VERY BAD. """
        # Arrange.
        vote_value = 3
        vote_meaning = 'Very Bad'
        festival = create_festival('Sundance', self.city, '2025-01-23', '2025-02-02')
        film = Film(festival_id=festival.id, film_id=-1, seq_nr=-1, title='American Duty',
                    duration=timedelta(minutes=90))
        film.save()
        fan = me()
        vote = FilmFanFilmVote(film=film, film_fan=fan, vote=vote_value)
        vote.save()

        # Act.
        vote_name = self.arrange_get_vote_label(vote_value)

        # Assert.
        self.assertEqual(vote_meaning, vote_name)

    def test_vote_has_no_special_meaning(self):
        """ Vote 2 doesn't exist """
        # Arrange.
        vote_value = 2  # rating meaning is special ('Will See')
        festival = create_festival('Imagine', self.city, '2024-01-24', '2024-11-03')
        film = Film(festival_id=festival.id, film_id=-1, seq_nr=-1, title='The Vampire Vanishes',
                    duration=timedelta(minutes=104))
        film.save()
        fan = me()
        vote = FilmFanFilmVote(film=film, film_fan=fan, vote=vote_value)
        vote.save()

        # Act and assert.
        self.assertRaises(IndexError, self.arrange_get_vote_label, vote_value)


class SectionModelTests(TestCase):

    def setUp(self):
        super().setUp()
        self.city = City.cities.create(city_id=1, name='Oslo', country='no')
        self.festival = create_festival('OFF', self.city, '2023-12-15', '2023-12-16')

    def test_subsection_can_be_created_from_code(self):
        """
        A Subsection object can be created in the database from code.
        """
        # Arrange.
        section = Section.sections.create(festival=self.festival, section_id=24, name='Shades',
                                          color='Grey')
        subsection = Subsection(subsection_id=13, section=section,
                                name='Direction Favorites', description='What we like best')
        # Act.
        subsection.save()

        # Assert.
        self.assertEqual(Subsection.subsections.count(), 1)
        self.assertEqual(Subsection.subsections.all()[0].name, subsection.name)

    def test_subsection_id_and_section_festival_not_unique_together(self):
        """
        Subsection fields subsection_id and section are unique together, independent of the (o
        """
        # Arrange.
        festival = create_festival('CPH:DOX', self.city, '2022-11-11', '2022-11-16')
        section = Section.sections.create(festival=festival, section_id=24, name='Shades',
                                          color='Grey')
        subsection_1 = Subsection(subsection_id=13, section=section,
                                  name='Direction Favorites', description='What we like best')
        subsection_2 = Subsection(subsection_id=13, section=section,
                                  name='Scout Favorites', description='Best found footage')
        # Act and Assert.
        subsection_1.save()
        with self.assertRaises(IntegrityError):
            subsection_2.save()

    def test_subsection_id_and_section_unique_together(self):
        """
        Subsection fields subsection_id and section are unique together
        """
        # Arrange.
        section = Section.sections.create(festival=self.festival, section_id=24, name='Shades',
                                          color='Grey')
        subsection_1 = Subsection(subsection_id=13, section=section,
                                  name='Direction Favorites', description='What we like best')
        subsection_2 = Subsection(subsection_id=13, section=section,
                                  name='Scout Favorites', description='Best found footage')

        # Act and Assert.
        subsection_1.save()
        with self.assertRaises(IntegrityError):
            subsection_2.save()

    def test_subsection_id_and_festival_not_unique_together(self):
        """
        Subsection fields subsection_id and festival are not unique together.
        """
        # Arrange.
        festival_2 = create_festival('CPH:DOX', self.city, '2022-11-11', '2022-11-16')
        section_1 = Section.sections.create(festival=self.festival, section_id=24, name='Shades',
                                            color='Grey')
        section_2 = Section.sections.create(festival=festival_2, section_id=24, name='Markets',
                                            color='Purple')
        subsection_1 = Subsection(subsection_id=13, section=section_1,
                                  name='Direction Favorites', description='What we like best')
        subsection_2 = Subsection(subsection_id=13, section=section_2,
                                  name='Scout Favorites', description='Best found footage')

        # Act.
        subsection_1.save()
        subsection_2.save()

        # Assert.
        self.assertEqual(Subsection.subsections.count(), 2)
        kwargs_1 = {'subsection_id': subsection_1.subsection_id, 'section': section_1}
        self.assertEqual(Subsection.subsections.get(**kwargs_1), subsection_1)
        kwargs_2 = {'subsection_id': subsection_2.subsection_id, 'section': section_2}
        self.assertEqual(Subsection.subsections.get(**kwargs_2), subsection_2)


class ViewsTestCase(TestCase):

    def setUp(self):
        super().setUp()
        debug_tools.SUPPRESS_DEBUG_PRINT = True
        self.client = Client()
        self.session = self.client.session

        # Set up an admin user.
        self.admin_fan, self.admin_user, self.admin_credentials = \
            set_up_user_with_fan('john', 'war=over', seq_nr=1, is_admin=True)

        # Set up a regular user.
        self.regular_fan, self.regular_user, self.regular_credentials = \
            set_up_user_with_fan('paul', 'mull-kintyre', seq_nr=1942)

        # Cleanup the fans who appear in the rating views.
        models.FANS_IN_RATINGS_TABLE[0:] = []

    def tearDown(self):
        super().tearDown()
        _ = self.client.post(reverse('authentication:logout'))

    @staticmethod
    def invalidate_cache(session):
        festival = current_festival(session)
        if not PickRating.film_rating_cache:
            PickRating.film_rating_cache = FilmRatingCache(session, FilmsView.unexpected_errors)
        PickRating.film_rating_cache.invalidate_festival_caches(festival)
        FilmRatingCache.set_filters(session, {})

    def login(self, credentials):
        return self.client.login(
            username=credentials['username'],
            password=credentials['password']
        )

    def arrange_switch_fan(self, fan):
        fan_post_data = {'selected_fan': [fan.name]}
        fan_response = self.client.post(reverse('films:film_fan'), data=fan_post_data)
        self.assertEqual(fan_response.status_code, HTTPStatus.FOUND)
        return fan_response

    def get_request(self, fan, user, credentials):
        logged_in = self.login(credentials)
        request = HttpRequest()
        request.user = user
        request.session = get_session_with_fan(fan)
        self.arrange_switch_fan(fan)
        self.invalidate_cache(request.session)
        self.assertIs(logged_in, True)
        return request

    def get_admin_request(self):
        request = self.get_request(self.admin_fan, self.admin_user, self.admin_credentials)
        self.assertIs(self.admin_fan.is_admin, True)
        return request

    def get_regular_fan_request(self):
        request = self.get_request(self.regular_fan, self.regular_user, self.regular_credentials)
        self.assertIs(self.regular_fan.is_admin, False)
        return request


class ResultsViewsTests(ViewsTestCase):

    def assert_fan_row(self, fan, rating_str, response, fan_is_current=True):
        if fan_is_current:
            fan_row_re_str = r'<td>\s*' + f'{fan.name}' + r'\s*</td>\s*'\
                             + r'<td[^>]*>\s*<span[^>]*>\s*'\
                             + f'{rating_str}' + r'\s*</span>'
        else:
            fan_row_re_str = r'<td>\s*' + f'{fan.name}' + r'\s*</td>\s*'\
                             + r'<td[^>]*>\s*' + f'{rating_str}' + r'\s*</td>'
        fan_row_re = re.compile(fan_row_re_str, re.DOTALL)
        self.assertRegex(get_decoded_content(response), fan_row_re)

    def test_results_of_hacked_film_without_login(self):
        """
        The results view with a hacked film id redirects to login page.
        when not logged in.
        """
        # Arrange.
        self.client.logout()
        hacked_film = new_film(film_id=5000, title='Future Question', minutes=95)
        fake_pk = 2000

        # Act.
        get_response = self.client.get(reverse('films:details', args=[fake_pk]))
        redirect_response = self.client.get(get_response.url)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertContains(redirect_response, 'Application Login')
        self.assertContains(redirect_response, 'Access Denied')

    def test_results_of_hacked_film_logged_in(self):
        """
        The results view with a hacked film id returns a 404 not found.
        """
        # Arrange.
        hacked_film = new_film(film_id=5001, title='Futuristic Quests', minutes=96)
        fake_pk = hacked_film.film_id
        _ = self.get_regular_fan_request()

        # Act.
        get_response = self.client.get(reverse('films:details', args=[fake_pk]))

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.NOT_FOUND)

    def test_rating_of_created_film_without_login(self):
        """
        The results view with film id of a film that was newly added to
        the database forbids to view the ratings of the given film
        when not logged in.
        """
        # Arrange.
        saved_film = create_film(film_id=6000, title='New Adventure', minutes=114)
        url = reverse('films:details', args=[saved_film.pk])
        PickRating.film_rating_cache = FilmRatingCache(self.client.session, FilmsView.unexpected_errors)

        # Act.
        response = self.client.get(url)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        with self.assertRaisesRegex(AssertionError, r"^302 != 200 : Couldn't retrieve content"):
            self.assertContains(response, saved_film.title)

    def test_created_film_unrated_logged_in(self):
        """
        The results view with film id of a film that was newly added to
        the database displays no ratings for the given film.
        """
        # Arrange.
        fan = self.regular_fan
        _ = self.get_regular_fan_request()
        saved_film = create_film(film_id=6001, title='New Adventures', minutes=115)
        models.FANS_IN_RATINGS_TABLE.append(self.regular_fan.name)

        # Act.
        get_response = self.client.get(reverse('films:details', args=[saved_film.pk]))

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, saved_film.title)
        self.assert_fan_row(fan, UNRATED_STR, get_response)

    def test_rating_of_created_film_logged_in(self):
        """
        The results view with film id of a film that was newly added to
        the database displays the ratings of the given film.
        """
        # Arrange.
        fan = self.regular_fan
        _ = self.get_regular_fan_request()

        saved_film = create_film(film_id=6002, title='A Few More Adventures', minutes=116)
        rating_value = 8
        FilmFanFilmRating.film_ratings.create(film=saved_film, film_fan=fan, rating=rating_value)
        models.FANS_IN_RATINGS_TABLE.append(self.regular_fan.name)
        models.FANS_IN_RATINGS_TABLE.append(self.admin_fan.name)

        # Act.
        get_response = self.client.get(reverse('films:details', args=[saved_film.pk]))

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, saved_film.title)
        self.assert_fan_row(fan, str(rating_value), get_response)
        self.assert_fan_row(self.admin_fan, UNRATED_STR, get_response, fan_is_current=False)

    def test_admin_can_vote_on_behalf_of_a_different_film_fan(self):
        """
        An admin fan can rate films on behalf of another film fan.
        """
        # Arrange.
        saved_film = create_film(film_id=5100, title='Rate Me, Rate Me!', minutes=17)
        fan = FilmFan.film_fans.get(name='Paul')
        _ = self.get_admin_request()
        post_data = {'selected_fan': [fan.name]}
        fan_response = self.client.post(reverse('films:film_fan'), data=post_data)
        films_response = self.client.get(reverse('films:films'))    # Initialize cache.

        # Act.
        get_response = self.client.get(reverse('films:details', args=[saved_film.pk]))

        # Assert.
        self.assertEqual(films_response.status_code, HTTPStatus.OK)
        self.assertEqual(fan_response.status_code, HTTPStatus.FOUND)
        self.assertIs(self.regular_fan.is_admin, False)
        self.assertIs(self.admin_fan.is_admin, True)
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, f"{self.admin_credentials['username']} represents")
        self.assertContains(get_response, self.regular_fan.name)

    @skip("Unexpected HTTP status 405 method not allowed, to be fixed")
    def test_logged_in_fan_can_remove_rating_in_detail_view(self):
        """ TODO fix unexpected 405
        A logged in fan can remove a rating from the film detail view.
        """
        # Arrange.
        does_not_exist_msg = 'FilmFanFilmRating matching query does not exist'
        _ = self.get_regular_fan_request()
        fan = self.regular_fan

        film = create_film(film_id=1999, title='The Prince and the Price', minutes=98)
        rating_value = 6
        new_rating_value = 0
        FilmFanFilmRating.film_ratings.create(film=film, film_fan=fan, rating=rating_value)
        rating = FilmFanFilmRating.film_ratings.get(film=film, film_fan=fan)
        self.assertEqual(rating.rating, rating_value)

        post_data = {'fan_rating': [f'{FilmDetailView.submit_name_prefix}{film.film_id}_{new_rating_value}']}

        # Act.
        post_response = self.client.post(reverse('films:details', args=[film.pk]), data=post_data)

        # Assert.
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND, f'Unexpected POST response of {FilmDetailView.__name__}')
        self.assertURLEqual(post_response.url, reverse('films:details', args=[film.id]))
        self.assertContains(post_response, self.regular_fan.name)
        self.assertContains(post_response, self.admin_fan.name)
        self.assert_fan_row(fan, str(new_rating_value), post_response)
        self.assert_fan_row(self.admin_fan, UNRATED_STR, post_response, fan_is_current=False)


class FilmListViewsTests(ViewsTestCase):

    def setUp(self):
        super().setUp()
        self.city = City.cities.create(city_id=1, name='Berlin', country='de')

    def tearDown(self):
        super().tearDown()
        self.city.delete()

    @staticmethod
    def arrange_get_rating_post_data(film, rating_value=0):
        return {f'{FilmsView.submit_name_prefix}{film.id}_{rating_value}': ['label']}

    def arrange_filtered_view(self, filter_setter, setter_arg):
        request = self.get_regular_fan_request()
        request.method = 'GET'
        films_view = FilmsListView()
        session = request.session
        films_view.setup(request)
        filter_setter(session, films_view, setter_arg)
        films_view.dispatch(request)
        films_view.queryset = films_view.get_queryset()
        context = films_view.get_context_data()
        return films_view, context

    def assert_rating_action_redirect(self, user, get_response, post_response, redirect_response):
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, user.username)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assert_paths_equal(post_response.url, reverse('films:films'))
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)

    def assert_paths_equal(self, path1, path2):
        obj1 = urlparse(path1)
        obj2 = urlparse(path2)
        url1 = urlunparse(['', '', obj1.path, '', '', ''])
        url2 = urlunparse(['', '', obj2.path, '', '', ''])
        self.assertURLEqual(url1, url2)

    def test_hacked_film_in_film_list_logged_in(self):
        """
        The film ratings view doesn't display a hacked film.
        """
        # Arrange.
        city = City.cities.create(city_id=3, name='Gent', country='be')
        festival = create_festival('FFG', city, '2024-10-09', '2024-10-20')
        hacked_film = new_film(film_id=4242, title='The Negative Answer', minutes=84, festival=festival)
        saved_film = create_film(film_id=1122, title='The Good Answer', minutes=42, festival=festival)
        saved_film2 = create_film(film_id=4200, title='A Short Answer', minutes=10, festival=festival)
        _ = self.get_regular_fan_request()

        # Act.
        response = self.client.get(reverse('films:films'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, saved_film.title)
        self.assertContains(response, saved_film2.title)
        self.assertNotContains(response, hacked_film.title)

    def test_hacked_film_in_film_list_without_login(self):
        """
        The film ratings view redirects sessions from client without login.
        """
        # Arrange.
        hacked_film = new_film(film_id=4242, title='The Negative Answer', minutes=84)
        saved_film = create_film(film_id=1122, title='The Good Answer', minutes=42)

        # Act.
        response = self.client.get(reverse('films:films'))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)
        with self.assertRaisesRegex(AssertionError, r"^302 != 200 : Couldn't retrieve content"):
            self.assertContains(response, saved_film.title)
        with self.assertRaisesRegex(AssertionError, r"^302 != 200 : Couldn't retrieve content"):
            self.assertNotContains(response, hacked_film.title)

    def test_results_of_created_film(self):
        """
        The results view with film id of a film that was newly added to
        the database displays the details of the given film.
        """
        # Arrange.
        created_film = create_film(film_id=4422, title='The Wrong Answer', minutes=66)
        _ = self.get_regular_fan_request()
        _ = self.client.get(reverse('films:films'))    # Initialize cache.

        # Act.
        response = self.client.get(reverse('films:details', args=[created_film.pk]))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['film'], created_film)

    def test_login(self):
        """
        A test fan can log in.
        """
        # Arrange.
        pass

        # Act.
        logged_in = self.login(self.admin_credentials)

        # Assert.
        self.assertIs(logged_in, True)

    def test_admin_can_switch_to_a_different_film_fan(self):
        """
        An admin fan can switch to a different fan without logging in.
        """
        # Arrange.
        request = self.get_admin_request()

        # Act.
        response = views.film_fan(request)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Set current fan')

    def test_non_admin_cannot_switch_to_a_different_film_fan(self):
        """
        A non-admin fan cannot switch to another fan without logging
        in.
        """
        # Arrange.
        request = self.get_regular_fan_request()

        # Act.
        response = views.film_fan(request)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.regular_fan.name)
        self.assertContains(response, 'Only an admin fan can rate for other fans.')

    def test_logged_in_fan_can_add_rating(self):
        """
        A logged in fan can add a rating to a film.
        """
        # Arrange.
        festival = create_festival('NFF', self.city, '2024-07-11', '2024-07-20')
        film = create_film(film_id=2001, title='Odysseus in Trouble', minutes=128, festival=festival)
        rating_value = 9
        rating_name = get_rating_name(rating_value)

        _ = self.get_admin_request()
        fan = self.admin_fan

        post_data = self.arrange_get_rating_post_data(film, rating_value=rating_value)

        # Act.
        post_response = self.client.post(reverse('films:films'), data=post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        log_re = re.compile(f'{fan.name}' + r'\s+' + f'gave.*{film.title}.*rating of.* {rating_value}'
                            + r' \(' + f'{rating_name}' + r'\)')
        self.assertRegex(get_decoded_content(redirect_response), log_re)

    def test_logged_in_fan_can_change_rating(self):
        """
        A logged in fan can change an existing rating of a film.
        """
        # Arrange.
        film = create_film(film_id=1948, title='Big Brothers', minutes=110)
        fan = self.regular_fan
        old_rating_value = 8
        FilmFanFilmRating.film_ratings.create(film=film, film_fan=fan, rating=old_rating_value)
        new_rating_value = 3
        new_rating_name = get_rating_name(new_rating_value)

        client = Client()
        log_response = client.post(reverse('authentication:login'), self.regular_credentials)
        get_response = client.get(reverse('films:films'))
        get_request = self.get_regular_fan_request()
        post_data = self.arrange_get_rating_post_data(film, rating_value=new_rating_value)

        # Act.
        post_response = client.post(reverse('films:films'), data=post_data)
        redirect_response = client.get(post_response.url)

        # Assert.
        self.assertEqual(log_response.status_code, HTTPStatus.FOUND, f"Login of {self.regular_user} failed")
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assert_rating_action_redirect(get_request.user, get_response, post_response, redirect_response)
        log_re = re.compile(f'{fan.name}' + r'\s+'
                            + f'changed rating {old_rating_value} of.*{film.title}.*into.* {new_rating_value}'
                            + r' \(' + f'{new_rating_name}' + r'\)')
        self.assertRegex(get_decoded_content(redirect_response), log_re)

    def test_logged_in_fan_can_remove_rating(self):
        """
        A logged in fan can remove a rating from the film list view.
        """
        # Arrange.
        unexpected_post_status_msg = f'Unexpected POST response of {FilmDetailView.__name__}'
        _ = self.get_regular_fan_request()
        fan = self.regular_fan

        film = create_film(film_id=1999, title='The Prince and the Price', minutes=98)
        rating_value = 6
        new_rating_value = 0
        FilmFanFilmRating.film_ratings.create(film=film, film_fan=fan, rating=rating_value)
        rating = FilmFanFilmRating.film_ratings.get(film=film, film_fan=fan)

        post_data = self.arrange_get_rating_post_data(film, rating_value=new_rating_value)

        # Act.
        post_response = self.client.post(reverse('films:films'), data=post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(rating.rating, rating_value)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND, unexpected_post_status_msg)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertContains(redirect_response, self.regular_fan.name)
        current_fan_row_re = re.compile(f'{fan.name}' + r'\s+' + f'removed rating {rating_value} of.*{film.title}')
        self.assertRegex(get_decoded_content(redirect_response), current_fan_row_re)

    def test_non_admin_cannot_save_ratings(self):
        """
        A non-admin fan can't save ratings.
        """
        # Arrange.
        festival = create_festival('IDFA', self.city, '2023-11-19', '2023-11-28')
        get_request = self.get_regular_fan_request()
        save_view = RatingDumperView()
        save_view.object = festival
        save_view.setup(get_request)
        context = save_view.get_context_data()

        # Act.
        get_response = save_view.render_to_response(context)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, 'Not allowed')

    def test_admin_can_open_save_ratings_page(self):
        """
        A logged in admin fan has access to the save ratings page.
        """
        # Arrange.
        festival = create_festival('IDFA', self.city, '2023-11-19', '2023-11-28')
        get_request = self.get_admin_request()

        save_view = RatingDumperView()
        save_view.object = festival
        save_view.setup(get_request)
        context = save_view.get_context_data()

        # Act.
        get_response = save_view.render_to_response(context)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertNotContains(get_response, 'Not allowed')

    def test_filter_out_shorts(self):
        """
        Films with duration less than config['Constants']['MaxShortMinutes']
        can be filtered out.
        """
        # Arrange.
        festival = create_std_festival()
        feature_film = create_film(film_id=2700, title='The Flashlight Saga', minutes=80, festival=festival)
        short_film = create_film(film_id=27, title='Flashing Away', minutes=12, festival=festival)
        edge_film = create_film(film_id=270, title='Flashing Edgeward', minutes=MAX_SHORT_MINUTES, festival=festival)
        _ = self.get_regular_fan_request()
        shorts_filter = Filter('shorts')
        hide_shorts_query = f'?{shorts_filter.get_cookie_key()}={Filter.query_by_filtered[True]}'
        include_shorts_query = f'?{shorts_filter.get_cookie_key()}={Filter.query_by_filtered[False]}'

        # Act.
        include_shorts_response = self.client.get(reverse('films:films') + include_shorts_query)
        hide_shorts_response = self.client.get(reverse('films:films') + hide_shorts_query)

        # Assert.
        self.assertEqual(hide_shorts_response.status_code, HTTPStatus.OK)
        self.assertContains(include_shorts_response, feature_film.title)
        self.assertContains(include_shorts_response, short_film.title)
        self.assertContains(include_shorts_response, edge_film.title)

        self.assertContains(hide_shorts_response, feature_film.title)
        self.assertNotContains(hide_shorts_response, short_film.title)
        self.assertNotContains(hide_shorts_response, edge_film.title)

    def test_select_subsection(self):
        """
        Films can be filtered as to keep one subsection visible.
        """
        def set_subsection_filter(session, view, setter_arg):
            su_filter = view.subsection_filters[setter_arg]
            su_filter.set(session, not su_filter.get(session))

        # Arrange.
        festival = create_std_festival()
        section = Section.sections.create(festival=festival, section_id=24, name='Fighting', color='red')
        subsection_1 = Subsection.subsections.create(
            subsection_id=1, section=section, name='War movies', description='In these films, people fight in wars')
        subsection_2 = Subsection.subsections.create(
            subsection_id=2, section=section, name='Activism', description='About people who fight for piece')
        film_without_subsection = create_film(film_id=200, title='A Bear and a Forest', minutes=139, festival=festival)
        film_with_subsection_1 = create_film(film_id=201, title='War Chickens', minutes=86,
                                             subsection=subsection_1, festival=festival)
        film_with_subsection_2 = create_film(film_id=202, title='The Freemen', minutes=116,
                                             subsection=subsection_2, festival=festival)

        films_view, context = self.arrange_filtered_view(set_subsection_filter, subsection_1)

        # Act.
        get_response = films_view.render_to_response(context)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertNotContains(get_response, film_without_subsection.title)
        self.assertContains(get_response, film_with_subsection_1.title)
        self.assertNotContains(get_response, film_with_subsection_2.title)

    def test_select_section(self):
        """
        Films can be filtered as to keep one section visible.
        """
        def set_section_filter(session, view, setter_arg):
            se_filter = view.section_filters[setter_arg]
            se_filter.set(session, not se_filter.get(session))

        # Arrange.
        festival = create_std_festival()
        section_1 = Section.sections.create(festival=festival, section_id=20, name='Gods', color='blue')
        section_2 = Section.sections.create(festival=festival, section_id=21, name='Animals', color='pink')
        section_3 = Section.sections.create(festival=festival, section_id=22, name='Plants', color='green')
        subsection_1 = Subsection.subsections.create(
            subsection_id=1, section=section_1, name='Led Zeppelin', description='These films concern Gods of Rock')
        subsection_2 = Subsection.subsections.create(
            subsection_id=2, section=section_2, name='Tuna season', description='About symbolic use of fishes')
        subsection_3 = Subsection.subsections.create(
            subsection_id=3, section=section_3, name='Speaking trees', description='About secret properties of plants')
        film_with_subsection_1 = create_film(film_id=211, title='Pages or Plants', minutes=98,
                                             subsection=subsection_1, festival=festival)
        film_with_subsection_2 = create_film(film_id=212, title='Salmons Go Crazy', minutes=79,
                                             subsection=subsection_2, festival=festival)
        film_with_subsection_3 = create_film(film_id=210, title='Symbolic Strangling', minutes=111,
                                             subsection=subsection_3, festival=festival)

        films_view, context = self.arrange_filtered_view(set_section_filter, section_2)

        # Act.
        get_response = films_view.render_to_response(context)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, film_with_subsection_2.title)
        self.assertNotContains(get_response, film_with_subsection_1.title)
        self.assertNotContains(get_response, film_with_subsection_3.title)

    def test_select_section_deselects_subsection(self):
        """
        If a section is selected while a subsection is already selected, the subsection filter is cleared.
        """
        def set_subsection_filter(session, view, setter_arg):
            su_filter = view.subsection_filters[setter_arg]
            su_filter.set(session, not su_filter.get(session))

        def get_section_query_from_content(response):
            content = get_decoded_content(response)
            m = re_section_query.search(content)
            return m.group(1)

        # Arrange.

        # Arrange data in the database.
        festival = create_std_festival()
        section = Section.sections.create(festival=festival, section_id=23, name='Running', color='yellow')
        subsection_1 = Subsection.subsections.create(
            subsection_id=31, section=section, name='The Olympics', description='Collects films about olympic runners')
        subsection_2 = Subsection.subsections.create(
            subsection_id=32, section=section, name='Cold', description='Films about adults with running noses')
        film_with_subsection_1 = create_film(film_id=301, title='Haruki Murakami', minutes=102,
                                             subsection=subsection_1, festival=festival)
        film_with_subsection_2 = create_film(film_id=302, title='Hot Chili!', minutes=134,
                                             subsection=subsection_2, festival=festival)

        # Arrange a compiled regex for multiple use in get_section_query_from_content().
        str_section_query = r'<a href="([^>]*)">[^<]*</a>\s*<span[^>]*>\s*' + section.name + r'\s*</span>'
        re_section_query = re.compile(str_section_query, re.MULTILINE)

        # Arrange a response with a subsection selected.
        films_view, context_1 = self.arrange_filtered_view(set_subsection_filter, subsection_1)
        get_response_1 = films_view.render_to_response(context_1)

        # Arrange a response with the accessory section selected. This should deselect the subsection.
        select_section_url = get_section_query_from_content(get_response_1.render())
        get_response_2 = self.client.get(select_section_url)

        # Act.
        # Deselect the sector. All films should be visible again.
        deselect_section_url = get_section_query_from_content(get_response_2)
        get_response_3 = self.client.get(deselect_section_url)

        # Assert.
        self.assertEqual(get_response_1.status_code, HTTPStatus.OK)
        self.assertEqual(get_response_2.status_code, HTTPStatus.OK)
        self.assertContains(get_response_1, film_with_subsection_1.title)
        self.assertNotContains(get_response_1, film_with_subsection_2.title)
        self.assertContains(get_response_2, film_with_subsection_1.title)
        self.assertContains(get_response_2, film_with_subsection_2.title)
        self.assertRegex(get_decoded_content(get_response_2),
                         r'<a[^>]*>\s*Select subsection',
                         'Subsection should be deselected')
        self.assertRegex(get_decoded_content(get_response_2),
                         r'<a[^>]*>\s*Remove filter\s*</a>\s*<span[^>]*>\s*' + section.name + r'\s*</span',
                         'Subsection should be selected')
        self.assertContains(get_response_3, film_with_subsection_1.title)
        self.assertContains(get_response_3, film_with_subsection_2.title)

    def test_find_title(self):
        """
        Films starting with or containing a text snippet that is entered
        in the search box are displayed as links.
        """
        # Arrange.
        festival = create_std_festival()
        film_1 = create_film(title='Early Masters: Bruno Ganz', minutes=132, film_id=2031, festival=festival)
        film_2 = create_film(title='La Brunette', sort_title='Brunette, La', minutes=89, film_id=2030, festival=festival)
        film_3 = create_film(title='Bruna Brockovich', minutes=131, film_id=2032, festival=festival)
        film_4 = create_film(title='Four Brothers', minutes=98, film_id=3033, festival=festival)
        film_5 = create_film(title='Ronnie Brunswijk, Friend or Foe', minutes=17, film_id=3034, festival=festival)
        found_films_re = re.compile(
            r'<h3[^>]*>Search[^>]+results</h3>\s*'
            + r'<a [^>]*>' + f'{film_3.title}' + r'</a>\s*<br>\s*'
            + r'<a [^>]*>' + f'{film_2.title}' + r'</a>\s*<br>\s*'
            + r'<a [^>]*>' + f'{film_5.title}' + r'</a>\s*<br>\s*'
            + r'<a [^>]*>' + f'{film_1.title}' + r'</a>\s*<br>\s*'
            + f'<p[^.]*>'
        )
        post_data = {BaseFilmsFormView.SEARCH_KEY: ['brun']}

        _ = self.get_regular_fan_request()

        # Act.
        post_response = self.client.post(reverse('films:films'), post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertRegex(get_decoded_content(redirect_response), found_films_re)
        self.assertContains(redirect_response, film_4.title)
