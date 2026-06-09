import csv

from festival_planner.debug_tools import pr_debug
from festival_planner.tools import CSV_DIALECT, add_log
from films.forms.film_forms import PickRating
from films.models import minutes_str, FilmFanFilmRating
from films.views import FilmDetailView
from screenings.models import Screening, Attendance, Ticket
from theaters.models import Theater, Screen, City


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
    FOR_AGENDA = True
    TAIL_BY_AGENDA = {True: ['url', 'notes'], False: ['attendants', 'status', 'ratings', 'filmscreening_count']}
    manager = None
    header = ['title', 'location', 'start_time', 'end_time'] + TAIL_BY_AGENDA[FOR_AGENDA]

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
        ] + ([
            screening.film.url,
            self._get_notes(obj),
        ] if self.FOR_AGENDA else [
            obj['attendants'],
            obj['status_label'],
            obj['ratings'],
            obj['filmscreening_count'],
        ])

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


class RatingDumper(BaseDumper):
    manager = FilmFanFilmRating.film_ratings
    header = ['filmid', 'filmfan', 'rating', 'original_rating']

    def __init__(self, session):
        super().__init__(session, 'rating', self.manager, self.header)
        PickRating.invalidate_festival_caches(session)

    def object_row(self, rating):
        yield [rating.film.film_id, rating.film_fan.name, rating.rating, rating.original_rating]


class AttendanceDumper(BaseDumper):
    manager = Attendance.attendances
    header = [
        'filmid', 'screenid', 'starttime', 'movablestarttime', 'movableendtime', 'combinedfilmid',
        'autoplanned', 'blocked', 'Maarten,Adrienne,Manfred,Piggel,Rijk,Geeth', 'ticketsbought', 'soldout'
    ]
    TRUE = 'WAAR'
    FALSE = 'ONWAAR'
    ATTENDANCE_FIELD_INDEX = 8
    field_by_bool = {True: TRUE, False: FALSE}
    fan_names = header[ATTENDANCE_FIELD_INDEX].split(',')

    def __init__(self, session):
        super().__init__(session, 'attendance', self.manager, self.header)

    def object_row(self, attendance):
        attending_fans = [self.field_by_bool[attendance.fan.name == fan_name] for fan_name in self.fan_names]
        ticket_bought = Ticket.tickets.filter(screening=attendance.screening, fan=attendance.fan)
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
