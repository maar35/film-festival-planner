from unittest import skip

from django.test import TestCase

import csv
import os
import re
import shutil
from http import HTTPStatus

from django.test import RequestFactory
from django.urls import reverse

from festivals.models import Festival
from festivals.tests import create_festival, mock_base_festival_mnemonic
from films.models import FilmFanFilmRating
from films.tests import create_film, ViewsTestCase, get_request_with_session
from films.views import SaveView, films
from loader.forms.loader_forms import FilmLoader, RatingLoader
from loader.views import SectionsLoaderView, get_festival_row, load_festival_ratings
from sections.models import Section
from theaters.models import City


def create_rating(film, fan, rating):
    return FilmFanFilmRating.film_ratings.create(film=film, film_fan=fan, rating=rating)


def serialize_film(film):
    minutes = int(film.duration.total_seconds() / 60)
    duration_str = str(minutes) + "′"
    fields = [
        str(film.seq_nr),
        str(film.film_id),
        film.sort_title,
        film.title,
        film.title_language,
        film.subsection if film.subsection is not None else '',
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
        self.city = City.cities.create(city_id=1, name='Berlin', country='de')
        self.festival = self.create_festival(self.city, '2023-02-16', '2023-02-26')

        # Create working directories for films and ratings.
        self.create_planner_data_dir()
        self.create_festival_data_dir()

    def tearDown(self):
        super(LoaderViewsTests, self).tearDown()
        self.city.delete()
        self.remove_festival_data()

    @staticmethod
    def create_festival(city, start_data_str, end_date_str):
        return create_festival(mock_base_festival_mnemonic(), city, start_data_str, end_date_str)

    def create_planner_data_dir(self):
        os.makedirs(self.festival.planner_data_dir)

    def create_festival_data_dir(self):
        os.makedirs(self.festival.festival_data_dir)

    def remove_festival_data(self):
        base_dir = self.festival.festival_base_dir
        shutil.rmtree(base_dir)


class RatingLoaderViewsTests(LoaderViewsTests):

    def setUp(self):
        super(RatingLoaderViewsTests, self).setUp()

        # Set up POST data for the ratings.html template.
        self.post_data = {f'festival_{self.festival.id}': ['Load'], 'keep_ratings': []}

    def tearDown(self):
        super(RatingLoaderViewsTests, self).tearDown()

    def assert_reading_from_file(self, get_response, post_response, redirect_response):
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, '#Ratings on file')
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(redirect_response, 'films/films.html')
        self.assertContains(redirect_response, 'Load results')
        self.assertContains(redirect_response, 'Reading from file')

    def test_admin_can_load_films(self):
        """
        A file with correct film records can be loaded by an admin fan.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = load_festival_ratings(request)

        film_1 = create_film(1, 'Der Berliner', 103, festival=self.festival)
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
        get_response = load_festival_ratings(request)

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
        get_response = load_festival_ratings(request)

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

    def test_non_admin_cannot_load_rating_data(self):
        """
        A non-admin fan can't load data.
        """
        request = self.get_regular_fan_request()

        # Act.
        get_response = load_festival_ratings(request)

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
        get_response = load_festival_ratings(request)

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
        get_response = load_festival_ratings(request)

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
        get_response = load_festival_ratings(request)

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

    def test_admin_can_save_ratings(self):
        """
        An admin fan can save ratings.
        """
        # Arrange.
        film_1 = create_film(1, 'Ich bin ein Hamburger', 86, festival=self.festival)
        film_2 = create_film(2, 'Böse Banken', 127, festival=self.festival)
        rating_1 = create_rating(film_1, self.admin_fan, 5)
        rating_2 = create_rating(film_1, self.regular_fan, 4)
        rating_3 = create_rating(film_2, self.regular_fan, 8)

        request = self.get_admin_request()
        save_view = SaveView()
        save_view.object = self.festival
        save_view.setup(request)
        context = save_view.get_context_data()
        get_response = save_view.render_to_response(context)

        post_request = get_request_with_session(request, method_is_post=True, post_data={'dummy_field': 'None'})
        save_view.object = self.festival
        save_view.setup(post_request)
        post_data = {'dummy_field': ''}
        factory = RequestFactory()
        post_request = factory.post(f'/films/{self.festival.id}/save/', data=post_data)
        post_request.user = self.admin_user
        post_request.session = request.session

        # Act.
        post_response = SaveView.as_view()(post_request)

        # Assert.
        redirect_request = get_request_with_session(request)
        redirect_response = films(redirect_request)
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertNotContains(get_response, 'Not allowed')
        self.assertContains(get_response, 'Save 3 ratings')
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertURLEqual(post_response.url, reverse('films:films'))
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertContains(redirect_response, 'Save results')
        self.assertContains(redirect_response, '3 existing ratings saved.')
        log_re = re.compile(r'\b3 existing ratings saved')
        self.assertRegex(redirect_response.content.decode('utf-8'), log_re)


class SectionLoaderViewsTests(LoaderViewsTests):
    max_section_id = 0

    def setUp(self):
        super(SectionLoaderViewsTests, self).setUp()

        # Get a good feeling about writing on festival files.
        self.assertEqual(mock_base_festival_mnemonic(), 'Berlinale')
        self.assertEqual(mock_base_festival_mnemonic(), self.festival.base.mnemonic)

        # Set up a loader view including the mock festival.
        self.loader_view = SectionsLoaderView()
        self.festival.id = max([row['id'] for row in self.loader_view.object_list]) + 1
        self.festival.save()
        self.loader_view.object_list.append(get_festival_row(self.festival))

        # Set up POST data for the sections.html template.
        self.post_data = {f'{self.festival.id}': ['Load']}

    def tearDown(self):
        super(SectionLoaderViewsTests, self).tearDown()

    def get_get_response(self, get_request):
        self.loader_view.setup(get_request)
        context = self.loader_view.get_context_data()
        return self.loader_view.render_to_response(context)

    def arrange_create_section(self, name, color):
        self.max_section_id += 1
        return Section.sections.create(festival=self.festival, section_id=self.max_section_id, name=name, color=color)

    @staticmethod
    def arrange_serialize_section(section):
        fields = [
            str(section.section_id),
            section.name,
            section.color,
        ]
        return fields

    def test_admin_can_load_sections(self):
        """
        A file with correct sections records can be loaded by an admin fan.
        """
        # Arrange.
        get_response = self.get_get_response(self.get_admin_request())
        section_1 = self.arrange_create_section('Hot items', 'HotPink')
        section_2 = self.arrange_create_section('Longs', 'Blue')
        sections_file = self.festival.sections_file
        with open(sections_file, 'w', newline='') as csvfile:
            section_writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            section_writer.writerow(self.arrange_serialize_section(section_1))
            section_writer.writerow(self.arrange_serialize_section(section_2))

        # Act.
        post_response = self.client.post(reverse('loader:sections'), self.post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, 'Pick a festival to load section data from')
        self.assertContains(get_response, '#Sections on file')
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertTemplateUsed(redirect_response, 'sections/index.html')
        self.assertContains(redirect_response, 'Section Overview')
        self.assertContains(redirect_response, 'Load results')
        self.assertContains(redirect_response, 'Reading from file')
        self.assertContains(redirect_response, '2 section records read')

    @skip("Test for test driven development still to be developed.")
    def test_regular_user_can_not_load_sections(self):
        # TODO use this test for test-driven development of implementing @login_required in a view class.
        self.assertTrue(False, '@login_required not implemented in the loader view class')
