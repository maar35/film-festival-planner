from http import HTTPStatus

from django.urls import reverse

from festivals.tests import create_festival, mock_base_festival_mnemonic
from films.tests import ViewsTestCase
from theaters.models import City, Theater, Screen


class TheaterViewTests(ViewsTestCase):

    def setUp(self):
        super().setUp()

        # Set up a festival. Needed to render any page in the app.
        self.city = City.cities.create(city_id=1, name='Berlin', country='de')
        self.festival = self.create_festival(self.city, '2023-02-16', '2023-02-26')

        # Create some URL shorthands.
        self.theaters_url = reverse('theaters:theaters')
        self.details_url = lambda pk: reverse('theaters:details', args=[pk])

    def tearDown(self):
        super().tearDown()

    @staticmethod
    def create_festival(city, start_data_str, end_date_str):
        return create_festival(mock_base_festival_mnemonic(), city, start_data_str, end_date_str)

    def arrange_create_theater(self, theater_id, parse_name, abbreviation, priority):
        city = self.city
        return Theater.theaters.create(
            theater_id=theater_id,
            city=city,
            parse_name=parse_name,
            abbreviation=abbreviation,
            priority=priority,
        )

    @staticmethod
    def arrange_create_screen(
            screen_id, theater, screen_name, abbreviation, address_type=Screen.ScreenAddressType.PHYSICAL):
        parse_name = f'{theater.parse_name} {screen_name}'
        return Screen.screens.create(
            screen_id=screen_id,
            theater=theater,
            parse_name=parse_name,
            abbreviation=abbreviation,
            address_type=address_type,
        )

    def test_list_view_displays_theaters(self):
        # Arrange.
        theater_1 = self.arrange_create_theater(1, 'Bellevue Berlin', 'bellevue', Theater.Priority.NO_GO)
        theater_2 = self.arrange_create_theater(2, 'Liebeskammer Berlin', 'kammer', Theater.Priority.HIGH)

        # Act.
        response = self.client.get(self.theaters_url)

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, self.city.name)
        self.assertContains(response, theater_1.parse_name)
        self.assertContains(response, theater_2.abbreviation)
        self.assertNotContains(response, Theater.Priority.LOW.label)
        self.assertContains(response, Theater.Priority.NO_GO.label)

    def test_hacker_can_not_display_theater_details(self):
        # Arrange.
        theater = self.arrange_create_theater(17, 'Festarena der Filme', 'fest', Theater.Priority.LOW)
        pk = theater.pk

        # Act.
        get_response = self.client.get(self.details_url(pk))
        redirect_response = self.client.get(get_response.url)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.FOUND)
        self.assertContains(redirect_response, 'Application Login')
        self.assertContains(redirect_response, 'Please enter your credentials')
        self.assertNotContains(redirect_response, theater.parse_name)
        self.assertNotRegex(redirect_response.rendered_content, r'Abbreviation.*?' + f'{theater.abbreviation}')

    def test_admin_can_display_theater_details(self):
        # Arrange.
        theater = self.arrange_create_theater(6, 'Baer Palace', 'b', Theater.Priority.NO_GO)
        screen_1 = self.arrange_create_screen(11, theater, 'Zimmer 1', '1')
        screen_2 = self.arrange_create_screen(12, theater, 'Zimmer 2', '2')
        pk = theater.pk
        _ = self.get_admin_request()

        # Act.
        response = self.client.get(self.details_url(pk))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Theater Details')
        self.assertNotContains(response, 'Not allowed')
        self.assertContains(response, screen_1.parse_name)
        self.assertContains(response, screen_2.abbreviation)

    def test_regular_fan_can_not_display_theater_details(self):
        # Arrange.
        theater = self.arrange_create_theater(1, 'Theater Georges Méliès', 'gm-', Theater.Priority.HIGH)
        screen_g = self.arrange_create_screen(7, theater, 'großer Raum', 'gr')
        screen_k = self.arrange_create_screen(4, theater, 'kleine Halle', 'kl')
        pk = theater.pk
        _ = self.get_regular_fan_request()

        # Act.
        response = self.client.get(self.details_url(pk))

        # Assert.
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Theater Details')
        self.assertContains(response, 'Not allowed')
        self.assertNotContains(response, screen_g.parse_name)
        self.assertNotContains(response, screen_k.abbreviation)
