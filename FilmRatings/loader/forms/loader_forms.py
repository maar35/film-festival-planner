import csv
import datetime

from django import forms

from FilmRatings.tools import initialize_log, add_log
from festivals.models import current_festival
from film_list.models import Film, FilmFanFilmRating, FilmFan
from sections.models import Section, Subsection
from theaters.models import Theater, theaters_path, City, cities_path


class RatingLoaderForm(forms.Form):
    keep_ratings = forms.BooleanField(
        label='Save existing ratings before loading',
        required=False,
        initial=True
    )

    @staticmethod
    def load_rating_data(session, festival, keep_ratings):
        initialize_log(session)
        if FilmLoader(session, festival, keep_ratings).load_films():
            RatingLoader(session, festival, keep_ratings).load_ratings()


class LoadTheatersForm(forms.Form):
    dummy_field = forms.SlugField(required=False)

    @staticmethod
    def load_theater_data(session):
        initialize_log(session)
        if CityLoader(session).load_objects():
            TheaterLoader(session).load_objects()


class BaseLoader:
    """
    Base class for loading objects such as films or ratings from CSV files.
    """
    expected_header = None

    def __init__(self, session, file_required=True):
        """
        Initialize the member variables
        :param session: Session to store the log as a cookie
        :param file_required: Boolean to indicate whether the input file is required
        """
        self.session = session
        self.file_required = file_required
        self.object_name = None
        self.objects_on_file = None

    def read_objects(self, objects_file, object_list):
        """
        Member method to be used by derived classes to read objects from files
        :param objects_file: The CSV file to read the objects form
        :param object_list: A list to receive the objects read
        :return: Whether reading objects was successful
        """
        # Initialize.
        self.objects_on_file = 0

        # Read the objects form the file.
        self.add_log(f'Reading from file {objects_file}.')
        try:
            with open(objects_file, newline='') as csvfile:
                object_reader = csv.reader(csvfile, delimiter=';', quotechar='"')

                # Read the header.
                if not self.check_header(objects_file, object_reader):
                    return False

                # Read the data rows.
                for row in object_reader:
                    self.objects_on_file += 1
                    object_read = self.read_row(row)
                    if object_read is not None:
                        object_list.append(object_read)

        except FileNotFoundError:
            if self.file_required:
                self.add_log(f'File {objects_file} not found.')
            return False

        except ValueError:
            self.add_log(f'Bad value in file {objects_file}.')
            return False

        return True

    def check_header(self, file, reader):
        if self.expected_header is None:
            return True
        header = reader.__next__()
        if header != self.expected_header:
            self.add_log(f'File {file} has an incompatible header.')
            return False
        return True

    def read_row(self, row):
        """
        "Virtual" method to read one object from file
        :param row: Line from the file being read
        :return: The object read, None if no object could be read
        """
        return None

    def delete_objects(self, objects):
        deleted_object_count, deleted_count_by_object_type = objects.delete()
        if deleted_object_count == 0:
            self.add_log(f'No existing {self.object_name}s need to be deleted.')
        for (object_type, deleted_count) in deleted_count_by_object_type.items():
            self.add_log(f'{deleted_count} existing {object_type.split(".")[-1]}s deleted.')

    def add_log(self, text):
        add_log(self.session, text)


class FilmLoader(BaseLoader):
    expected_header = ['seqnr', 'filmid', 'sort', 'title', 'titlelanguage', 'section', 'duration', 'mediumcategory', 'url']

    def __init__(self, session, festival, keep_ratings):
        super().__init__(session)
        self.festival = festival
        self.keep_ratings = keep_ratings
        self.object_name = 'film'
        self.films = None

    def load_films(self):
        # Read the films of the given festival.
        if not self.read_films():
            return False

        # Save ratings if the Keep Ratings flag is set.
        if self.keep_ratings:
            if not self.save_ratings(self.festival.ratings_cache):
                return False

        # Delete existing films of the given festival.
        existing_films = Film.films.filter(festival_id=self.festival.id)
        self.delete_objects(existing_films)

        # Load the new films.
        Film.films.bulk_create(self.films)
        self.add_log(f'{len(self.films)} films loaded.')

        return True

    def read_films(self):
        # Initialize.
        films_file = self.festival.films_file
        self.films = []

        # Read films from file.
        if not self.read_objects(films_file, self.films):
            return False

        # Add result statistics to the log.
        films_count = len(self.films)
        if films_count == 0:
            self.add_log(f'No films found in file{films_file}')
            return False
        self.add_log(f'{films_count} films read.')
        return True

    def read_row(self, row):
        seq_nr = int(row[0])
        film_id = int(row[1])
        film = Film(festival=self.festival, film_id=film_id, seq_nr=seq_nr)
        film.sort_title = row[2]
        film.title = row[3]
        film.title_language = row[4]
        film.subsection = row[5]
        film.duration = datetime.timedelta(minutes=int(row[6].rstrip("′")))
        film.medium_category = row[7]
        film.url = row[8]
        return film

    def save_ratings(self, file):
        festival = self.festival
        ratings = FilmFanFilmRating.fan_ratings.filter(film__festival_id=festival.id)

        try:
            with open(file, 'w', newline='') as csvfile:
                rating_writer = csv.writer(csvfile, delimiter=';', quotechar='"')
                rating_writer.writerow(RatingLoader.expected_header)
                for rating in ratings:
                    row = [rating.film.film_id, rating.film_fan.name, rating.rating]
                    rating_writer.writerow(row)
        except FileNotFoundError:
            self.add_log(f'File {file} not found.')
            return False
        else:
            self.add_log(f'{len(ratings)} existing ratings saved.')

        return True


class RatingLoader(BaseLoader):
    expected_header = ['filmid', 'filmfan', 'rating']

    def __init__(self, session, festival, keep_ratings):
        super().__init__(session, file_required=False)
        self.festival = festival
        self.keep_ratings = keep_ratings
        self.object_name = 'rating'
        self.ratings_file = self.festival.ratings_file
        self.ratings_cache = self.festival.ratings_cache
        self.ratings = None

    def load_ratings(self):
        # Read the ratings.
        if not self.read_ratings():
            return

        # Delete existing ratings.
        existing_ratings = FilmFanFilmRating.fan_ratings.filter(film__festival_id=self.festival.id)
        self.delete_objects(existing_ratings)

        # Load the new ratings.
        FilmFanFilmRating.fan_ratings.bulk_create(self.ratings)
        self.add_log(f'{len(self.ratings)} ratings loaded.')

    def read_ratings(self):
        # Initialize.
        ratings_file = self.ratings_cache if self.keep_ratings else self.ratings_file
        self.ratings = []

        # Read the ratings from file.
        if not self.read_objects(ratings_file, self.ratings):
            self.add_log('No ratings read.')
            return False

        # Log results
        self.add_log(f'{self.objects_on_file} ratings read, {len(self.ratings)} accepted.')
        return True

    def read_row(self, row):
        film_id = int(row[0])
        film_fan_name = row[1]
        rating_value = int(row[2])
        try:
            film = Film.films.get(festival_id=self.festival.id, film_id=film_id)
        except Film.DoesNotExist:
            self.add_log(f'Film not found: #{film_id}.')
            return None
        try:
            film_fan = FilmFan.film_fans.get(name=film_fan_name)
        except FilmFan.DoesNotExist:
            self.add_log(f'Fan not found: {film_fan_name}.')
            return None
        rating = FilmFanFilmRating(film=film, film_fan=film_fan)
        rating.rating = rating_value
        return rating


class SimpleLoader(BaseLoader):

    def __init__(self, session, object_name, object_manager, objects_file, festival=None):
        super().__init__(session)
        self.festival = festival
        self.object_name = object_name
        self.object_manager = object_manager
        self.objects_file = objects_file
        self.object_list = []

    def load_objects(self):
        # Read the objects of the given festival.
        if not self.read_objects_simple():
            return False

        # Delete existing objects (of the given festival).
        if self.festival:
            existing_objects = self.object_manager.filter(festival_id=self.festival.id)
        else:
            existing_objects = self.object_manager.all()
        self.delete_objects(existing_objects)

        # Load the new objects.
        self.object_manager.bulk_create(self.object_list)
        self.add_log(f'{len(self.object_list)} {self.object_name} records loaded.')

        return True

    def read_objects_simple(self):
        # Read objects from file.
        if not self.read_objects(self.objects_file, self.object_list):
            return False

        # Add result statistics to the log.
        object_count = len(self.object_list)
        if object_count == 0:
            self.add_log(f'No {self.object_name} records found in file {self.objects_file}')
            return False
        self.add_log(f'{object_count} {self.object_name} records read.')

        return True


class SectionLoader(SimpleLoader):

    def __init__(self, session, festival):
        manager = Section.sections
        file = festival.sections_file
        super().__init__(session, 'section', manager, file, festival)

    def read_row(self, row):
        section_id = int(row[0])
        name = row[1]
        color = row[2]
        section = Section(festival=self.festival, section_id=section_id, name=name, color=color)
        return section


class SubsectionLoader(SimpleLoader):

    def __init__(self, session, festival):
        manager = Subsection.subsections
        file = festival.subsections_file
        super().__init__(session, 'subsection', manager, file, festival)

    def read_row(self, row):
        subsection_id = int(row[0])
        section_id = int(row[1])
        name = row[2]
        description = row[3]
        url = row[4]
        try:
            section = Section.sections.get(festival_id=self.festival.id, section_id=section_id)
        except Section.DoesNotExist:
            self.add_log(f'Section not found: #{section_id}.')
            return None
        subsection = Subsection(festival=self.festival, subsection_id=subsection_id, section=section, name=name,
                                description=description, url=url)
        return subsection


class CityLoader(SimpleLoader):

    def __init__(self, session):
        manager = City.cities
        file = cities_path()
        super().__init__(session, 'city', manager, file)

    def read_row(self, row):
        city_id = int(row[0])
        name = row[1]
        country = row[2]
        city = City(city_id=city_id, name=name, country=country)
        return city


class TheaterLoader(SimpleLoader):

    def __init__(self, session):
        manager = Theater.theaters
        file = theaters_path()
        super().__init__(session, 'theater', manager, file)

    def read_row(self, row):
        theater_id = int(row[0])
        city_id = int(row[1])
        parse_name = row[2]
        abbreviation = row[3]
        priority = Theater.Priority(int(row[4]))
        try:
            city = City.cities.get(city_id=city_id)
        except City.DoesNotExist:
            self.add_log(f'City not found: #{city_id}.')
            return None
        theater = Theater(theater_id=theater_id, city=city, parse_name=parse_name, abbreviation=abbreviation,
                          priority=priority)
        return theater
