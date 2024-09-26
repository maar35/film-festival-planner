from django.db import models

from authentication.models import FilmFan


class Availabilities(models.Model):
    """
    The availabilities table holds the periods in time that a user is available for a festival.
    The app limits the availability periods to be within festival periods.
    """
    # Define the fields.
    fan = models.ForeignKey(FilmFan, on_delete=models.CASCADE)
    start_dt = models.DateTimeField()
    end_dt = models.DateTimeField()

    # Define a manager.
    availabilities = models.Manager()

    class Meta:
        db_table = 'availability'
        constraints = [
            models.UniqueConstraint(fields=['fan', 'start_dt'],
                                    name='unique_fan_start')
        ]

    def __str__(self):
        dt_fmt = '%Y-%m-%d %H:00'
        return (f'{self.fan.name} is available'
                f' between {self.start_dt.strftime(dt_fmt)} and {self.end_dt.strftime(dt_fmt)}')
