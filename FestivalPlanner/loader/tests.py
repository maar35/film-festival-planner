import csv
import os
import re
import tempfile
from datetime import timedelta
from http import HTTPStatus

from django.test import RequestFactory
from django.urls import reverse

import festivals.models
import theaters
from festival_planner import debug_tools
from festival_planner.tools import initialize_log, unset_log, CSV_DIALECT
from festivals.tests import create_festival, mock_base_festival_mnemonic
from films.models import FilmFanFilmRating, Film
from films.tests import create_film, ViewsTestCase, get_request_with_session, new_film
from films.views import FilmsView
from loader.forms.loader_forms import FilmLoader, RatingLoader, CityDumper, TheaterDumper, ScreenDumper, \
    get_subsection_id
from loader.views import SectionsLoaderView, get_festival_row, RatingsLoaderView, NewTheaterDataView, \
    SaveRatingsView
from sections.models import Section, Subsection
from theaters.models import City, new_cities_path, new_theaters_path, new_screens_path, Theater, Screen


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
        get_subsection_id(film),
        duration_str,
        film.medium_category,
        film.reviewer or '',
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
        festivals.models.TEST_BASE_DIR = tempfile.TemporaryDirectory()
        self.create_planner_data_dir()
        self.create_festival_data_dir()

        # Define a placeholder for a view for derived classes.
        self.loader_view = None

    def tearDown(self):
        super().tearDown()
        self.city.delete()
        self.festival.delete()
        festivals.models.clean_base_dir()
        if self.loader_view:
            del self.loader_view

    @staticmethod
    def create_festival(city, start_data_str, end_date_str):
        return create_festival(mock_base_festival_mnemonic(), city, start_data_str, end_date_str)

    def create_planner_data_dir(self):
        os.makedirs(self.festival.planner_data_dir())

    def create_festival_data_dir(self):
        os.makedirs(self.festival.festival_data_dir())

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
        debug_tools.SUPPRESS_DEBUG_PRINT = True

        # Set up POST data for the ratings.html template.
        self.post_data = {f'ratings_{self.festival.id}': ['Load'], 'import_mode': []}

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
            subsection=None)
        film_1 = Film(
            festival=self.festival,
            film_id=other_film_id,
            seq_nr=11,
            title='Die dumme Gans',
            duration=timedelta(minutes=188),
            subsection=None)

        with open(self.festival.films_file(), 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, dialect=CSV_DIALECT)
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

    def pre_execute_loading_reviewer(self, reviewer=None):
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)

        film = new_film(3320, 'The Space Cowboys', 109)
        film.reviewer = reviewer or ' '

        with open(self.festival.films_file(), 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, dialect=CSV_DIALECT)
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film))

        self.post_data['import_mode'] = ['on']
        post_response = self.client.post(reverse('loader:ratings'), self.post_data)

        # Act.
        redirect_response = self.client.get(post_response.url)

        # assert.
        self.assert_reading_from_file(get_response, post_response, redirect_response)
        self.assertContains(redirect_response, 'film records read')

    def test_admin_can_load_films(self):
        """
        A file with correct film records can be loaded by an admin fan.
        """
        # Arrange.
        request = self.get_admin_request()
        get_response = self.arrange_get_get_response(request)

        film_1 = create_film(1, 'Der Berliner', 103, festival=self.festival)
        film_2 = create_film(2, 'Angst und Freude', 15, festival=self.festival)
        films_file = self.festival.films_file()
        with open(films_file, 'w', newline='') as csvfile:
            film_writer = csv.writer(csvfile, dialect=CSV_DIALECT)
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
        with open(self.festival.films_file(), 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, dialect=CSV_DIALECT)
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film))

        rating_1 = create_rating(film, self.admin_fan, 10)
        rating_2 = create_rating(film, self.regular_fan, 8)
        with open(self.festival.ratings_file(), 'w', newline='') as csv_ratings_file:
            rating_writer = csv.writer(csv_ratings_file, dialect=CSV_DIALECT)
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
        with open(self.festival.films_file(), 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, dialect=CSV_DIALECT)
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film))

        rating_1 = create_rating(film, self.admin_fan, 10)
        _ = create_rating(film, self.regular_fan, 8)
        with open(self.festival.ratings_file(), 'w', newline='') as csv_ratings_file:
            rating_writer = csv.writer(csv_ratings_file, dialect=CSV_DIALECT)
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

        films_file = self.festival.films_file()
        with open(films_file, 'w', newline='') as csvfile:
            film_writer = csv.writer(csvfile, dialect=CSV_DIALECT)
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
        films_file = self.festival.films_file()
        with open(films_file, 'w', newline='') as csvfile:
            film_writer = csv.writer(csvfile, dialect=CSV_DIALECT)
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
        with open(self.festival.films_file(), 'w', newline='') as csv_films_file:
            film_writer = csv.writer(csv_films_file, dialect=CSV_DIALECT)
            film_writer.writerow(FilmLoader.expected_header)
            film_writer.writerow(serialize_film(film))

        rating_1 = create_rating(film, self.admin_fan, 6)
        rating_2 = create_rating(film, self.regular_fan, 9)
        with open(self.festival.ratings_file(), 'w', newline='') as csv_ratings_file:
            rating_writer = csv.writer(csv_ratings_file, dialect=CSV_DIALECT)
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

    def test_reviewer_can_be_loaded_blank(self):
        """
        The reviewer of a film can't be a blank string.
        Unfortunately this would be accepted when creating a film directly,
        but reviewers are only fed into the database with the loader.
        Also see test films.FilmModelTests.test_reviewer_can_be_created_blank.
        """
        # Arrange and Act,
        test_reviewer = ' '
        self.pre_execute_loading_reviewer(reviewer=test_reviewer)

        # Assert,
        result_film = Film.films.get(film_id=3320, festival=self.festival)
        self.assertNotEqual(result_film.reviewer, test_reviewer)
        self.assertIsNone(result_film.reviewer)

    def test_reviewer_can_be_loaded_empty(self):
        """
        The reviewer of a film can't be an empty string.
        The loader should convert such value to None.
        """
        # Arrange and Act,
        test_reviewer = ''
        self.pre_execute_loading_reviewer(reviewer=test_reviewer)

        # Assert,
        result_film = Film.films.get(film_id=3320, festival=self.festival)
        self.assertNotEqual(result_film.reviewer, test_reviewer)
        self.assertIsNone(result_film.reviewer)

    def test_reviewer_can_be_loaded_unstripped(self):
        """
        The loader should strip the reviewer of a film.
        """
        # Arrange and Act,
        test_reviewer = ' Mats Matters'
        self.pre_execute_loading_reviewer(reviewer=test_reviewer)

        # Assert,
        result_film = Film.films.get(film_id=3320, festival=self.festival)
        self.assertNotEqual(result_film.reviewer, test_reviewer)
        self.assertIsNotNone(result_film.reviewer)
        self.assertEqual(result_film.reviewer, test_reviewer.strip())

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
        save_view = SaveRatingsView()
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
        post_response = SaveRatingsView.as_view()(post_request)

        # Assert.
        redirect_request = get_request_with_session(request)
        redirect_response = FilmsView.as_view()(redirect_request)
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

    @staticmethod
    def arrange_serialize_subsection(subsection):
        fields = [
            str(subsection.subsection_id),
            str(subsection.section.id),
            subsection.name,
            subsection.description,
            subsection.url,
        ]
        return fields

    def arrange_write_sections(self, sections):
        serialized_sections = [self.arrange_serialize_section(s) for s in sections]
        sections_file = self.festival.sections_file()
        with open(sections_file, 'w', newline='') as csvfile:
            section_writer = csv.writer(csvfile, dialect=CSV_DIALECT)
            section_writer.writerows(serialized_sections)

    def arrange_write_subsection(self, subsections):
        serialized_subsections = [ self.arrange_serialize_subsection(s) for s in subsections]
        subsections_file = self.festival.subsections_file()
        with open(subsections_file, 'w', newline='') as csvfile:
            subsection_writer = csv.writer(csvfile, dialect=CSV_DIALECT)
            subsection_writer.writerows(serialized_subsections)

    def test_admin_can_load_sections(self):
        """
        A file with correct section records can be loaded by an admin fan.
        """
        # Arrange.
        get_response = self.get_get_response(self.get_admin_request())
        section_1 = self.arrange_create_section('Hot items', 'HotPink')
        section_2 = self.arrange_create_section('Longs', 'Blue')
        self.arrange_write_sections([section_1, section_2])

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
        A file with correct section records can't be loaded by a non-admin fan.
        """
        # Arrange.
        section = self.arrange_create_section('Japanese Pink Movies', 'Pink')
        self.arrange_write_sections([section])

        # Act.
        get_response = self.get_get_response(self.get_regular_fan_request())

        # Assert.
        self.assertEqual(get_response.status_code, HTTPStatus.OK)
        self.assertContains(get_response, 'Not allowed')
        self.assertNotContains(get_response, 'Pick a festival to load section data from')

    def test_duplicate_subsections_not_accepted(self):
        # Arrange.
        _ = self.get_admin_request()
        sections = Section.sections.all()
        sections.delete()
        section = self.arrange_create_section('Markets', 'Blue')
        subsection_1 = Subsection(festival=section.festival, subsection_id=13, section=section,
                                  name='Bear Markets', description='When everything goes down')
        subsection_2 = Subsection(festival=section.festival, subsection_id=13, section=section,
                                  name='On the Fish Market', description="Something's smelly here")

        self.arrange_write_sections([section])
        self.arrange_write_subsection([subsection_1, subsection_2])

        # Act.
        post_response = self.client.post(reverse('loader:sections'), self.post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertContains(redirect_response, 'Section Overview')
        self.assertContains(redirect_response, '1 section records read')
        self.assertContains(redirect_response, '2 subsection records read')
        self.assertContains(redirect_response, '1 subsection records created')
        self.assertContains(redirect_response, '1 subsection records updated')
        subsection_count = Subsection.subsections.count()
        self.assertEqual(subsection_count, 1)
        self.assertContains(redirect_response, subsection_2.name)
        self.assertNotContains(redirect_response, subsection_1.name)
        self.assertContains(redirect_response, section.name)

    def test_duplicate_subsections_other_section_not_accepted(self):
        # Arrange.
        _ = self.get_admin_request()
        sections = Section.sections.all()
        sections.delete()
        section_1 = self.arrange_create_section('Markets', 'Blue')
        section_2 = self.arrange_create_section('Food', 'Green')
        subsection_1 = Subsection(festival=section_1.festival, subsection_id=13, section=section_1,
                                  name='Bear Markets', description='When everything goes down')
        subsection_2 = Subsection(festival=section_2.festival, subsection_id=13, section=section_2,
                                  name='On the Fish Market', description="Something's smelly here")

        self.arrange_write_sections([section_1, section_2])
        self.arrange_write_subsection([subsection_1, subsection_2])

        # Act.
        post_response = self.client.post(reverse('loader:sections'), self.post_data)
        redirect_response = self.client.get(post_response.url)

        # Assert.
        self.assertEqual(post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(redirect_response.status_code, HTTPStatus.OK)
        self.assertContains(redirect_response, 'Section Overview')
        self.assertContains(redirect_response, '2 section records read')
        self.assertContains(redirect_response, '2 subsection records read')
        self.assertContains(redirect_response, '1 subsection records created')
        self.assertContains(redirect_response, '1 subsection records updated')
        subsection_count = Subsection.subsections.count()
        self.assertEqual(subsection_count, 1)
        self.assertContains(redirect_response, subsection_2.name)
        self.assertNotContains(redirect_response, subsection_1.name)
        self.assertContains(redirect_response, section_2.name)
        self.assertNotContains(redirect_response, section_1.name)


class TheaterDataLoaderViewsTests(LoaderViewsTests):
    def setUp(self):
        super().setUp()
        theaters.models.TEST_COMMON_DATA_DIR = tempfile.TemporaryDirectory()
        NewTheaterDataView.state_nr = 0
        self.session = None

    def tearDown(self):
        super().tearDown()
        theaters.models.clean_common_data_dir()
        unset_log(self.session)

    def arrange_session_with_log(self, by_admin=True):
        if by_admin:
            request = self.get_admin_request()
        else:
            request = self.get_regular_fan_request()
        self.session = request.session
        initialize_log(self.session)

    def arrange_new_screens(self, session):
        city = City(name='Groningen', country='nl', city_id=50)
        theater = Theater(city=city, parse_name='Kriterion', abbreviation='kr-', priority=1, theater_id=2001)
        screen_1 = Screen(theater=theater, abbreviation='gr', parse_name='Kriterion Grote Zaal',
                          address_type=3, screen_id=1)
        screen_2 = Screen(theater=theater, abbreviation='kl', parse_name='Kriterion Kleine Zaal',
                          address_type=3, screen_id=2)

        self.expected_words_new_screens = ['Groningen', 'Kriterion', 'Kleine Zaal', 'Grote Zaal']
        self.expected_words_theaters = ['Groningen', 'Kriterion', 'kr-', '2']

        _ = CityDumper(session).dump_objects(new_cities_path(), objects=[city])
        _ = TheaterDumper(session).dump_objects(new_theaters_path(), objects=[theater])
        _ = ScreenDumper(session).dump_objects(new_screens_path(), objects=[screen_1, screen_2])

    def assert_load_results(self, response, by_admin=True):
        self.assertEqual(response.status_code, HTTPStatus.OK)
        if by_admin:
            self.assertContains(response, 'Load results')
            self.assertContains(response, '1 city records read')
            self.assertContains(response, '1 theater records read')
            self.assertContains(response, '2 screen records read')
        else:
            self.assertNotContains(response, 'Load results')
        self.assert_words_visible(response, self.expected_words_new_screens, by_admin=by_admin)

    def assert_words_visible(self, response, expected_words, by_admin=True):
        for word in expected_words:
            if by_admin:
                self.assertContains(response, word)
            else:
                self.assertNotContains(response, word)

    def test_regular_user_cannot_load_new_screens(self):
        # Arrange.
        self.arrange_session_with_log(by_admin=False)
        self.arrange_new_screens(self.session)

        # Act.
        response = self.client.get(reverse('loader:new_screens'))

        # Assert.
        self.assert_load_results(response, by_admin=False)

    def test_admin_can_load_new_screens(self):
        # Arrange.
        self.arrange_session_with_log(by_admin=True)
        self.arrange_new_screens(self.session)

        # Act.
        response = self.client.get(reverse('loader:new_screens'))

        # Assert.
        self.assert_load_results(response)

    def test_admin_can_insert_new_theater_data(self):
        # Arrange.
        self.arrange_session_with_log(by_admin=True)
        self.arrange_new_screens(self.session)
        get_response = self.client.get(reverse('loader:new_screens'))
        self.assert_load_results(get_response)

        # Act.
        cities_post_response = self.client.post(reverse('loader:new_screens'))
        cities_redirect_response = self.client.get(cities_post_response.url)
        theaters_post_response = self.client.post(reverse('loader:new_screens'))
        theaters_redirect_response = self.client.get(theaters_post_response.url)
        screens_post_response = self.client.post(reverse('loader:new_screens'))
        screens_redirect_response = self.client.get(screens_post_response.url)

        # Assert.
        self.assertEqual(cities_post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(theaters_post_response.status_code, HTTPStatus.FOUND)
        self.assertEqual(screens_post_response.status_code, HTTPStatus.FOUND)
        self.assertContains(cities_redirect_response, 'Cities insert results')
        self.assertContains(theaters_redirect_response, 'Theaters insert results')
        self.assertContains(screens_redirect_response, 'Screens insert results')
        self.assert_words_visible(screens_redirect_response, self.expected_words_theaters)
