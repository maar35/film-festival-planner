import inspect
import os

from django.db import models
from django.db.models.fields.related_descriptors import ReverseManyToOneDescriptor
from django.forms import Form, SlugField

from authentication.models import FilmFan
from availabilities.models import Availabilities
from festival_planner.debug_tools import timed_method
from festival_planner.tools import initialize_log, add_log
from festivals.config import Config
from festivals.models import Festival, FestivalBase
from films.models import Film, FilmFanFilmRating, FilmFanFilmVote
from loader.forms.dumper_forms import BaseDumper
from loader.forms.loader_forms import CityDumper
from screenings.models import Screening, Attendance, Ticket
from sections.models import Section, Subsection
from theaters.models import Theater, Screen

COMMON_DATA_DIR = os.path.expanduser(f'~/{Config().config["Paths"]["CommonDataDirectory"]}')
BACKUP_DATA_DIR = os.path.join(COMMON_DATA_DIR, 'Backups')
CITIES_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'cities.csv')
FESTIVAL_BASES_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'festival_bases.csv')
FESTIVALS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'festivals.csv')
SECTIONS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'sections.csv')
SUBSECTIONS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'subsections.csv')
FILMS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'films.csv')
FILM_FANS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'film_fans.csv')
RATINGS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'ratings.csv')
VOTES_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'votes.csv')
AVAILABILITIES_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'availabilities.csv')
THEATERS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'theaters.csv')
SCREENS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'screens.csv')
SCREENINGS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'screenings.csv')
ATTENDANCES_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'attendances.csv')
TICKETS_BACKUP_PATH = os.path.join(BACKUP_DATA_DIR, 'tickets.csv')


def get_subsection_id(film):
    return film.subsection.subsection_id if film.subsection else ''


def get_main_title_id(film):
    return film.main_title.id if film.main_title else ''


class RatingDataBackupForm(Form):
    dummy_field = SlugField(required=False)

    @staticmethod
    @timed_method
    def backup_film_data(session):
        initialize_log(session, 'Backup')
        add_log(session, 'Backing up film database data.')
        _ = RatingBackupDumper(session).dump_objects(RATINGS_BACKUP_PATH)
        _ = VoteBackupDumper(session).dump_objects(VOTES_BACKUP_PATH)
        _ = FanBackupDumper(session).dump_objects(FILM_FANS_BACKUP_PATH)
        _ = FilmBackupDumper(session).dump_objects(FILMS_BACKUP_PATH)
        _ = SubsectionBackupDumper(session).dump_objects(SUBSECTIONS_BACKUP_PATH)
        _ = SectionBackupDumper(session).dump_objects(SECTIONS_BACKUP_PATH)
        _ = FestivalBackupDumper(session).dump_objects(FESTIVALS_BACKUP_PATH)
        _ = FestivalBaseBackupDumper(session).dump_objects(FESTIVAL_BASES_BACKUP_PATH)
        _ = CityBackupDumper(session).dump_objects(CITIES_BACKUP_PATH)


class ScreeningDataBackupForm(Form):
    dummy_field = SlugField(required=False)

    @staticmethod
    @timed_method
    def backup_screening_data(session):
        initialize_log(session, 'Backup')
        add_log(session, 'Backing up screening database data.')
        _ = AvailabilityBackupDumper(session).dump_objects(AVAILABILITIES_BACKUP_PATH)
        _ = TheaterBackupDumper(session).dump_objects(THEATERS_BACKUP_PATH)
        _ = ScreenBackupDumper(session).dump_objects(SCREENS_BACKUP_PATH)
        _ = ScreeningBackupDumper(session).dump_objects(SCREENINGS_BACKUP_PATH)
        _ = AttendanceBackupDumper(session).dump_objects(ATTENDANCES_BACKUP_PATH)
        _ = TicketBackupDumper(session).dump_objects(TICKETS_BACKUP_PATH)


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


class SectionBackupDumper(BaseDumper):
    manager = Section.sections
    header = ['id', 'festival_mnemonic', 'festival_year', 'festival_edition', 'section_id', 'name', 'color']

    def __init__(self, session):
        super().__init__(session, 'section', self.manager, self.header)

    def object_row(self, section):
        yield [
            section.id,
            section.festival.base.mnemonic,
            section.festival.year,
            section.festival.edition,
            section.section_id,
            section.name,
            section.color,
        ]


class SubsectionBackupDumper(BaseDumper):
    manager = Subsection.subsections
    header = [
        'id',
        'festival_mnemonic',
        'festival_year',
        'festival_edition',
        'section_id',
        'name',
        'description',
        'url',
    ]

    def __init__(self, session):
        super().__init__(session, 'subsection', self.manager, self.header)

    def object_row(self, subsection):
        yield [
            subsection.id,
            subsection.section.festival.base.mnemonic,
            subsection.section.festival.year,
            subsection.section.festival.edition,
            subsection.section.section_id,
            subsection.name,
            subsection.description,
            subsection.url,
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
        'main_title',
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
            get_main_title_id(film),
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
    header = [
        'id', 'festival_mnemonic', 'festival_year', 'festival_edition', 'film_id', 'fan', 'rating', 'original_rating'
    ]

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
            rating.original_rating,
        ]


class VoteBackupDumper(BaseDumper):
    manager = FilmFanFilmVote.film_votes
    header = ['id', 'festival_mnemonic', 'festival_year', 'festival_edition', 'film_id', 'fan', 'vote']

    def __init__(self, session):
        super().__init__(session, 'vote', self.manager, self.header)

    def object_row(self, vote):
        yield [
            vote.id,
            vote.film.festival.base.mnemonic,
            vote.film.festival.year,
            vote.film.festival.edition,
            vote.film.film_id,
            vote.film_fan.name,
            vote.vote,
        ]


def get_attrs(class_, skip_fields=None):
    def _strip(attr):
        def _getmembers_predicate(a):
            skip_classes = (ReverseManyToOneDescriptor, models.manager.Manager, models.enums.ChoicesMeta, type)
            return inspect.ismethod(a) or inspect.isfunction(a) or a.__class__ in skip_classes

        # Reject attribute based on the first letter of the name.
        if attr[0] == '_':
            return False

        # Reject attribute based on inspect() and class.
        attributes_ = inspect.getmembers(class_, _getmembers_predicate)
        if attr in [k for (k, v) in attributes_]:
            return False

        # Attribute passes if is not a "__xyz__" builtin.
        if not attr.startswith('__') and not attr.endswith('__'):
            return True

    attrs = [a for a in class_.__dict__.keys() if _strip(a)]
    for skip_field in skip_fields if skip_fields else []:
        attrs.remove(skip_field)
    return attrs


class BaseBackupDumper(BaseDumper):
    manager = None
    class_ = None
    object_name = None
    user_fields = None
    header = None

    def __init__(self, session):
        super().__init__(session, self.object_name, self.manager, self.header)

    def object_row(self, obj):
        yield [getattr(obj, fld, '_') for fld in self.user_fields]


class AvailabilityBackupDumper(BaseBackupDumper):
    manager = Availabilities.availabilities
    class_ = Availabilities
    object_name = 'availability'
    user_fields = get_attrs(class_)
    header = user_fields

    def __init__(self, session):
        super().__init__(session)


class TheaterBackupDumper(BaseBackupDumper):
    manager = Theater.theaters
    class_ = Theater
    object_name = 'theater'
    user_fields = get_attrs(class_, skip_fields=['color_by_priority'])
    header = user_fields

    def __init__(self, session):
        super().__init__(session)


class ScreenBackupDumper(BaseBackupDumper):
    manager = Screen.screens
    class_ = Screen
    object_name = 'screen'
    user_fields = get_attrs(class_)
    header = user_fields

    def __init__(self, session):
        super().__init__(session)


class ScreeningBackupDumper(BaseBackupDumper):
    manager = Screening.screenings
    class_ = Screening
    object_name = 'screening'
    skip_fields = [
        'color_pair_by_screening_status',
        'color_pair_selected_by_screening_status',
        'color_warning_by_screening_status',
        'interesting_rating_color_attends_film_background',
        'interesting_rating_color_should_sell_background',
        'uninteresting_rating_color',
    ]
    user_fields = get_attrs(class_, skip_fields=skip_fields)
    header = user_fields

    def __init__(self, session):
        super().__init__(session)


class AttendanceBackupDumper(BaseBackupDumper):
    manager = Attendance.attendances
    class_ = Attendance
    object_name = 'attendance'
    user_fields = get_attrs(class_)
    header = user_fields

    def __init__(self, session):
        super().__init__(session)


class TicketBackupDumper(BaseBackupDumper):
    manager = Ticket.tickets
    class_ = Ticket
    object_name = 'ticket'
    user_fields = get_attrs(class_)
    header = user_fields

    def __init__(self, session):
        super().__init__(session)
