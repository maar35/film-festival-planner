import datetime
import tempfile
import unittest

from Shared.parse_tools import FileKeeper
from Shared.planner_interface import Film, FilmInfo
import Shared.application_tools as app_tools


class BaseTestCase(unittest.TestCase):
    festival = 'Riga IFF'
    year = 2000
    file_keeper = None

    def setUp(self):
        super().setUp()
        app_tools.SUPPRESS_INFO_PRINTS = True
        self.temp_dir = tempfile.TemporaryDirectory()
        self.file_keeper = FileKeeper(self.festival, self.year, basedir=self.temp_dir.name)

    def tearDown(self):
        super().tearDown()
        self.temp_dir.cleanup()


class BaseFilmTestCase(BaseTestCase):
    film_id = 0
    festival_data = None    # Overwrite in derived class.

    def add_test_film(self, title=None, minutes=0, url=None, description=None):
        self.film_id += 1

        # Add a film from the parameters.
        film = self.festival_data.create_film(title, url)
        film.duration = datetime.timedelta(minutes=minutes)
        film.medium_category = 'films'
        self.festival_data.films.append(film)

        # Add film info.
        article = ''
        film_info = FilmInfo(self.film_id, description, article)
        self.festival_data.filminfos.append(film_info)


class TestFilm(Film):
    def __init__(self, film_id, title, url, minutes, description, festival_data):
        festival_data.film_seqnr += 1
        Film.__init__(self, festival_data.film_seqnr, film_id, title, url)
        self.duration = datetime.timedelta(minutes=minutes)
        self.medium_category = 'films'
        self.description = description
