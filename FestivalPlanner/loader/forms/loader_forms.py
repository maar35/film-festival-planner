import csv
import datetime

from django import forms
from django.db import IntegrityError

from festival_planner.tools import initialize_log, add_log
from films.models import Film, FilmFanFilmRating, FilmFan
from sections.models import Section, Subsection
from theaters.models import Theater, theaters_path, City, cities_path


class RatingLoaderForm(forms.Form):
    import_mode = forms.BooleanField(
        label='Use import mode, all ratings are replaced',
        required=False,
        initial=False,
    )

    @staticmethod
    def load_rating_data(session, festival, import_mode=False):
        initialize_log(session)
        import_mode or add_log(session, 'No ratings will be effected.')
        if FilmLoader(session, festival, import_mode).load_objects():
            if import_mode:
                add_log(session, 'Import mode. Ratings will be replaced.')
                RatingLoader(session, festival).load_objects()


class TheaterLoaderForm(forms.Form):
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

    def read_objects(self, objects_file, values_list):
        """
        Member method to be used by derived classes to read objects from files
        :param objects_file: The CSV file to read the objects from
        :param values_list: A list to receive the objects read
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

                # Read the data records.
                for record in object_reader:
                    self.objects_on_file += 1
                    values_read = self.read_row(record)
                    if values_read:
                        values_list.append(values_read)

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


class SimpleLoader(BaseLoader):

    key_fields = []
    default_fields = []
    label_by_created = {
        True: 'created',
        False: 'updated',
        None: 'cause integrity error',
    }

    def __init__(self, session, object_name, object_manager, objects_file,
                 festival=None, festival_pk=None, file_required=True):
        super().__init__(session, file_required=file_required)
        self.object_name = object_name
        self.object_manager = object_manager
        self.objects_file = objects_file
        self.festival = festival
        self.festival_filter = None if festival is None else {festival_pk or 'festival__pk': self.festival.pk}
        self.records = []
        self.delete_disappeared_objects = True

    def load_objects(self):
        # Prepare statistics.
        objects_by_created = {}
        existing_object_set = set()
        updated_object_set = set()

        # Select the existing objects.
        if self.delete_disappeared_objects:
            if self.festival:
                existing_objects = self.object_manager.filter(**self.festival_filter)
            else:
                existing_objects = self.object_manager.all()
            existing_object_set = set(list(existing_objects))

        # Read the objects from the member file into the designated list.
        if not self.read_objects(self.objects_file, self.records):
            self.add_log(f'No {self.object_name} records read.')
            return False

        # Update objects and create ones when absent.
        for value_by_field in self.records:
            keys, defaults = self.pop_key_fields(value_by_field)

            # Update or create an object.
            try:
                affected_object, created = self.object_manager.update_or_create(**keys, defaults=defaults)
            except IntegrityError as e:
                created = None
                print(f'ERROR {e=} {keys=}')
            else:
                if not created:
                    updated_object_set.add(affected_object)

            # Update statistics.
            try:
                objects_by_created[created] += 1
            except KeyError:
                objects_by_created[created] = 1

        # Log the results.
        for created, count in objects_by_created.items():
            self.add_log(f'{count} {self.object_name} records {self.label_by_created[created]}.')

        # Delete objects that do not appear in the file.
        if self.delete_disappeared_objects:
            # Find existing objects that are not on the file.
            disappeared_object_set = existing_object_set - updated_object_set
            disappeared_pk_list = [obj.pk for obj in disappeared_object_set]
            disappeared_objects = existing_objects.filter(pk__in=disappeared_pk_list)

            # Delete disappeared objects from the database.
            self.delete_objects(disappeared_objects)

        return True

    def read_objects(self, objects_file, records):
        # Read objects from file.
        if not super().read_objects(objects_file, records):
            return False

        # Add result statistics to the log.
        object_count = len(records)
        if object_count == 0:
            self.add_log(f'No {self.object_name} records found in file {objects_file}')
            return False
        self.add_log(f'{object_count} {self.object_name} records read.')

        return True

    def pop_key_fields(self, value_by_field):
        value_by_key_field = {}
        value_by_default_field = {}
        for field, value in value_by_field.items():
            if field in self.key_fields:
                value_by_key_field[field] = value
            else:
                value_by_default_field[field] = value

        return value_by_key_field, value_by_default_field


class FilmLoader(SimpleLoader):
    expected_header = ['seqnr', 'filmid', 'sort', 'title', 'titlelanguage',
                       'section', 'duration', 'mediumcategory', 'url']
    key_fields = ['festival', 'seq_nr', 'film_id']
    manager = Film.films

    def __init__(self, session, festival, import_mode):
        super().__init__(session, 'film', self.manager, festival.films_file, festival=festival)
        self.festival = festival
        self.import_mode = import_mode
        self.delete_disappeared_objects = True

        # Save ratings if the import mode flag is set and all ratings
        # are replaced.
        if self.import_mode:
            _ = self.save_ratings(self.festival.ratings_cache)

    def read_row(self, row):
        seq_nr = int(row[0])
        film_id = int(row[1])
        sort_title = row[2]
        title = row[3]
        title_language = row[4]
        subsection = row[5]
        duration = datetime.timedelta(minutes=int(row[6].rstrip("′")))
        medium_category = row[7]
        url = row[8]

        value_by_field = {
            'festival': self.festival,
            'seq_nr': seq_nr,
            'film_id': film_id,
            'sort_title': sort_title,
            'title': title,
            'title_language': title_language,
            'subsection': subsection,
            'duration': duration,
            'medium_category': medium_category,
            'url': url,
        }
        return value_by_field

    def save_ratings(self, file):
        festival = self.festival
        ratings = FilmFanFilmRating.film_ratings.filter(film__festival_id=festival.id)

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
            self.add_log(f'{len(ratings)} existing ratings saved to {file}.')

        return True


class RatingLoader(SimpleLoader):
    expected_header = ['filmid', 'filmfan', 'rating']
    key_fields = ['film', 'film_fan']
    manager = FilmFanFilmRating.film_ratings

    def __init__(self, session, festival):
        file = festival.ratings_file
        super().__init__(session, 'rating', self.manager, file, file_required=False,
                         festival=festival, festival_pk='film__festival__pk')
        self.festival = festival
        self.delete_disappeared_objects = True

    def read_row(self, row):
        film_id = int(row[0])
        film_fan_name = row[1]
        rating = int(row[2])
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

        value_by_field = {
            'film': film,
            'film_fan': film_fan,
            'rating': rating,
        }
        return value_by_field


class SectionLoader(SimpleLoader):
    key_fields = ['section_id', 'festival']
    manager = Section.sections

    def __init__(self, session, festival):
        file = festival.sections_file
        super().__init__(session, 'section', self.manager, file, festival)

    def read_row(self, row):
        section_id = int(row[0])
        name = row[1]
        color = row[2]

        value_by_field = {
            'section_id': section_id,
            'festival': self.festival,
            'name': name,
            'color': color,
        }
        return value_by_field


class SubsectionLoader(SimpleLoader):
    key_fields = ['subsection_id', 'festival']
    manager = Subsection.subsections

    def __init__(self, session, festival):
        file = festival.subsections_file
        super().__init__(session, 'subsection', self.manager, file, festival)

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

        value_by_field = {
            'subsection_id': subsection_id,
            'festival': self.festival,
            'section': section,
            'name': name,
            'description': description,
            'url': url,
        }
        return value_by_field


class CityLoader(SimpleLoader):
    key_fields = ['city_id']
    manager = City.cities
    file = cities_path()

    def __init__(self, session):
        super().__init__(session, 'city', self.manager, self.file)

    def read_row(self, row):
        city_id = int(row[0])
        name = row[1]
        country = row[2]

        value_by_field = {
            'city_id': city_id,
            'name': name,
            'country': country,
        }
        return value_by_field


class TheaterLoader(SimpleLoader):
    key_fields = ['theater_id']
    manager = Theater.theaters
    file = theaters_path()

    def __init__(self, session):
        super().__init__(session, 'theater', self.manager, self.file)

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

        value_by_field = {
            'theater_id': theater_id,
            'city': city,
            'parse_name': parse_name,
            'abbreviation': abbreviation,
            'priority': priority,
        }
        return value_by_field
