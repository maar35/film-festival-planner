from datetime import timedelta
from http import HTTPStatus
from importlib import import_module

import django.http
from django.conf import settings
from django.contrib.auth.models import User
from django.http import HttpRequest
from django.test import TestCase
from django.urls import reverse

from film_list import views
from .models import Film, FilmFan, me, FilmFanFilmRating


def create_film(film_id, title, minutes, seq_nr=-1):
    """
    Create a film with the given arguments in the database.
    """
    duration = timedelta(minutes=minutes)
    return Film.films.create(film_id=film_id, seq_nr=seq_nr, title=title, duration=duration)


def new_film(film_id, title, minutes, seq_nr=-1):
    """
    Create a film instance with the given arguments.
    """
    duration = timedelta(minutes=minutes)
    return Film(film_id=film_id, seq_nr=seq_nr, title=title, duration=duration)


def fan_name_to_user_name(fan_name):
    return f'{fan_name[0].lower()}{fan_name[1:]}'


def get_session_with_fan(fan):
    session_store = import_module(settings.SESSION_ENGINE).SessionStore
    session = session_store()
    session['fan_name'] = fan.name
    session.create()
    return session


class FilmModelTests(TestCase):

    def setUp(self):
        super(FilmModelTests, self).setUp()

        # Set up a regular user.
        self.regular_user = User.objects.create(username='paul')
        self.regular_user.set_password('mull-kintyre')
        self.regular_user.save()

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
        regular_fan = FilmFan.film_fans.create(name='Paul', seq_nr=1942)
        logged_in = self.client.login(username='paul', password='mull-kintyre')
        request = HttpRequest()
        request.user = self.regular_user
        request.session = get_session_with_fan(regular_fan)

        # Act and Assert.
        with self.assertRaisesMessage(django.http.response.Http404, 'No Film matches the given query.'):
            _ = views.rating(request, hacked_film.film_id)
        self.assertIs(logged_in, True)

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
        regular_fan = FilmFan.film_fans.create(name='Paul', seq_nr=1942)
        logged_in = self.client.login(username='paul', password='mull-kintyre')
        request = HttpRequest()
        request.user = self.regular_user
        request.session = get_session_with_fan(regular_fan)

        # Act.
        response = views.rating(request, created_film.film_id)

        # Assert.
        self.assertIs(logged_in, True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, created_film.title)

    def test_results_of_created_film(self):
        """
        The results view with film id of a film that was newly added to
        the database displays the details of the given film.
        """
        # Arrange.
        created_film = create_film(film_id=4422, title='The Wrong Answer', minutes=66)
        url = reverse('film_list:results', args=(created_film.film_id,))

        # Act.
        response = self.client.get(url)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertEqual(response.context['film'], created_film)


class FilmFanModelTests(TestCase):

    def setUp(self):
        super(FilmFanModelTests, self).setUp()

        # Set up a regular (non-admin) fan.
        regular_fans = [fan for fan in FilmFan.film_fans.all() if not fan.is_admin]
        self.regular_fan = regular_fans[0]

        # Set up a regular user.
        self.regular_user = User.objects.create(username='mick')
        self.regular_user.set_password('shot-away')
        self.regular_user.save()

        # Set up an admin user.
        self.admin_user = User.objects.create(username='john')
        self.admin_user.set_password('war=over')
        self.admin_user.save()

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

    def test_login(self):
        """
        A test fan can log in.
        """
        # Arrange.
        pass

        # Act.
        logged_in = self.client.login(username='john', password='war=over')

        # Assert.
        self.assertIs(logged_in, True)

    def test_admin_can_switch_to_a_different_film_fan(self):
        """
        An admin fan can switch to a different fan without logging in.
        """
        # Arrange.
        admin_fan = FilmFan.film_fans.create(name='John', seq_nr=-1, is_admin=True)
        logged_in = self.client.login(username='john', password='war=over')
        request = HttpRequest()
        request.user = self.admin_user
        request.session = get_session_with_fan(admin_fan)

        # Act.
        response = views.film_fan(request)

        # Assert.
        self.assertIs(logged_in, True)
        self.assertIs(admin_fan.is_admin, True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Set current fan')

    def test_non_admin_cannot_switch_to_a_different_film_fan(self):
        """
        A non-admin fan cannot switch to another fan without logging
        in.
        """
        # Arrange.
        regular_fan = FilmFan.film_fans.create(name='Mick', seq_nr=1943)
        logged_in = self.client.login(username='mick', password='shot-away')
        request = HttpRequest()
        request.user = self.regular_user
        request.session = get_session_with_fan(regular_fan)

        # Act.
        response = views.film_fan(request)

        # Assert.
        self.assertIs(logged_in, True)
        self.assertIs(regular_fan.is_admin, False)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Mick')
        self.assertContains(response, 'Only an admin fan can rate for other fans.')

    def test_admin_can_vote_on_behalf_of_a_different_film_fan(self):
        """
        An admin fan can rate films on behalf of another film fan.
        """
        # Arrange.
        film = create_film(film_id=5100, title='Rate Me, Rate Me!', minutes=17)

        admin_fan = FilmFan.film_fans.create(name='John', seq_nr=-1, is_admin=True)
        logged_in = self.client.login(username='john', password='war=over')

        regular_fan = self.regular_fan

        request = HttpRequest()
        request.user = self.admin_user
        request.session = get_session_with_fan(regular_fan)

        # Act.
        response = views.rating(request, film.film_id)

        # Assert.
        self.assertIs(logged_in, True)
        self.assertIs(regular_fan.is_admin, False)
        self.assertIs(admin_fan.is_admin, True)
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'john represents')
        self.assertContains(response, regular_fan.name)


class RatingModelTests(TestCase):

    def test_rating_has_correct_meaning(self):
        """
        Rating 7 has meaning INDECISIVE.
        """

        # Arrange.
        rating_value = 7
        rating_meaning = 'Indecisive'
        film = Film(film_id=-1, seq_nr=-1, title='A Test Movie', duration=timedelta(minutes=666))
        film.save()
        fan = me()
        rating = FilmFanFilmRating(film=film, film_fan=fan, rating=rating_value)
        rating.save()

        # Act.
        rating_name = fan.fan_rating_name(film)

        # Assert.
        self.assertEqual(rating_meaning, rating_name)
