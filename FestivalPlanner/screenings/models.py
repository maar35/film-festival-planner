from django.db import models

from films.models import Film
from theaters.models import Screen


class Screening(models.Model):
    """
    Screenings table.
    """
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
        return f'{start_date} {start_time} - {end_time} {self.screen} {self.film.title}'
