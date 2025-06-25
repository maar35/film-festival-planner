import datetime

from django.db import models

from authentication.models import FilmFan, get_sorted_fan_list
from availabilities.models import Availabilities
from festival_planner.debug_tools import profiled_method, UNAVAILABLE_PROFILER, RATING_DATA_PROFILER, \
    FAN_ATTENDS_PROFILER
from festivals.config import Config
from films.models import Film, FilmFanFilmRating, fan_rating
from theaters.models import Screen

CONSTANTS_CONFIG = Config().config['Constants']
WALK_TIME_SAME_THEATER = datetime.timedelta(minutes=CONSTANTS_CONFIG['WalkMinutesSameTheater'])
TRAVEL_TIME_OTHER_THEATER = datetime.timedelta(minutes=CONSTANTS_CONFIG['TravelMinutesOtherTheater'])


COLOR_WARNING_ORANGE = 'rgb(255, 127, 0)'
COLOR_WARNING_RED = 'rgb(255, 38, 0)'
COLOR_WARNING_YELLOW = 'rgb(255, 219, 0)'


def color_pair(color, background):
    return {'color': color, 'background': background}


COLOR_PAIR_TRANSPARANT = color_pair(None, None)
COLOR_PAIR_OFF_BLACK = color_pair('orange', None)
COLOR_PAIR_RED = color_pair('white', 'rgb(176, 0, 38)')
COLOR_PAIR_BLUE = color_pair('yellow', 'rgb(0, 38, 176)')
COLOR_PAIR_YELLOW = color_pair('black', 'yellow')
COLOR_PAIR_GREY = color_pair('darkgrey', 'rgb(79, 79, 79)')
COLOR_PAIR_DARKGREY = color_pair('darkgrey', 'rgb(38, 38, 38)')
COLOR_PAIR_PURPLE = color_pair('white', 'rgb(176, 0, 176)')
COLOR_PAIR_AQUA = color_pair('black', 'rgb(38, 255, 176)')
COLOR_PAIR_SELECT_BLUE = color_pair(None,  'rgba(0, 0, 255, 0.8)')
COLOR_PAIR_SCREEN = color_pair(None, 'rgba(0, 0, 0, 0.4)')

COLOR_PAIR_FREE = COLOR_PAIR_TRANSPARANT
COLOR_PAIR_UNAVAILABLE = COLOR_PAIR_OFF_BLACK
COLOR_PAIR_ATTENDS = COLOR_PAIR_RED
COLOR_PAIR_FRIEND_ATTENDS = COLOR_PAIR_BLUE
COLOR_PAIR_ATTENDS_FILM = COLOR_PAIR_YELLOW
COLOR_PAIR_TIME_OVERLAP = COLOR_PAIR_GREY
COLOR_PAIR_NO_TRAVEL_TIME = COLOR_PAIR_DARKGREY
COLOR_PAIR_NEEDS_TICKETS = COLOR_PAIR_PURPLE
COLOR_PAIR_SHOULD_SELL_TICKETS = COLOR_PAIR_AQUA
COLOR_PAIR_SELECTED = COLOR_PAIR_SELECT_BLUE


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
        SHOULD_SELL_TICKETS = 8,

    # Define color dictionaries.
    color_pair_by_screening_status = {
        ScreeningStatus.FREE: COLOR_PAIR_FREE,
        ScreeningStatus.UNAVAILABLE: COLOR_PAIR_UNAVAILABLE,
        ScreeningStatus.ATTENDS: COLOR_PAIR_ATTENDS,
        ScreeningStatus.FRIEND_ATTENDS: COLOR_PAIR_FRIEND_ATTENDS,
        ScreeningStatus.ATTENDS_FILM: COLOR_PAIR_ATTENDS_FILM,
        ScreeningStatus.TIME_OVERLAP: COLOR_PAIR_TIME_OVERLAP,
        ScreeningStatus.NO_TRAVEL_TIME: COLOR_PAIR_NO_TRAVEL_TIME,
        ScreeningStatus.NEEDS_TICKETS: COLOR_PAIR_NEEDS_TICKETS,
        ScreeningStatus.SHOULD_SELL_TICKETS: COLOR_PAIR_SHOULD_SELL_TICKETS,
    }

    color_pair_selected_by_screening_status = {
        c[0]: color_pair('white', 'blue') for c in ScreeningStatus.choices
    }
    color_pair_selected_by_screening_status[ScreeningStatus.FRIEND_ATTENDS] = COLOR_PAIR_RED

    color_warning_by_screening_status = {
        c[0]: COLOR_WARNING_ORANGE for c in ScreeningStatus.choices
    }
    color_warning_by_screening_status[ScreeningStatus.ATTENDS] = COLOR_WARNING_YELLOW
    color_warning_by_screening_status[ScreeningStatus.ATTENDS_FILM] = COLOR_WARNING_RED
    color_warning_by_screening_status[ScreeningStatus.UNAVAILABLE] = COLOR_WARNING_RED
    color_warning_by_screening_status[ScreeningStatus.SHOULD_SELL_TICKETS] = COLOR_WARNING_RED

    # Define colors that help interesting ratings to stand out.
    interesting_rating_color_attends_film_background = 'blue'
    interesting_rating_color_should_sell_background = 'blue'
    uninteresting_rating_color = 'grey'

    # Define the fields.
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE)
    start_dt = models.DateTimeField()
    end_dt = models.DateTimeField()
    combination_program = models.ForeignKey(Film, null=True, on_delete=models.SET_NULL,
                                            related_name='combined_screening')
    subtitles = models.CharField(max_length=24)
    q_and_a = models.BooleanField()
    auto_planned = models.BooleanField(default=False)

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

    def str_day_of_month(self):
        return self.start_dt.strftime('%d').lstrip('0')

    def str_day(self):
        return self.start_dt.strftime(f'%a {self.str_day_of_month()} %b')

    def str_start_time(self):
        return self.start_dt.strftime('%H:%M')

    def str_short(self):
        return f'{self.str_day()} {self.str_start_time()} {self.screen}'

    def str_title(self):
        return f'{self.film.title} on {self.str_day()}'

    def str_q_and_a(self):
        return 'Yes!' if self.q_and_a else None

    def duration(self):
        return self.end_dt - self.start_dt

    def overlaps(self, other_screening, use_travel_time=False):
        travel_time = self.get_travel_time(other_screening) if use_travel_time else datetime.timedelta(0)
        ok = other_screening.start_dt <= self.end_dt + travel_time and other_screening.end_dt >= self.start_dt - travel_time
        return ok

    def get_travel_time(self, other_screening):
        same_theater = self.screen.theater == other_screening.screen.theater
        travel_time = WALK_TIME_SAME_THEATER if same_theater else TRAVEL_TIME_OTHER_THEATER
        return travel_time

    @profiled_method(UNAVAILABLE_PROFILER)
    def available_by_fan(self, fan):
        manager = Availabilities.availabilities
        availabilities = manager.filter(fan=fan, start_dt__lte=self.start_dt, end_dt__gte=self.end_dt)
        return availabilities or False

    def get_available_fans(self):
        manager = Availabilities.availabilities
        kwargs = {'start_dt__lte': self.start_dt, 'end_dt__gte': self.end_dt}
        available_fans = [availability.fan for availability in manager.filter(**kwargs)]
        return available_fans

    @profiled_method(FAN_ATTENDS_PROFILER)
    def fan_attends(self, fan):
        attendances = Attendance.attendances.filter(screening=self, fan=fan)
        return attendances

    def attendants_str(self):
        attendances = Attendance.attendances.filter(screening=self)
        return ', '.join(attendance.fan.name for attendance in attendances)

    def attendants_abbr(self):
        attendances = Attendance.attendances.filter(screening=self)
        return ', '.join(attendance.fan.initial() for attendance in attendances)

    def attending_fans(self):
        attendances = Attendance.attendances.filter(screening=self)
        fans = [attendance.fan for attendance in attendances]
        return fans

    def attending_friends(self, fan):
        friend_attendances = Attendance.attendances.filter(screening=self).exclude(fan=fan)
        attending_friends = [a.fan for a in friend_attendances]
        return attending_friends

    def fan_has_ticket(self, fan):
        tickets = Ticket.tickets.filter(fan=fan, screening=self)
        return tickets

    def fan_ticket_confirmed(self, fan):
        confirmed = Ticket.tickets.filter(fan=fan, screening=self, confirmed=True)
        return confirmed

    def filmscreening_count(self):
        return len(filmscreenings(self.film))

    @profiled_method(RATING_DATA_PROFILER)
    def film_rating_data(self, status):
        """
        Return compact rating per fan, representative film rating string
        and the color indicating whether the rating is interesting.
        """
        # Get the fan ratings string and the representative film rating string.
        fan_ratings_str, film_rating_str, max_rating = film_rating_strings(self)

        # decide the color.
        attends_film = status == self.ScreeningStatus.ATTENDS_FILM
        attends = status == self.ScreeningStatus.ATTENDS
        should_sell_ticket = status == self.ScreeningStatus.SHOULD_SELL_TICKETS
        rating_is_interesting = max_rating in FilmFanFilmRating.get_interesting_ratings()
        regular_color = self.color_pair_selected_by_screening_status[status]['color']
        if attends:
            color = regular_color
        elif rating_is_interesting:
            if attends_film:
                color = Screening.interesting_rating_color_attends_film_background
            elif should_sell_ticket:
                color = Screening.interesting_rating_color_should_sell_background
            else:
                color = regular_color
        else:
            color = Screening.uninteresting_rating_color

        return fan_ratings_str, film_rating_str, color


class Attendance(models.Model):
    """
    Attendance table, holds who attend what screenings.
    """
    # Define the fields.
    fan = models.ForeignKey(FilmFan, on_delete=models.CASCADE)
    screening = models.ForeignKey(Screening, on_delete=models.CASCADE)

    # Define a manager.
    attendances = models.Manager()

    class Meta:
        db_table = 'attendance'
        constraints = [
            models.UniqueConstraint(fields=['fan', 'screening'], name='unique_fan_screening')
        ]

    def __str__(self):
        start_time = self.screening.str_start_time()
        return f'{self.fan} attends {self.screening.str_title} at {start_time}'


class Ticket(models.Model):
    """
    Represents a ticket for a screening of one fan.
    """
    # Define the fields.
    screening = models.ForeignKey(Screening, on_delete=models.CASCADE)
    fan = models.ForeignKey(FilmFan, on_delete=models.CASCADE)
    confirmed = models.BooleanField(default=False)

    # Define a manager.
    tickets = models.Manager()

    class Meta:
        db_table = 'ticket'
        constraints = [
            models.UniqueConstraint(fields=['screening', 'fan'], name='unique_screening_fan')
        ]

    def __str__(self):
        return f'Ticket of {self.fan} for {self.screening.str_title()}'


def film_rating_strings(screening):
    return screening.film.rating_strings()


def filmscreenings(film):
    return Screening.screenings.filter(film=film)


def get_available_filmscreenings(film, fan):
    screenings = filmscreenings(film)
    available_filmscreenings = [s for s in screenings if s.available_by_fan(fan)]
    return available_filmscreenings
