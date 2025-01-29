from django.db import models

INITIAL_BY_FAN = {'Maarten': 'Ⓜ', 'Martin': 'H'}


class FilmFan(models.Model):

    # Define the fields.
    name = models.CharField(max_length=16, unique=True)
    seq_nr = models.IntegerField(unique=True)
    is_admin = models.BooleanField(default=False)

    # Define a manager.
    film_fans = models.Manager()

    class Meta:
        db_table = "film_fan"

    def __str__(self):
        return f'{self.name}'

    def initial(self):
        return INITIAL_BY_FAN[self.name] if self.name in INITIAL_BY_FAN else self.name[:1]

    def switch_current(self, session):
        session['fan_name'] = self.name


def me():
    return FilmFan.film_fans.get(seq_nr=1) or None
