import datetime

from django.db import models

from authentication.models import FilmFan
from festivals.config import Config
from films.models import Film
from theaters.models import Screen

CONSTANTS_CONFIG = Config().config['Constants']
WALK_TIME_SAME_THEATER = datetime.timedelta(minutes=CONSTANTS_CONFIG['WalkMinutesSameTheater'])
TRAVEL_TIME_OTHER_THEATER = datetime.timedelta(minutes=CONSTANTS_CONFIG['TravelMinutesOtherTheater'])


def color_pair(color, background):
    return {'color': color, 'background': background}


COLOR_PAIR_TRANSPARANT = color_pair(None, None)
COLOR_PAIR_OFF_BLACK = color_pair('orange', None)
COLOR_PAIR_RED = color_pair('white', 'rgb(176, 0, 38)')
COLOR_PAIR_BLUE = color_pair('yellow', 'rgb(0, 38, 176)')
COLOR_PAIR_YELLOW = color_pair('black', 'yellow')
COLOR_PAIR_GREY = color_pair('black', 'rgb(79, 79, 79)')
COLOR_PAIR_DARKGREY = color_pair('darkgrey', 'rgb(38, 38, 38)')
COLOR_PAIR_PURPLE = color_pair('white', 'rgb(176, 0, 176)')

COLOR_PAIR_FREE = COLOR_PAIR_TRANSPARANT
COLOR_PAIR_UNAVAILABLE = COLOR_PAIR_OFF_BLACK
COLOR_PAIR_ATTENDS = COLOR_PAIR_RED
COLOR_PAIR_FRIEND_ATTENDS = COLOR_PAIR_BLUE
COLOR_PAIR_ATTENDS_FILM = COLOR_PAIR_YELLOW
COLOR_PAIR_TIME_OVERLAP = COLOR_PAIR_GREY
COLOR_PAIR_NO_TRAVEL_TIME = COLOR_PAIR_DARKGREY
COLOR_PAIR_NEEDS_TICKETS = COLOR_PAIR_PURPLE


class Screening(models.Model):
    """
    Screenings table, represents events where a given film is screened
    on a given screen at specific period in time.
    """
    class ScreeningStatus(models.IntegerChoices):
        FREE = 0,
        UNAVAILABLE = 1,
        ATTENDS = 2,
        FRIEND_ATTENDS = 3,
        ATTENDS_FILM = 4,
        TIME_OVERLAP = 5,
        NO_TRAVEL_TIME = 6,
        NEEDS_TICKETS = 7,

    # Define color dictionary.
    color_pair_by_screening_status = {
        ScreeningStatus.FREE: COLOR_PAIR_FREE,
        ScreeningStatus.UNAVAILABLE: COLOR_PAIR_UNAVAILABLE,
        ScreeningStatus.ATTENDS: COLOR_PAIR_ATTENDS,
        ScreeningStatus.FRIEND_ATTENDS: COLOR_PAIR_FRIEND_ATTENDS,
        ScreeningStatus.ATTENDS_FILM: COLOR_PAIR_ATTENDS_FILM,
        ScreeningStatus.TIME_OVERLAP: COLOR_PAIR_TIME_OVERLAP,
        ScreeningStatus.NO_TRAVEL_TIME: COLOR_PAIR_NO_TRAVEL_TIME,
        ScreeningStatus.NEEDS_TICKETS: COLOR_PAIR_NEEDS_TICKETS,
    }

    # Define the fields.
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE)
    start_dt = models.DateTimeField()
    end_dt = models.DateTimeField()
    combination_program = models.ForeignKey(Film, null=True, on_delete=models.SET_NULL,
                                            related_name='combined_screening')
    subtitles = models.CharField(max_length=24)
    q_and_a = models.BooleanField()

    # Define a manager.
    screenings = models.Manager()

    class Meta:
        db_table = 'screening'
        constraints = [
            models.UniqueConstraint(fields=['film', 'screen', 'start_dt'],
                                    name='unique_film_screen_start')
        ]

    def __str__(self):
        start_date = self.start_dt.date().isoformat()
        start_time = self.start_dt.time().isoformat(timespec='minutes')
        end_time = self.end_dt.time().isoformat(timespec='minutes')
        return f'{self.film.title} · {self.screen} · {start_date} {start_time} - {end_time}'

    def overlaps(self, other_screening, use_travel_time=False):
        travel_time = self.get_travel_time(other_screening) if use_travel_time else datetime.timedelta(0)
        ok = other_screening.start_dt <= self.end_dt + travel_time and other_screening.end_dt >= self.start_dt - travel_time
        return ok

    def get_travel_time(self, other_screening):
        same_theater = self.screen.theater == other_screening.screen.theater
        travel_time = WALK_TIME_SAME_THEATER if same_theater else TRAVEL_TIME_OTHER_THEATER
        return travel_time


class Attendance(models.Model):
    """
    Attendance table, holds who attend what screenings.
    """
    # Define the fields.
    fan = models.ForeignKey(FilmFan, on_delete=models.CASCADE)
    screening = models.ForeignKey(Screening, on_delete=models.CASCADE)
    tickets = models.BooleanField(default=False)

    # Define a manager.
    attendances = models.Manager()

    class Meta:
        db_table = 'attendance'
        constraints = [
            models.UniqueConstraint(fields=['fan', 'screening'], name='unique_fan_screening')
        ]

    def __str__(self):
        title = self.screening.film.title
        dom = self.screening.start_dt.strftime('%d').lstrip('0')
        day = self.screening.start_dt.strftime(f'%a {dom}%b')
        start_time = self.screening.start_dt.strftime('%H:%M')
        return f'{self.fan} attends {title} on {day} at {start_time}'
