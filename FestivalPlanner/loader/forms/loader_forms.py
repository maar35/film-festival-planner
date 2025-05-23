import csv
import datetime
import os

from django.db import IntegrityError, transaction
from django.forms import Form, BooleanField, SlugField

from authentication.models import FilmFan
from festival_planner.cache import FilmRatingCache
from festival_planner.debug_tools import pr_debug
from festival_planner.tools import initialize_log, add_log, CSV_DIALECT
from festivals.config import Config
from festivals.models import Festival, FestivalBase
from films.forms.film_forms import PickRating
from films.models import Film, FilmFanFilmRating, minutes_str
from films.views import FilmsView, FilmDetailView
from screenings.models import Screening, Attendance, Ticket
from sections.models import Section, Subsection
from theaters.models import Theater, theaters_path, City, cities_path, Screen, screens_path, cities_cache_path, \
    theaters_cache_path, screens_cache_path

COMMON_DATA_DIR = os.path.expanduser(f'~/{Config().config["Paths"]["CommonDataDirectory"]}')
BACKUP_DATA_DIR = os.path.join(COMMON_DATA_DIR, 'Backups')
CITIES_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'cities.csv')
FESTIVAL_BASES_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'festival_bases.csv')
FESTIVALS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'festivals.csv')
FILMS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'films.csv')
FILM_FANS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'film_fans.csv')
RATINGS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'ratings.csv')
FILMS_FILE_HEADER = Config().config['Headers']['FilmsFileHeader']


def get_subsection_id(film):
    return film.subsection.subsection_id if film.subsection else ''


class RatingLoaderForm(Form):
    import_mode = BooleanField(
        label='Use import mode, all ratings are replaced',
        required=False,
        initial=False,
    )

    @staticmethod
    def load_rating_data(session, festival, rating_queryset, rating_cachefile, import_mode=False):
        initialize_log(session)
        import_mode or add_log(session, 'No ratings will be loaded.')

        # Invalidate the cache associated with the current festival.
        PickRating.invalidate_festival_caches(session, FilmsView.unexpected_errors)

        # Save ratings if the import mode flag is set and all ratings
        # are replaced.
        if import_mode:
            _ = RatingDumper(session).dump_objects(rating_cachefile, rating_queryset)

        # Load films and, if applicable, ratings.
        if FilmLoader(session, festival).load_objects():
            if import_mode:
                add_log(session, 'Import mode. Ratings will be replaced.')
                RatingLoader(session, festival).load_objects()


class SingleTableDumperForm(Form):
    dummy_field = SlugField(required=False)

    @staticmethod
    def dump_data(session, festival, data_name, dumper_class, dumpfile, queryset):
        initialize_log(session, 'Dump')
        add_log(session, f'Dumping the {festival} {data_name}.')
        if not dumper_class(session).dump_objects(dumpfile, queryset):
            add_log(session, f'Failed to dump the {festival} {data_name}.')


class TheaterDataLoaderForm(Form):
    dummy_field = SlugField(required=False)

    @staticmethod
    def load_theater_data(session):
        initialize_log(session)

        # Cache the database data before it is overwritten.
        _ = CityDumper(session).dump_objects(cities_cache_path())
        _ = TheaterDumper(session).dump_objects(theaters_cache_path())
        _ = ScreenDumper(session).dump_objects(screens_cache_path())

        # Overwrite the festival data in the database.
        go_on = True
        if go_on:
            go_on = CityLoader(session).load_objects()
        if go_on:
            go_on = TheaterLoader(session).load_objects()
        if go_on:
            _ = ScreenLoader(session).load_objects()


class TheaterDataUpdateForm(Form):
    dummy_field = SlugField(required=False)

    @staticmethod
    def add_new_cities(session, new_cities):
        initialize_log(session, 'Cities insert')
        CityUpdater(session).add_new_objects(new_cities)

    @staticmethod
    def add_new_theaters(session, new_theaters):
        initialize_log(session, 'Theaters insert')
        TheaterUpdater(session).add_new_objects(new_theaters)

    @staticmethod
    def add_new_screens(session, new_screens):
        initialize_log(session, 'Screens insert')
        ScreenUpdater(session).add_new_objects(new_screens)


class TheaterDataDumperForm(Form):
    dummy_field = SlugField(required=False)

    @staticmethod
    def dump_theater_data(session):
        initialize_log(session, 'Dump')
        add_log(session, 'Dumping the theater database data.')
        CityDumper(session).dump_objects(cities_path())
        TheaterDumper(session).dump_objects(theaters_path())
        ScreenDumper(session).dump_objects(screens_path())


class RatingDataBackupForm(Form):
    dummy_field = SlugField(required=False)

    @staticmethod
    def backup_film_data(session):
        initialize_log(session, 'Backup')
        add_log(session, 'Backing up film database data.')
        _ = RatingBackupDumper(session).dump_objects(RATINGS_BACKUP_PATH)
        _ = FanBackupDumper(session).dump_objects(FILM_FANS_BACKUP_PATH)
        _ = FilmBackupDumper(session).dump_objects(FILMS_BACKUP_PATH)
        _ = FestivalBackupDumper(session).dump_objects(FESTIVALS_BACKUP_PATH)
        _ = FestivalBaseBackupDumper(session).dump_objects(FESTIVAL_BASES_BACKUP_PATH)
        _ = CityBackupDumper(session).dump_objects(CITIES_BACKUP_PATH)


class BaseLoader:
    """
    Base class for loading objects such as films or ratings from CSV files.
    """
    expected_header = None
    foreign_objects = None

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
                object_reader = csv.reader(csvfile, dialect=CSV_DIALECT)

                # Read the header.
                if not self.check_header(objects_file, object_reader):
                    return False

                # Read the data records.
                for record in object_reader:
                    self.objects_on_file += 1
                    row_generator = self.read_row(record)
                    for value_by_field in row_generator:
                        if value_by_field:
                            values_list.append(value_by_field)

        except FileNotFoundError:
            if self.file_required:
                self.add_log(f'File {objects_file} not found.')
            return False

        except ValueError as e:
            self.add_log(f'{e}. Bad value in file {objects_file}.')
            return False

        # Add result statistics to the log.
        object_count = len(values_list)
        if object_count == 0:
            self.add_log(f'No {self.object_name} records found in file {objects_file}')
            return False
        self.add_log(f'{object_count} {self.object_name} records read.')

        return True

    def check_header(self, file, reader):
        """Internal method to handle presence of a data header"""
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
        yield None

    def get_foreign_key(self, foreign_class, foreign_manager, **kwargs):
        """
        Member method to be used by derived classes to get an object to use as foreign key

        :param foreign_class: class of the foreign key object
        :param foreign_manager: Manager of the foreign key object class
        :param kwargs: Keyword arguments to crate the foreign key object

        """
        foreign_object = None
        object_str = foreign_class.__name__
        try:
            foreign_object = foreign_manager.get(**kwargs)
        except foreign_class.DoesNotExist:
            missing_attributes = []
            for attribute, value in kwargs.items():
                if self.foreign_objects:
                    try:
                        foreign_object = [obj for obj in self.foreign_objects if getattr(obj, attribute) == value][0]
                    except IndexError as e:
                        self.add_log(f'{e}: {object_str} with {attribute}={value} not in new foreign objects')
                        return None
                    except AttributeError as e:
                        self.add_log(f'{e}')
                        return None
                else:
                    missing_attributes.append(f'{attribute}={value}')
            if missing_attributes:
                attributes_str = ' and '.join(missing_attributes)
                self.add_log(f'{object_str} with {attributes_str} not found in database.')
                return None
        return foreign_object

    def get_value_by_field(self, obj):
        """
        "Virtual" method to return a value by field dictionary from the
        given object.
        """
        return None

    def construct_object(self, value_by_field):
        """
        "Virtual" method to return a new object from the given value by
        field dictionary.
        """
        return None

    def delete_objects(self, objects):
        """Facility method to delete given objects without questions"""
        deleted_object_count, deleted_count_by_object_type = objects.delete()
        if deleted_object_count == 0:
            self.add_log(f'No existing {self.object_name}s need to be deleted.')
        for (object_type, deleted_count) in deleted_count_by_object_type.items():
            self.add_log(f'{deleted_count} existing {object_type.split(".")[-1]}s deleted.')

    def add_log(self, text):
        """Shorthand method to add text to the current log"""
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
        self.value_by_field_list = []
        self.delete_disappeared_objects = True

    def load_objects(self):
        existing_object_set = set()
        updated_object_set = set()

        # Select the existing objects.
        existing_objects = None
        if self.delete_disappeared_objects:
            if self.festival:
                existing_objects = self.object_manager.filter(**self.festival_filter)
            else:
                existing_objects = self.object_manager.all()
            existing_object_set = set(list(existing_objects))

        # Read the objects from the member file into the designated list.
        if not self.read_objects(self.objects_file, self.value_by_field_list):
            self.add_log(f'No {self.object_name} records read.')
            return False

        # Update or create either all objects or none.
        transaction_committed = self.atomic_update_or_create(updated_object_set)

        # Delete objects that do not appear in the file.
        if self.delete_disappeared_objects and transaction_committed:
            # Find existing objects that are not on the file.
            disappeared_object_set = existing_object_set - updated_object_set
            disappeared_pk_list = [obj.pk for obj in disappeared_object_set]
            disappeared_objects = existing_objects.filter(pk__in=disappeared_pk_list)
            for obj in disappeared_objects:
                self.add_log(f'{obj=} will be deleted')

            # Delete disappeared objects from the database.
            self.delete_objects(disappeared_objects)

        # Allow subclasses to round up.
        self.finalize()

        return True

    def load_new_objects(self, target_object_list, foreign_objects=None):
        self.foreign_objects = foreign_objects

        # Get a list of value by field dictionaries from file.
        if not self.read_objects(self.objects_file, self.value_by_field_list):
            self.add_log(f'No {self.object_name} records read.')
            return False

        # Construct new objects from the value by field dictionary list.
        for value_by_field in self.value_by_field_list:
            new_object = self.construct_object(value_by_field)
            if new_object:
                target_object_list.append(new_object)
            else:
                raise ValueError(f"Couldn't construct new {self.object_name} object from {value_by_field}.")

        return True

    def atomic_update_or_create(self, updated_object_set):
        transaction_committed = False
        try:
            with transaction.atomic():
                self.update_or_create(updated_object_set)
                transaction_committed = True
        except IntegrityError as e:
            self.add_log(f'{e}: database rolled back.')
        return transaction_committed

    def update_or_create(self, updated_object_set):
        objects_by_created = {}

        # Update objects or create ones when absent.
        for value_by_field in self.value_by_field_list:
            keys, defaults = self.pop_key_fields(value_by_field)

            # Update or create an object.
            affected_object, created = self.object_manager.update_or_create(**keys, defaults=defaults)
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
        if not objects_by_created:
            self.add_log(f'No {self.object_name} records found.')

    def add_new_objects(self, object_list):
        dummy_set = set()
        value_by_field_list = []

        self.add_log(f'Inserting new {self.object_name} records.')
        for obj in object_list:
            value_by_field = self.get_value_by_field(obj)
            value_by_field_list.append(value_by_field)
        self.value_by_field_list = value_by_field_list
        self.atomic_update_or_create(dummy_set)

    def pop_key_fields(self, value_by_field):
        value_by_key_field = {}
        value_by_default_field = {}
        for field, value in value_by_field.items():
            if field in self.key_fields:
                value_by_key_field[field] = value
            else:
                value_by_default_field[field] = value

        return value_by_key_field, value_by_default_field

    def finalize(self):
        """
        "Virtual" method to allow derived classes to round things up.

        :return: None
        """
        return None


class FilmLoader(SimpleLoader):
    expected_header = FILMS_FILE_HEADER
    key_fields = ['festival', 'film_id']
    manager = Film.films

    def __init__(self, session, festival):
        super().__init__(session, 'film', self.manager, festival.films_file(), festival=festival)
        self.festival = festival
        self.delete_disappeared_objects = True

    def read_row(self, row):
        seq_nr = int(row[0])
        film_id = int(row[1])
        sort_title = row[2]
        title = row[3]
        title_language = row[4]
        subsection_id = int(row[5]) if row[5].strip() else None
        duration = datetime.timedelta(minutes=int(row[6].rstrip("′")))
        medium_category = row[7]
        reviewer = (row[8]).strip() or None
        url = row[9]

        subsection = None
        if subsection_id:
            """
            Relies on uniqueness of subsection_id together with section.festival,
            which is guaranteed ion the Loader.
            """
            subsection = Subsection.subsections.filter(section__festival_id=self.festival.id,
                                                       subsection_id=subsection_id
                                                       ).first()

        value_by_field = {
            'festival': self.festival,
            'seq_nr': seq_nr,
            'film_id': film_id,
            'sort_title': sort_title,
            'title': title,
            'title_language': title_language,
            'subsection': subsection or None,
            'duration': duration,
            'medium_category': medium_category,
            'reviewer': reviewer,
            'url': url,
        }
        yield value_by_field


class RatingLoader(SimpleLoader):
    expected_header = ['filmid', 'filmfan', 'rating']
    key_fields = ['film', 'film_fan']
    manager = FilmFanFilmRating.film_ratings

    def __init__(self, session, festival):
        file = festival.ratings_file()
        super().__init__(session, 'rating', self.manager, file, file_required=False,
                         festival=festival, festival_pk='film__festival__pk')
        self.festival = festival
        self.delete_disappeared_objects = True

    def read_row(self, row):
        film_id = int(row[0])
        film_fan_name = row[1]
        rating = int(row[2])

        film = self.get_foreign_key(Film, Film.films, **{'festival_id': self.festival.id, 'film_id': film_id})
        if not film:
            yield None

        film_fan = self.get_foreign_key(FilmFan, FilmFan.film_fans, **{'name': film_fan_name})
        if not film_fan:
            yield None

        value_by_field = {
            'film': film,
            'film_fan': film_fan,
            'rating': rating,
        }
        yield value_by_field


class SectionLoader(SimpleLoader):
    key_fields = ['section_id', 'festival']
    manager = Section.sections

    def __init__(self, session, festival):
        file = festival.sections_file()
        super().__init__(session, 'section', self.manager, file, festival=festival)

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
        yield value_by_field


class SubsectionLoader(SimpleLoader):
    key_fields = ['subsection_id', 'section']
    manager = Subsection.subsections

    def __init__(self, session, festival):
        file = festival.subsections_file()
        super().__init__(session, 'subsection', self.manager, file,
                         festival=festival, festival_pk='section__festival__pk')

    def read_row(self, row):
        subsection_id = int(row[0])
        section_id = int(row[1])
        name = row[2]
        description = row[3]
        url = row[4]

        kwargs = {'festival_id': self.festival.id, 'section_id': section_id}
        section = self.get_foreign_key(Section, Section.sections, **kwargs)
        if not section:
            yield None

        value_by_field = {
            'subsection_id': subsection_id,
            'section': section,
            'name': name,
            'description': description,
            'url': url,
        }
        yield value_by_field


class CityLoader(SimpleLoader):
    key_fields = ['city_id']
    manager = City.cities
    file = cities_path()

    def __init__(self, session, file=None):
        file = file or self.file
        super().__init__(session, 'city', self.manager, file)

    def read_row(self, row):
        city_id = int(row[0])
        name = row[1]
        country = row[2]

        value_by_field = {
            'city_id': city_id,
            'name': name,
            'country': country,
        }
        yield value_by_field

    def construct_object(self, value_by_field):
        city = City(**value_by_field)
        return city


class TheaterLoader(SimpleLoader):
    key_fields = ['theater_id']
    manager = Theater.theaters
    file = theaters_path()

    def __init__(self, session, file=None):
        file = file or self.file
        super().__init__(session, 'theater', self.manager, file)

    def read_row(self, row):
        theater_id = int(row[0])
        city_id = int(row[1])
        parse_name = row[2]
        abbreviation = row[3]
        priority = Theater.Priority(int(row[4]))

        city = self.get_foreign_key(City, City.cities, **{'city_id': city_id})
        if not city:
            yield None

        value_by_field = {
            'theater_id': theater_id,
            'city': city,
            'parse_name': parse_name,
            'abbreviation': abbreviation,
            'priority': priority,
        }
        yield value_by_field

    def construct_object(self, value_by_field):
        theater = Theater(**value_by_field)
        return theater


class ScreenLoader(SimpleLoader):
    key_fields = ['screen_id']
    manager = Screen.screens
    file = screens_path()

    def __init__(self, session, file=None):
        file = file or self.file
        super().__init__(session, 'screen', self.manager, file)

    def read_row(self, row):
        screen_id = int(row[0])
        theater_id = int(row[1])
        parse_name = row[2]
        abbreviation = row[3]
        address_type = Screen.ScreenAddressType(int(row[4]))

        theater = self.get_foreign_key(Theater, Theater.theaters, **{'theater_id': theater_id})
        if not theater:
            yield None

        value_by_field = {
            'screen_id': screen_id,
            'theater': theater,
            'parse_name': parse_name,
            'abbreviation': abbreviation,
            'address_type': address_type,
        }
        yield value_by_field

    def construct_object(self, value_by_field):
        screen = Screen(**value_by_field)
        return screen


class ScreeningLoader(SimpleLoader):
    expected_header = ['film_id', 'screen_id', 'start_time', 'end_time', 'combination_id',
                       'subtitles', 'qanda', 'extra', 'sold_out']
    alternative_header = expected_header[:-1]
    key_fields = ['film', 'screen', 'start_dt']
    manager = Screening.screenings

    def __init__(self, session, festival, festival_pk=None):
        file = festival.screenings_file()
        super().__init__(session, 'screening', self.manager, file, festival=festival, festival_pk=festival_pk)
        self._check_header()
        self.delete_disappeared_objects = True
        initialize_log(session)

    def read_row(self, row):
        film_id = int(row[0])
        screen_id = int(row[1])
        start_dt = datetime.datetime.fromisoformat(row[2]).replace(tzinfo=None)
        end_dt = datetime.datetime.fromisoformat(row[3]).replace(tzinfo=None)
        combination_id = int(row[4]) if row[4] else None
        subtitles = row[5]
        q_and_a = True if row[6] else False
        _ = row[7]      # extra
        if len(self.expected_header) == 7:
            _ = row[8]  # sold_out

        film = self.get_foreign_key(Film, Film.films, **{'festival': self.festival, 'film_id': film_id})
        screen = self.get_foreign_key(Screen, Screen.screens, **{'screen_id': screen_id})
        combination_program = None
        if combination_id is not None:
            kwargs = {'festival': self.festival, 'film_id': combination_id}
            combination_program = Film.films.filter(**kwargs).first()
        try:
            existing_screening = Screening.screenings.get(film=film, screen=screen, start_dt=start_dt)
        except Screening.DoesNotExist:
            auto_planned = False
        else:
            auto_planned = existing_screening.auto_planned

        if not film or not screen:
            yield None

        value_by_field = {
            'film': film,
            'screen': screen,
            'start_dt': start_dt,
            'end_dt': end_dt,
            'combination_program': combination_program or None,
            'subtitles': subtitles,
            'q_and_a': q_and_a,
            'auto_planned': auto_planned,
        }
        yield value_by_field

    @staticmethod
    def get_header(path):
        try:
            with open(path, newline='') as csvfile:
                reader = csv.reader(csvfile, dialect=CSV_DIALECT)
                header = reader.__next__()
        except FileNotFoundError:
            header = None
        return header

    def _check_header(self):
        header = self.get_header(self.objects_file)
        if header == self.expected_header:
            pass
        elif header == self.alternative_header:
            self.expected_header = self.alternative_header


class AttendanceLoader(SimpleLoader):
    TRUE = 'WAAR'
    ATTENDANCE_FIELD_INDEX = 8
    expected_header = [
        'filmid', 'screenid', 'starttime', 'movablestarttime', 'movableendtime', 'combinedfilmid',
        'autoplanned', 'blocked', 'Maarten,Adrienne,Manfred,Piggel,Rijk,Geeth', 'ticketsbought', 'soldout'
    ]
    key_fields = ['fan', 'screening']
    object_name = 'attendance'
    manager = Attendance.attendances
    fan_names = expected_header[ATTENDANCE_FIELD_INDEX].split(',')

    def __init__(self, session, festival, festival_pk):
        file = festival.screening_info_file()
        festival_pk = 'screening__film__festival__pk'
        super().__init__(session, self.object_name, self.manager, file, festival=festival, festival_pk=festival_pk)
        self.unknown_screenings = 0
        initialize_log(session)

    def read_row(self, row):
        film_id = row[0]
        screen_id = row[1]
        start_dt = datetime.datetime.fromisoformat(row[2]).replace(tzinfo=None)
        _ = row[3]      # movable_start_time
        _ = row[4]      # movable_end_time
        _ = row[5]      # combined_film_id
        _ = row[6]      # auto_planned
        _ = row[7]      # blocked
        fan_attendances = (Maarten, Adrienne, Manfred, Piggel, Rijk, Geeth) = row[8].split(',')
        tickets_bought = row[9] == self.TRUE
        _ = row[10]     # sold_out

        film = self.get_foreign_key(Film, Film.films, **{'festival': self.festival, 'film_id': film_id})
        screen = self.get_foreign_key(Screen, Screen.screens, **{'screen_id': screen_id})
        screening_kwargs = {'film': film, 'screen': screen, 'start_dt': start_dt}
        screening = self.get_foreign_key(Screening, Screening.screenings, **screening_kwargs)
        attendance_props_by_fan_name = {}
        for i, fan_name in enumerate(self.fan_names):
            try:
                fan = FilmFan.film_fans.get(name=fan_name)
            except FilmFan.DoesNotExist:
                pass
            else:
                fan_attendance = fan_attendances[i] == self.TRUE
                if fan_attendance:
                    attendance_props_by_fan_name[fan_name] = {
                        'fan': fan,
                        'attendance': fan_attendance,
                    }

        if not screening:
            self.unknown_screenings += 1
            yield None

        if self.object_name == 'ticket' and not tickets_bought:
            yield None

        for props in attendance_props_by_fan_name.values():
            value_by_field = {
                'screening': screening,
                'fan': props['fan'],
            }
            yield value_by_field

    def finalize(self):
        self.add_log(f'{self.unknown_screenings} unknown screenings.')


class TicketLoader(AttendanceLoader):
    object_name = 'ticket'
    manager = Ticket.tickets


class CityUpdater(SimpleLoader):
    key_fields = CityLoader.key_fields
    manager = CityLoader.manager
    file = None

    def __init__(self, session):
        super().__init__(session, 'city', self.manager, self.file)

    def get_value_by_field(self, obj):
        value_by_field = {
            'city_id': obj.city_id,
            'name': obj.name,
            'country': obj.country,
        }
        return value_by_field


class TheaterUpdater(SimpleLoader):
    key_fields = TheaterLoader.key_fields
    manager = TheaterLoader.manager
    file = None

    def __init__(self, session):
        super().__init__(session, 'theater', self.manager, self.file)

    def get_value_by_field(self, obj):
        value_by_field = {
            'theater_id': obj.theater_id,
            'city': obj.city,
            'parse_name': obj.parse_name,
            'abbreviation': obj.abbreviation,
            'priority': obj.priority,
        }
        return value_by_field


class ScreenUpdater(SimpleLoader):
    key_fields = ScreenLoader.key_fields
    manager = ScreenLoader.manager
    file = None

    def __init__(self, session):
        super().__init__(session, 'screen', self.manager, self.file)

    def get_value_by_field(self, obj):
        value_by_field = {
            'screen_id': obj.screen_id,
            'theater': obj.theater,
            'parse_name': obj.parse_name,
            'abbreviation': obj.abbreviation,
            'address_type': obj.address_type,
        }
        return value_by_field


class BaseDumper:
    """
    Base class for dumping objects to CSV files.
    """

    def __init__(self, session, object_name, manager, header=None):
        self.session = session
        self.object_name = object_name
        self.manager = manager
        self.header = header

    def dump_objects(self, file, objects=None):
        objects = objects or self.manager.all()
        self.add_log(f'Dumping {self.object_name} data.')
        try:
            with open(file, 'w', newline='') as csvfile:
                csv_writer = csv.writer(csvfile, dialect=CSV_DIALECT)
                if self.header:
                    csv_writer.writerow(self.header)
                for obj in objects:
                    row_generator = self.object_row(obj)
                    for row in row_generator:
                        csv_writer.writerow(row)
        except PermissionError as e:
            self.add_log(f'{e}: File {file} could not be written.')
            return False
        else:
            self.add_log(f'{len(objects)} existing {self.object_name} objects saved in {file}.')

        return True

    def object_row(self, obj):
        """
        "Virtual" method to dump one object to file

        :obj: The object to be dumped.
        :return: List of object attributes to be written
        """
        yield []

    def add_log(self, text):
        add_log(self.session, text)


class CityDumper(BaseDumper):
    manager = City.cities

    def __init__(self, session):
        super().__init__(session, 'city', self.manager)

    def object_row(self, city):
        yield [city.city_id, city.name, city.country]


class TheaterDumper(BaseDumper):
    manager = Theater.theaters

    def __init__(self, session):
        super().__init__(session, 'theater', self.manager)

    def object_row(self, theater):
        yield [
            theater.theater_id,
            theater.city.city_id,
            theater.parse_name,
            theater.abbreviation,
            theater.priority,
        ]


class ScreenDumper(BaseDumper):
    manager = Screen.screens

    def __init__(self, session):
        super().__init__(session, 'screen', self.manager)

    def object_row(self, screen):
        try:
            row = [
                screen.screen_id,
                screen.theater.theater_id,
                screen.parse_name,
                screen.abbreviation,
                screen.address_type,
            ]
        except Theater.DoesNotExist as e:
            pr_debug(f'{e}: {screen.screen_id=}, {screen.parse_name=}')
            return
        yield row


class CalendarDumper(BaseDumper):
    manager = None
    header = ['title', 'location', 'start_time', 'end_time', 'url', 'notes']

    def __init__(self, session):
        super().__init__(session, 'calendar', self.manager, header=self.header)

    def object_row(self, obj):
        dt_fmt = '%d-%m-%Y %H:%M'
        screening = obj['screening']
        yield [
            f"{screening.film.title} - {screening.screen}",
            screening.screen.theater.parse_name,
            screening.start_dt.strftime(dt_fmt),
            screening.end_dt.strftime(dt_fmt),
            screening.film.url,
            self._get_notes(obj),
        ]

    @staticmethod
    def _get_notes(obj):
        separator = '|'
        status = Screening.ScreeningStatus.ATTENDS
        screening = obj['screening']
        fans_rating_str, film_rating_str, color = screening.film_rating_data(status)
        notes = [
            f"Film duration: {minutes_str(screening.film.duration)}",
            f"Screening duration: {minutes_str(screening.end_dt - screening.start_dt)}",
            f"Attendants: {obj['attendants']}",
            f"Ratings: {fans_rating_str} ({film_rating_str})",
            '',
            FilmDetailView.get_description(screening.film) or '',
        ]
        return separator.join(notes)


class CityBackupDumper(CityDumper):

    def __init__(self, session):
        super().__init__(session)
        self.header = ['city_id', 'name', 'country']


class FestivalBaseBackupDumper(BaseDumper):
    manager = FestivalBase.festival_bases
    header = ['mnemonic', 'name', 'image', 'city_id']

    def __init__(self, session):
        super().__init__(session, 'festival base', self.manager, self.header)

    def object_row(self, base):
        yield [
            base.mnemonic,
            base.name,
            base.image,
            base.home_city.city_id,
        ]


class FestivalBackupDumper(BaseDumper):
    manager = Festival.festivals
    header = ['mnemonic', 'year', 'edition', 'start_date', 'end_date', 'color']

    def __init__(self, session):
        super().__init__(session, 'festival', self.manager, self.header)

    def object_row(self, festival):
        yield [
            festival.base.mnemonic,
            festival.year,
            festival.edition,
            festival.start_date,
            festival.end_date,
            festival.festival_color,
        ]


class FilmBackupDumper(BaseDumper):
    manager = Film.films
    header = [
        'festival_mnemonic',
        'festival_year',
        'festival_edition',
        'film_id',
        'seq_nr',
        'sort_title',
        'title',
        'title_language',
        'subsection',
        'duration',
        'medium_category',
        'reviewer',
        'url',
    ]

    def __init__(self, session):
        super().__init__(session, 'film', self.manager, self.header)

    def object_row(self, film):
        yield [
            film.festival.base.mnemonic,
            film.festival.year,
            film.festival.edition,
            film.film_id,
            film.seq_nr,
            film.sort_title,
            film.title,
            film.title_language,
            get_subsection_id(film),
            film.duration,
            film.medium_category,
            film.reviewer,
            film.url,
        ]


class FanBackupDumper(BaseDumper):
    manager = FilmFan.film_fans
    header = ['id', 'name', 'seq_nr', 'is_admin']

    def __init__(self, session):
        super().__init__(session, 'filmfan', self.manager, self.header)

    def object_row(self, fan):
        yield [fan.id, fan.name, fan.seq_nr, fan.is_admin]


class RatingBackupDumper(BaseDumper):
    manager = FilmFanFilmRating.film_ratings
    header = ['id', 'festival_mnemonic', 'festival_year', 'festival_edition', 'film_id', 'fan', 'rating']

    def __init__(self, session):
        super().__init__(session, 'rating', self.manager, self.header)

    def object_row(self, rating):
        yield [
            rating.id,
            rating.film.festival.base.mnemonic,
            rating.film.festival.year,
            rating.film.festival.edition,
            rating.film.film_id,
            rating.film_fan.name,
            rating.rating,
        ]


class RatingDumper(BaseDumper):
    manager = FilmFanFilmRating.film_ratings
    header = RatingLoader.expected_header

    def __init__(self, session):
        super().__init__(session, 'rating', self.manager, self.header)
        PickRating.invalidate_festival_caches(session)

    def object_row(self, rating):
        yield [rating.film.film_id, rating.film_fan.name, rating.rating]


class AttendanceDumper(BaseDumper):
    manager = Attendance.attendances
    header = AttendanceLoader.expected_header
    TRUE = AttendanceLoader.TRUE
    FALSE = 'ONWAAR'
    field_by_bool = {True: TRUE, False: FALSE}
    fan_names = AttendanceLoader.fan_names

    def __init__(self, session):
        super().__init__(session, 'attendance', self.manager, self.header)

    def object_row(self, attendance):
        attending_fans = [self.field_by_bool[attendance.fan.name == fan_name] for fan_name in self.fan_names]
        ticket_bought = Ticket.tickets.filter(screening=attendance.sceening, fan=attendance.fan)
        field_by_index = {
            0: attendance.screening.film.film_id,
            1: attendance.screening.screen.screen_id,
            2: attendance.screening.start_dt.isoformat(timespec='minutes'),
            3: '',      # movable_start_time
            4: '',      # movable_end_time
            5: '',      # combined_film_id
            6: '',      # auto_planned
            7: '',      # blocked
            8: ','.join(attending_fans),
            9: self.TRUE if ticket_bought else self.FALSE,
            10: '',     # sold_out
        }
        yield field_by_index.values()


class TicketDumper(BaseDumper):
    manager = Ticket.tickets
    header = ['film_id', 'screen_id', 'start_dt', 'fan']

    def __init__(self, session):
        super().__init__(session, 'ticket', self.manager, self.header)

    def object_row(self, ticket):
        yield [
            ticket.screening.film.film_id,
            ticket.screening.screen.screen_id,
            ticket.screening.start_dt.isoformat(timespec='minutes'),
            ticket.fan.name,
        ]
