from django.db import models

from authentication.models import FilmFan
from films.models import Film
from theaters.models import Screen


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

    # Define the fields.
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    screen = models.ForeignKey(Screen, on_delete=models.CASCADE)
    start_dt = models.DateTimeField()
    end_dt = models.DateTimeField()
    status = models.IntegerField(choices=ScreeningStatus.choices, default=ScreeningStatus.FREE)
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
        return f'{start_date} {start_time} - {end_time} {self.screen} {self.film.title}'

    def get_status(self, fan):
        pass


class Attendance(models.Model):
    """
    Attendance tabel, holds who attend what screenings.
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
