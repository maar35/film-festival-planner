from datetime import date
from http import HTTPStatus

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse

from festivals.models import Festival, FestivalBase
from film_list.models import FilmFan


class AuthenticationViewsTest(TestCase):

    def setUp(self):
        super(AuthenticationViewsTest, self).setUp()
        
        # Set up a registered fan.
        self.registered_fan = FilmFan.film_fans.create(name='Mick', seq_nr=1943)
        self.registered_fan.save()
        self.credentials = {
            'username': 'mick',
            'password': 'shot-away',
        }
        self.registered_user = User.objects.create_user(username=self.credentials['username'])
        self.registered_user.set_password(self.credentials['password'])
        self.registered_user.is_active = True
        self.registered_user.save()

        # Set up an unregistered user.
        self.attacking_fan = 'Brian'
        self.attack_credentials = {
            'username': 'brian',
            'password': 'harmonica',
        }
        self.attacking_user = User.objects.create_user(username=self.attack_credentials['username'])

        # Set up a festival. Needed to render any page in the app.
        festival_base = FestivalBase.festival_bases.create(
            mnemonic='Kaboom',
            name='Kaboom Animation Festival'
        )
        festival_base.save()
        self.festival = Festival.festivals.create(
            base=festival_base,
            year=2023,
            start_date=date(2023, 3, 27),
            end_date=date(2023, 4, 2),
        )
        self.festival.save()

    def arrange_get_response(self, ):
        get_response = self.client.get(reverse('authentication:login'))
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, 'Username')
        self.assertContains(get_response, 'Password')

    def assert_redisplay_login_with_error(self, post_response):
        self.assertEqual(post_response.status_code, HTTPStatus.OK)
        self.assertFalse(post_response.context['user'].is_authenticated)
        self.assertContains(post_response, "That's not a valid username or password")
        self.assertTemplateUsed(post_response, 'authentication/login.html')
        self.assertContains(post_response, self.festival)

    def test_registered_user_can_login(self):
        """
        A registered user can log in using the login view.
        """
        # Arrange.
        self.arrange_get_response()

        # Act.
        post_response = self.client.post(reverse('authentication:login'), self.credentials)

        # Assert.
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        redirect_response = self.client.get(post_response.url)
        self.assertTrue(redirect_response.context['user'].is_authenticated)
        self.assertContains(redirect_response, self.credentials['username'])
        self.assertContains(redirect_response, self.registered_fan.name)
        self.assertContains(redirect_response, self.festival)

    def test_unregistered_user_cannot_login(self):
        """
        An unregistered user can not log in.
        """
        # Arrange.
        self.arrange_get_response()

        # Act.
        post_response = self.client.post(reverse('authentication:login'), self.attack_credentials)

        # Assert.
        self.assert_redisplay_login_with_error(post_response)

    def test_registered_user_cannot_login_with_wrong_password(self):
        """
        A registered user can not log in with a wrong password.
        """
        # Arrange.
        wrong_credentials = self.credentials
        wrong_credentials['password'] = self.credentials['password'] + 'typo'
        self.arrange_get_response()

        # Act.
        post_response = self.client.post(reverse('authentication:login'), wrong_credentials)

        # Assert.
        self.assert_redisplay_login_with_error(post_response)
