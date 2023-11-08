import csv
import os
import re
import shutil
import tempfile
from datetime import timedelta
from http import HTTPStatus
from unittest import skip

# from FilmFestivalPlanner.FilmFestivalLoader.Shared import planner_interface as planner
from django.test import RequestFactory
from django.urls import reverse

from festival_planner.tools import pr_debug
from festivals.tests import create_festival, mock_base_festival_mnemonic
from films.models import FilmFanFilmRating, Film
from films.tests import create_film, ViewsTestCase, get_request_with_session
from films.views import SaveView, films
from loader.forms.loader_forms import FilmLoader, RatingLoader
from loader.views import SectionsLoaderView, get_festival_row, RatingsLoaderView, NewTheaterDataView, \
    NewTheaterDataListView
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
        super().setUp()

        # Set up a festival. Needed to render any page in the app.
        self.city = City.cities.create(city_id=1, name='Berlin', country='de')
        self.festival = self.create_festival(self.city, '2023-02-16', '2023-02-26')

        # Create working directories for films and ratings.
        self.create_planner_data_dir()
        self.create_festival_data_dir()

        # Define a placeholder for a view for derived  classes.
        self.loader_view = None

    def tearDown(self):
        super().tearDown()
        self.city.delete()
        self.remove_festival_data()
        if self.loader_view:
            del self.loader_view

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

    def get_get_response(self, get_request, view=None):
        view = view or self.loader_view
        view.setup(get_request)
        view.queryset = view.get_queryset() if hasattr(view, 'get_queryset') else view.queryset
        context = view.get_context_data()
        return view.render_to_response(context)


class RatingLoaderViewsTests(LoaderViewsTests):

    def setUp(self):
        super().setUp()
        self.ratings_loader_view = RatingsLoaderView()

        # Set up POST data for the ratings.html template.
        self.post_data = {f'ratings_{self.festival.id}': ['Load'], 'import_mode': []}

    def tearDown(self):
        super(RatingLoaderViewsTests, self).tearDown()

    def arrange_get_get_response(self, get_request):
        self.ratings_loader_view.setup(get_request)
        context = self.ratings_loader_view.get_context_data()
        return self.ratings_loader_view.render_to_response(context)

    def arrange_new_and_existing_films(self):

        common_film_id = 1
        other_film_id = 2
        _ = create_film(common_film_id, 'Der schlaue Fuchs', 92, festival=self.festival, seq_nr=10)
        film_2 = Film(
            festival=self.festival,
            film_id=common_film_id,
            seq_nr=12,
            title='Der schlaue Fuchs',
            duration=timedelta(minutes=88),
            subsection='')
        film_1 = Film(
            festival=self.festival,
            film_id=other_film_id,
            seq_nr=11,
            title='Die dumme Gans',
            duration=timedelta(minutes=188),
            subsection='')

        with open(self.festival.films_file, 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, delimiter=';', quotechar='"')
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film_1))
            film_writer.writerow(serialize_film(film_2))

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
        get_response = self.arrange_get_get_response(request)

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
        self.assertContains(redirect_response, 'No ratings will be effected')
        self.assertNotContains(redirect_response, 'not found')
        self.assertNotContains(redirect_response, 'Bad value in file')
        self.assertNotContains(redirect_response, 'incompatible header')
        self.assertContains(redirect_response, '2 film records read')

    def test_admin_can_load_ratings(self):
        """
        A file with correct rating records can be loaded by an admin fan.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)

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

        self.post_data['import_mode'] = ['on']
        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, '1 film records read')
        self.assertNotContains(redirect_response, 'not found')
        self.assertNotContains(redirect_response, 'Bad value in file')
        self.assertNotContains(redirect_response, 'incompatible header')
        self.assertContains(redirect_response, 'existing rating objects saved')
        self.assertContains(redirect_response, '2 rating records read')

    def test_admin_can_replace_ratings_while_loading_films(self):
        """
        Existing ratings can be kept when loading films.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)

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

        self.post_data['import_mode'] = ['on']
        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, '1 film records read')
        self.assertNotContains(redirect_response, 'not found')
        self.assertNotContains(redirect_response, 'Bad value in file')
        self.assertNotContains(redirect_response, 'incompatible header')
        self.assertContains(redirect_response, '2 existing rating objects saved')
        self.assertContains(redirect_response, '1 rating records updated')

    def test_integrity_error_rolls_back_all_updates(self):
        """
        When loading new films, all updates and inserts are rolled back at an integrity error.
        """
        # Set up.
        FilmLoader.key_fields = ['festival', 'seq_nr', 'film_id']   # Not unique together.

        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)
        self.arrange_new_and_existing_films()

        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, 'No ratings will be effected.')
        self.assertContains(redirect_response, '2 film records read')
        self.assertContains(redirect_response, 'database rolled back')
        self.assertNotContains(redirect_response, 'Die dumme Gans')
        self.assertContains(redirect_response, 'Der schlaue Fuchs')
        self.assertContains(redirect_response, '1:32')    # Original duration.
        self.assertEqual(Film.films.count(), 1)

        # Tear down.
        FilmLoader.key_fields = ['festival', 'film_id']   # Original, unique together.

    def test_no_integrity_error_when_keys_conform_unique_together(self):
        """
        When loading a new film with existing unique key combination, film is updated and nothing is rolled back.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)
        self.arrange_new_and_existing_films()

        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, 'No ratings will be effected.')
        self.assertContains(redirect_response, '2 film records read')
        self.assertNotContains(redirect_response, 'database rolled back')
        self.assertContains(redirect_response, 'Die dumme Gans')
        self.assertContains(redirect_response, 'Der schlaue Fuchs')
        self.assertContains(redirect_response, '1:28')    # New duration.
        self.assertEqual(Film.films.count(), 2)

    def test_regular_user_cannot_load_rating_data(self):
        """
        A non-admin fan can't load data.
        """
        # Arrange.
        request = self.get_regular_fan_request()

        # Act.
        get_response = self.arrange_get_get_response(request)

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, 'Not allowed')
        self.assertNotContains(get_response, '#Ratings on file')

    def test_admin_cannot_load_incompatible_film_file(self):
        """
        An admin fan can't load an incompatible films file.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)

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
        self.assertContains(redirect_response, 'No film records read')
        self.assertNotContains(redirect_response, 'rating records read')

    def test_admin_cannot_load_corrupt_film(self):
        """
        An admin fan can't load a films file with bad data.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)

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
        self.assertContains(redirect_response, 'No film records read')
        self.assertNotContains(redirect_response, 'rating records read')

    def test_admin_cannot_load_corrupt_rating(self):
        """
        An admin fan can't load a ratings file with bad data.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)

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

        self.post_data['import_mode'] = ['on']
        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, 'film records read')
        self.assertContains(redirect_response, 'Bad value in file')
        self.assertContains(redirect_response, 'No rating records read')

    def test_admin_can_save_ratings(self):
        """
        An admin fan can save ratings.
        """
        # Arrange.
        film_1 = create_film(1, 'Ich bin ein Hamburger', 86, festival=self.festival)
        film_2 = create_film(2, 'Böse Banken', 127, festival=self.festival)
        _ = create_rating(film_1, self.admin_fan, 5)
        _ = create_rating(film_1, self.regular_fan, 4)
        _ = create_rating(film_2, self.regular_fan, 8)

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
        self.assertNotContains(get_response, 'existing rating objects saved ')
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertURLEqual(post_response.url, reverse('films:films'))
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertContains(redirect_response, 'Save results')
        self.assertContains(redirect_response, '3 existing rating objects saved')
        log_re = re.compile(r'\b3 existing rating objects saved in.*?csv')
        self.assertRegex(redirect_response.content.decode('utf-8'), log_re)


class SectionLoaderViewsTests(LoaderViewsTests):
    max_section_id = 0

    def setUp(self):
        super().setUp()

        # Get a good feeling about writing on festival files.
        self.assertEqual(mock_base_festival_mnemonic(), 'Berlinale')
        self.assertEqual(mock_base_festival_mnemonic(), self.festival.base.mnemonic)

        # Set up a loader view including the mock festival.
        self.loader_view = SectionsLoaderView()
        self.loader_view.queryset = self.loader_view.get_queryset()
        self.festival.id = max([row['id'] for row in self.loader_view.queryset]) + 1
        self.festival.save()
        self.loader_view.queryset.append(get_festival_row(self.festival))

        # Set up POST data for the sections.html template.
        self.post_data = {f'{self.festival.id}': ['Load']}

    def tearDown(self):
        super().tearDown()

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
        A file with correct section records can be loaded by an admin fan.
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

    def test_regular_user_can_not_load_sections(self):
        """
        A file with correct section records can't be loaded by an non-admin fan.
        """
        # Arrange.
        section = self.arrange_create_section('Japanese Pink Movies', 'Pink')
        sections_file = self.festival.sections_file
        with open(sections_file, 'w', newline='') as csvfile:
            section_writer = csv.writer(csvfile, delimiter=';', quotechar='"')
            section_writer.writerow(self.arrange_serialize_section(section))

        # Act.
        get_response = self.get_get_response(self.get_regular_fan_request())

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, 'Not allowed')
        self.assertNotContains(get_response, 'Pick a festival to load section data from')


class TheaterDataLoaderViewsTests(LoaderViewsTests):
    def setUp(self):
        super().setUp()
        self.temp_dir = tempfile.TemporaryDirectory()
        # self.festival_data = planner.FestivalData(self.temp_dir.name)
        self.loader_view = NewTheaterDataView()

    def tearDown(self):
        super().tearDown()
        self.temp_dir.cleanup()

    # def arrange_new_screens(self):
    #     data = self.festival_data
    #     city_name = 'Groningen'
    #     theater_name = 'Kriterion'
    #     screen_1 = data.get_screen(city_name, 'Kriterion Grote Zaal', theater_parse_name=theater_name)
    #     screen_2 = data.get_screen(city_name, 'Kriterion Kleine Zaal', theater_parse_name=theater_name)
    #     screen_1.abbr = 'krgr'
    #     screen_2.abbr = 'krkl'
    #     data.write_new_cities()
    #     data.write_new_theaters()
    #     data.write_new_screens()

    def assert_load_results(self, response, by_admin=True):
        self.assertEqual(response.status_code, HTTPStatus.OK)
        self.assertContains(response, 'Load results')
        self.assertContains(response, '1 city records read')
        self.assertContains(response, '1 theater records read')
        self.assertContains(response, '2 screen records read')
        content_keywords = ['Groningen', 'Kriterion', 'Kleine Zaal']
        for word in content_keywords:
            if by_admin:
                self.assertContains(response, word)
            else:
                self.assertNotContains(response, word)

    @skip("Importing planner interface doesn't work anymore")
    def test_regular_user_cannot_load_new_screens(self):
        # Arrange.
        # self.arrange_new_screens()

        # Act.
        get_response = self.get_get_response(self.get_regular_fan_request(), view=NewTheaterDataListView())

        # Assert.
        self.assert_load_results(get_response, by_admin=False)

    @skip("Importing planner interface doesn't work anymore")
    def test_admin_can_load_new_screens(self):
        # Arrange.
        # self.arrange_new_screens()

        # Act.
        get_response = self.get_get_response(self.get_admin_request(), view=NewTheaterDataListView())

        # Assert.
        self.assert_load_results(get_response)

    @skip("No time to get it working for the time being")
    def test_admin_can_insert_new_theater_data(self):
        # Arrange.
        # self.arrange_new_screens()
        get_request = self.get_admin_request()
        get_response = self.get_get_response(get_request, view=NewTheaterDataListView())
        self.assert_load_results(get_response)

        # Act.
        post_cities_response = self.client.post(reverse('loader:new_screens'))
        post_cities_response.user = self.admin_user
        post_cities_response.session = get_request.session
        get_theaters_response = self.get_get_response(get_request, view=NewTheaterDataListView())
        response = get_response.render()

        # Assert.
        self.assertEqual(post_cities_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(get_theaters_response.status_code, HTTPStatus.OK)
        pr_debug(f'\n\n{response=}\n')
        self.assertContains(get_theaters_response, 'Cities insert results')
