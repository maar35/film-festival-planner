import csv
import os
import shutil
from http import HTTPStatus

from django.urls import reverse

from festivals.tests import create_festival
from film_list.models import FilmFanFilmRating
from film_list.tests import create_film, ViewsTestCase
from loader import views
from loader.views import FilmLoader, RatingLoader


def create_rating(film, fan, rating):
    return FilmFanFilmRating.fan_ratings.create(film=film, film_fan=fan, rating=rating)


def serialize_film(film):
    minutes = int(film.duration.total_seconds() / 60)
    duration_str = str(minutes) + "′"
    fields = [
        str(film.seq_nr),
        str(film.film_id),
        film.sort_title,
        film.title,
        film.title_language,
        film.section if film.section is not None else '',
        duration_str,
        film.medium_category,
        film.url
    ]
    return fields


def serialize_rating(rating):
    fields = [
        str(rating.film_id),
        rating.film_fan.name,
        str(rating.rating),
    ]
    return fields


class LoaderViewsTests(ViewsTestCase):

    def setUp(self):
        super(LoaderViewsTests, self).setUp()

        # Set up a festival. Needed to render any page in the app.
        self.festival = self.create_festival('2023-02-16', '2023-02-26')

        # Set up POST data for the ratings.html template.
        self.post_data = {f'festival_{self.festival.id}': ['Load'], 'keep_ratings': []}

        # Create working directories for films and ratings.
        self.create_planner_data_dir()
        self.create_festival_data_dir()

    def tearDown(self):
        super(LoaderViewsTests, self).tearDown()
        self.remove_festival_data()

    @property
    def base_festival_mnemonic(self):
        return 'Berlinale'

    def create_festival(self, start_data_str, end_date_str):
        return create_festival(self.base_festival_mnemonic, start_data_str, end_date_str)

    def create_planner_data_dir(self):
        os.makedirs(self.festival.planner_data_dir)

    def create_festival_data_dir(self):
        os.makedirs(self.festival.festival_data_dir)

    def remove_festival_data(self):
        base_dir = self.festival.festival_base_dir
        shutil.rmtree(base_dir)

    def assert_reading_from_file(self, get_response, post_response, redirect_response):
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, '#Ratings on file')
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(redirect_response, 'film_list/film_list.html')
        self.assertContains(redirect_response, 'Load results')
        self.assertContains(redirect_response, 'Reading from file')

    def test_admin_can_load_films(self):
        """
        A file with correct film records can be loaded by an admin fan.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = views.load_festival_ratings(request)

        film_1 = create_film(1, 'Der Beliner', 103, festival=self.festival)
        film_2 = create_film(2, 'Angst und Freude', 15, festival=self.festival)
        films_file = self.festival.films_file
        with open(films_file, 'w', newline='') as csvfile:
            film_writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film_1))
            film_writer.writerow(serialize_film(film_2))

        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertNotContains(redirect_response, 'not found')
        self.assertNotContains(redirect_response, 'Bad value in file')
        self.assertNotContains(redirect_response, 'incompatible header')
        self.assertContains(redirect_response, '2 films read')
        self.assertContains(redirect_response, 'No ratings read')

    def test_admin_can_load_ratings(self):
        """
        A file with correct rating records can be loaded by an admin fan.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = views.load_festival_ratings(request)

        film = create_film(1, 'Leben und Sterben in Tirol', 182, festival=self.festival)
        with open(self.festival.films_file, 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, delimiter=';', quotechar='"')
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film))

        rating_1 = create_rating(film, self.admin_fan, 10)
        rating_2 = create_rating(film, self.regular_fan, 8)
        with open(self.festival.ratings_file, 'w', newline='') as csv_ratings_file:
            rating_writer = csv.writer(csv_ratings_file, delimiter=';', quotechar='"')
            rating_writer.writerow(RatingLoader.expected_header)
            rating_writer.writerow(serialize_rating(rating_1))
            rating_writer.writerow(serialize_rating(rating_2))

        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, '1 films read')
        self.assertNotContains(redirect_response, 'not found')
        self.assertNotContains(redirect_response, 'Bad value in file')
        self.assertNotContains(redirect_response, 'incompatible header')
        self.assertNotContains(redirect_response, 'existing ratings saved')
        self.assertContains(redirect_response, '2 ratings read')

    def test_admin_can_keep_ratings_while_loading_films(self):
        """
        Existing ratings can be kept when loading films.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = views.load_festival_ratings(request)

        film = create_film(1, 'Leben und Sterben in Tirol', 182, festival=self.festival)
        with open(self.festival.films_file, 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, delimiter=';', quotechar='"')
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film))

        rating_1 = create_rating(film, self.admin_fan, 10)
        _ = create_rating(film, self.regular_fan, 8)
        with open(self.festival.ratings_file, 'w', newline='') as csv_ratings_file:
            rating_writer = csv.writer(csv_ratings_file, delimiter=';', quotechar='"')
            rating_writer.writerow(RatingLoader.expected_header)
            rating_writer.writerow(serialize_rating(rating_1))

        self.post_data['keep_ratings'] = ['on']
        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, '1 films read')
        self.assertNotContains(redirect_response, 'not found')
        self.assertNotContains(redirect_response, 'Bad value in file')
        self.assertNotContains(redirect_response, 'incompatible header')
        self.assertContains(redirect_response, '2 existing ratings saved')
        self.assertContains(redirect_response, '2 ratings read')

    def test_non_admin_cannot_load_data(self):
        """
        A non-admin fan can't load data.
        """
        request = self.get_regular_fan_request()

        # Act.
        get_response = views.load_festival_ratings(request)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, 'Not allowed')
        self.assertNotContains(get_response, '#Ratings on file')

    def test_admin_cannot_load_incompatible_film_file(self):
        """
        Ad admin fan can't load an incompatible films file.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = views.load_festival_ratings(request)

        films_file = self.festival.films_file
        with open(films_file, 'w', newline='') as csvfile:
            film_writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            film_writer.writerow(FilmLoader.expected_header[1:])

        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, 'incompatible header')
        self.assertNotContains(redirect_response, 'films read')
        self.assertNotContains(redirect_response, 'ratings read')

    def test_admin_cannot_load_corrupt_film(self):
        """
        Ad admin fan can't load a films file with bad data.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = views.load_festival_ratings(request)

        film = create_film(1, 'Der Faust', 303, festival=self.festival)
        films_file = self.festival.films_file
        with open(films_file, 'w', newline='') as csvfile:
            film_writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            film_writer.writerow(FilmLoader.expected_header)
            film_row = serialize_film(film)
            film_row[6] = 'invalid_duration'
            film_writer.writerow(film_row)

        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, 'Bad value in file')
        self.assertNotContains(redirect_response, 'films read')
        self.assertNotContains(redirect_response, 'ratings read')

    def test_admin_cannot_load_corrupt_rating(self):
        """
        Ad admin fan can't load a ratings file with bad data.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = views.load_festival_ratings(request)

        film = create_film(1, 'Schwestern und Töchter', 95, festival=self.festival)
        with open(self.festival.films_file, 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, delimiter=';', quotechar='"')
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film))

        rating_1 = create_rating(film, self.admin_fan, 6)
        rating_2 = create_rating(film, self.regular_fan, 9)
        with open(self.festival.ratings_file, 'w', newline='') as csv_ratings_file:
            rating_writer = csv.writer(csv_ratings_file, delimiter=';', quotechar='"')
            rating_writer.writerow(RatingLoader.expected_header)
            rating_writer.writerow(serialize_rating(rating_1))
            rating_writer.writerow((serialize_rating(rating_2))[1:])

        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, 'films read')
        self.assertContains(redirect_response, 'Bad value in file')
        self.assertContains(redirect_response, 'No ratings read')
