import datetime

from django.db import models


# FestivalBase table, to keep information that is invariant for
# festival editions.
class FestivalBase(models.Model):
    mnemonic = models.CharField(max_length=10, primary_key=True, serialize=False)
    name = models.CharField(max_length=60)
    image = models.CharField(max_length=200, null=True, blank=True)

    # Use a manager to retrieve data with .festivals.all() as opposed
    # to .objects.all().
    festival_bases = models.Manager()

    class Meta:
        db_table = 'film_festival_base'

    def __str__(self):
        return f'{self.mnemonic}'


# Festival table, to keep festival information.
def default_festival(today=None):
    nearest_festival = None
    if today is None:
        today = datetime.date.today()
    coming_festivals = Festival.festivals.filter(end_date__gte=today).order_by('end_date')
    if len(coming_festivals):
        return coming_festivals[0]
    past_festivals = Festival.festivals.filter(end_date__lt=today).order_by('-end_date')
    if len(past_festivals):
        return past_festivals[0]
    return nearest_festival


def set_current_festival(session):
    festival = current_festival(session)
    festival.set_current(session)


def current_festival(session):
    festival_id = session.get('festival')
    if festival_id is None:
        return default_festival()
    festival = Festival.festivals.get(id=festival_id)
    if festival is None:
        return default_festival()
    return festival


class Festival(models.Model):
    TOMATO = 'tomato'
    RED = 'red'
    ORANGE = 'orange'
    MAROON = 'maroon'
    YELLOW = 'yellow'
    LIME = 'lime'
    GREEN = 'green'
    OLIVE = 'olive'
    TURQUOISE = 'turquoise'
    BLUE = 'blue'
    NAVY = 'navy'
    FUCHSIA = 'fuchsia'
    PURPLE = 'purple'
    SILVER = 'silver'
    GRAY = 'grey'
    BLACK = 'black'
    COLOR_CHOICES = [
        (TOMATO, 'tomato'),
        (RED, 'red'),
        (ORANGE, 'orange'),
        (MAROON, 'maroon'),
        (YELLOW, 'yellow'),
        (LIME, 'lime'),
        (GREEN, 'green'),
        (OLIVE, 'olive'),
        (TURQUOISE, 'turquoise'),
        (BLUE, 'blue'),
        (NAVY, 'navy'),
        (FUCHSIA, 'fuchsia'),
        (PURPLE, 'purple'),
        (SILVER, 'silver'),
        (GRAY, 'grey'),
        (BLACK, 'black'),
    ]

    base = models.ForeignKey(FestivalBase, db_column='mnemonic', on_delete=models.CASCADE)
    year = models.IntegerField()
    edition = models.CharField(max_length=16, null=True, blank=True)
    start_date = models.DateField()
    end_date = models.DateField()
    festival_color = models.CharField(max_length=24, choices=COLOR_CHOICES, default=GREEN)

    # Use a manager to retrieve data with .festivals.all() as opposed
    # to .objects.all().
    festivals = models.Manager()

    class Meta:
        db_table = 'film_festival'
        unique_together = ('base', 'year', 'edition')

    def __str__(self):
        edition_str = '' if self.edition is None else f' - {self.edition} edition'
        return f'{self.base} {self.year}{edition_str}'

    def set_current(self, session):
        session['festival'] = self.id
