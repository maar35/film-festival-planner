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


def get_sorted_fan_list(current_fan, fan_query_set=None):
    """
    Return a list of fans, starting with the current fan, followed by the other fans sorted by name.
    """
    fan_query_set = FilmFan.film_fans.all() if fan_query_set is None else fan_query_set
    first = [current_fan] if current_fan in fan_query_set else []
    return first + list(fan_query_set.exclude(id=current_fan.id).order_by('name'))
