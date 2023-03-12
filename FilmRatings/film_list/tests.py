import re
from datetime import timedelta
from http import HTTPStatus
from importlib import import_module

import django.http
from django.conf import settings
from django.http import HttpRequest
from django.test import TestCase
from django.urls import reverse

from authentication.tests import set_up_user_with_fan
from festivals.tests import create_festival
from film_list import views
from .models import Film, FilmFan, me, FilmFanFilmRating, current_fan, get_rating_name


def create_film(film_id, title, minutes, seq_nr=-1, festival=None):
    """
    Create a film with the given arguments in the database.
    """
    if festival is None:
        festival = create_festival('IFFR', '2021-01-27', '2021-02-06')
    duration = timedelta(minutes=minutes)
    return Film.films.create(festival_id=festival.id, film_id=film_id,seq_nr=seq_nr,
                             title=title, duration=duration, subsection='')


def new_film(film_id, title, minutes, seq_nr=-1):
    """
    Create a film instance with the given arguments.
    """
    duration = timedelta(minutes=minutes)
    return Film(film_id=film_id, seq_nr=seq_nr, title=title, duration=duration)


class FilmModelTests(TestCase):
    pass


class FilmFanModelTests(TestCase):

    def test_film_fan_me_is_maarten(self):
        """
        me() always returns 'Maarten'.
        """
        # Arrange.
        maarten = FilmFan.film_fans.get(name='Maarten')

        # Act.
        fan = me()

        # Assert.
        self.assertEqual(fan, maarten)

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


class RatingModelTests(TestCase):

    def test_rating_has_correct_meaning(self):
        """
        Rating 7 has meaning INDECISIVE.
        """
        # Arrange.
        rating_value = 7
        rating_meaning = 'Indecisive'
        festival = create_festival('IDFA', '2022-07-17', '2022-07-27')
        film = Film(festival_id=festival.id, film_id=-1, seq_nr=-1, title='A Test Movie', duration=timedelta(minutes=666))
        film.save()
        fan = me()
        rating = FilmFanFilmRating(film=film, film_fan=fan, rating=rating_value)
        rating.save()

        # Act.
        rating_name = fan.fan_rating_name(film)

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
        festival_1 = create_festival('IDFA', '2021-07-17', '2021-07-27')
        festival_2 = create_festival('MTMF', '2022-04-17', '2022-04-27')
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


def login(self, credentials):
    return self.client.login(
        username=credentials['username'],
        password=credentials['password']
    )


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


class ViewsTestCase(TestCase):

    def setUp(self):
        super(ViewsTestCase, self).setUp()

        # Set up an admin user.
        self.admin_fan, self.admin_user, self.admin_credentials = \
            set_up_user_with_fan('john', 'war=over', seq_nr=1940, is_admin=True)

        # Set up a regular user.
        self.regular_fan, self.regular_user, self.regular_credentials = \
            set_up_user_with_fan('paul', 'mull-kintyre', seq_nr=1942)

    def get_request(self, fan, user, credentials):
        logged_in = login(self, credentials)
        request = HttpRequest()
        request.user = user
        request.session = get_session_with_fan(fan)
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


class FilmListViewsTests(ViewsTestCase):

    @staticmethod
    def rating_post_data(film, rating_value=0):
        return {f'list_{film.id}_{rating_value}': ['label']}

    def assert_rating_action_redirect(self, user, get_response, post_response, redirect_response):
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, user.username)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertURLEqual(post_response.url, reverse('film_list:film_list'))
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)

    def test_rating_of_hacked_film_without_login(self):
        """
        The rating view with a hacked film id returns a 302 found
        when not logged in.
        """
        # Arrange.
        hacked_film = new_film(film_id=5000, title='Future Question', minutes=95)
        url = reverse('film_list:rating', args=(hacked_film.film_id,))

        # Act.
        response = self.client.get(url)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_rating_of_hacked_film_logged_in(self):
        """
        The rating view with a hacked film id returns a 404 not found.
        """
        # Arrange.
        hacked_film = new_film(film_id=5001, title='Future Questions', minutes=96)
        request = self.get_regular_fan_request()

        # Act and Assert.
        with self.assertRaisesMessage(django.http.response.Http404, 'No Film matches the given query.'):
            _ = views.rating(request, hacked_film.film_id)

    def test_results_of_hacked_film(self):
        """
        The results view with a hacked film id returns a 404 not found.
        """
        # Arrange.
        hacked_film = new_film(film_id=4242, title='The Negative Answer', minutes=84)
        url = reverse('film_list:results', args=(hacked_film.film_id,))

        # Act.
        response = self.client.get(url)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.NOT_FOUND)

    def test_rating_of_created_film_without_login(self):
        """
        The rating view with film id of a film that was newly added to
        the database forbids to view the ratings of the given film
        when not logged in.
        """
        # Arrange.
        created_film = create_film(film_id=6000, title='New Adventure', minutes=114)
        url = reverse('film_list:rating', args=(created_film.film_id,))

        # Act.
        response = self.client.get(url)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.FOUND)

    def test_rating_of_created_film_logged_in(self):
        """
        The rating view with film id of a film that was newly added to
        the database displays the ratings of the given film.
        """
        # Arrange.
        created_film = create_film(film_id=6001, title='New Adventures', minutes=115)
        request = self.get_regular_fan_request()

        # Act.
        response = views.rating(request, created_film.id)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, created_film.title)

    def test_results_of_created_film(self):
        """
        The results view with film id of a film that was newly added to
        the database displays the details of the given film.
        """
        # Arrange.
        created_film = create_film(film_id=4422, title='The Wrong Answer', minutes=66)
        url = reverse('film_list:results', args=(created_film.id,))

        # Act.
        response = self.client.get(url)

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
        logged_in = login(self, self.admin_credentials)

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

    def test_admin_can_vote_on_behalf_of_a_different_film_fan(self):
        """
        An admin fan can rate films on behalf of another film fan.
        """
        # Arrange.
        film = create_film(film_id=5100, title='Rate Me, Rate Me!', minutes=17)
        request = self.get_request(self.regular_fan, self.admin_user, self.admin_credentials)

        # Act.
        response = views.rating(request, film.id)

        # Assert.
        self.assertIs(self.regular_fan.is_admin, False)
        self.assertIs(self.admin_fan.is_admin, True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, f"{self.admin_credentials['username']} represents")
        self.assertContains(response, self.regular_fan.name)

    def test_logged_in_fan_can_add_rating(self):
        """
        A logged in fan can add a rating to a film.
        """
        # Arrange.
        festival = create_festival('NFF', '2024-07-11', '2024-07-20')
        film = create_film(film_id=2001, title='Odysseus in Trouble', minutes=128, festival=festival)

        get_request = self.get_admin_request()
        get_response = views.film_list(get_request)

        fan = self.admin_fan
        rating_value = 9
        rating_name = get_rating_name(rating_value)
        post_data = self.rating_post_data(film, rating_value=rating_value)
        post_request = get_request_with_session(get_request, method_is_post=True, post_data=post_data)
        post_response = views.film_list(post_request)

        # Act.
        redirect_response = views.film_list(get_request_with_session(post_request))

        # Assert.
        self.assert_rating_action_redirect(get_request.user, get_response, post_response, redirect_response)
        self.assertNotContains(redirect_response, 'Unexpected error')
        log_re = re.compile(f'{fan.name}' + r'\s+' + f'gave.*{film.title}.*a rating of.* {rating_value}'
                            + r' \(' + f'{rating_name}' + r'\)')
        self.assertRegex(redirect_response.content.decode('utf-8'), log_re)

    def test_logged_in_fan_can_change_rating(self):
        """
        A logged in fan can change an existing rating of a film.
        """
        # Arrange.
        film = create_film(film_id=1948, title='Big Brothers', minutes=110)

        get_request = self.get_regular_fan_request()
        get_response = views.film_list(get_request)

        fan = current_fan(get_request.session)
        old_rating_value = 8
        FilmFanFilmRating.fan_ratings.create(film=film, film_fan=fan, rating=old_rating_value)
        new_rating_value = 3
        new_rating_name = get_rating_name(new_rating_value)
        post_data = self.rating_post_data(film, rating_value=new_rating_value)

        post_request = get_request_with_session(get_request, method_is_post=True, post_data=post_data)
        post_response = views.film_list(post_request)

        # Act.
        redirect_response = views.film_list(get_request_with_session(post_request))

        # Assert.
        self.assert_rating_action_redirect(get_request.user, get_response, post_response, redirect_response)
        log_re = re.compile(f'{fan.name}' + r'\s+'
                            + f'changed rating {old_rating_value} of.*{film.title}.*into.* {new_rating_value}'
                            + r' \(' + f'{new_rating_name}' + r'\)')
        self.assertRegex(redirect_response.content.decode('utf-8'), log_re)

    def test_logged_in_fan_can_remove_rating_in_detail_view(self):
        """
        A logged in fan can remove a rating from the film detail view.
        """
        # Arrange.
        does_not_exist_msg = 'FilmFanFilmRating matching query does not exist'
        film = create_film(film_id=1999, title='The Prince and the Price', minutes=98)
        fan = self.regular_fan
        rating_value = 6
        FilmFanFilmRating.fan_ratings.create(film=film, film_fan=fan, rating=rating_value)
        rating = FilmFanFilmRating.fan_ratings.get(film=film, film_fan=fan)
        self.assertEqual(rating.rating, rating_value)

        get_request = self.get_regular_fan_request()
        get_response = views.rating(get_request, film.id)

        new_rating_value = 0
        post_data = {'fan_rating': f'{new_rating_value}'}
        post_request = get_request_with_session(get_request, method_is_post=True, post_data=post_data)
        post_response = views.rating(post_request, film.id)

        # Act.
        redirect_request = get_request_with_session(get_request)
        results_view = views.ResultsView()
        results_view.object = film
        results_view.setup(redirect_request)
        context = results_view.get_context_data()
        redirect_response = results_view.render_to_response(context)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, self.regular_user.username)
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertURLEqual(post_response.url, reverse('film_list:results', args=[film.id]))
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertContains(redirect_response, self.regular_fan.name)
        self.assertContains(redirect_response, self.admin_fan.name)
        with self.assertRaisesMessage(FilmFanFilmRating.DoesNotExist, does_not_exist_msg):
            _ = FilmFanFilmRating.fan_ratings.get(film=film, film_fan=fan)
        current_fan_row_re = re.compile(f'{fan.name}' + r'</a>\s*</td>\s*<td[^>]*>.*?</td>\s*<td>Unrated</td>',
                                        re.DOTALL)
        self.assertRegex(redirect_response.content.decode('utf-8'), current_fan_row_re)

    def test_non_admin_cannot_save_ratings(self):
        """
        A non-admin fan can't save ratings.
        """
        # Arrange.
        festival = create_festival('IDFA', '2023-11-19', '2023-11-28')
        get_request = self.get_regular_fan_request()
        save_view = views.SaveView()
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
        festival = create_festival('IDFA', '2023-11-19', '2023-11-28')
        get_request = self.get_admin_request()
        save_view = views.SaveView()
        save_view.object = festival
        save_view.setup(get_request)
        context = save_view.get_context_data()

        # Act.
        get_response = save_view.render_to_response(context)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertNotContains(get_response, 'Not allowed')
