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
def current_festival():
    festivals = Festival.festivals.filter(is_current_festival=True)
    return festivals[0] if len(festivals) == 1 else None


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
    border_color = models.CharField(max_length=10, choices=COLOR_CHOICES, default=GREEN)
    is_current_festival = models.BooleanField(default=False)

    # Use a manager to retrieve data with .festivals.all() as opposed
    # to .objects.all().
    festivals = models.Manager()

    class Meta:
        db_table = 'film_festival'
        unique_together = ('base', 'year', 'edition')

    def __str__(self):
        edition_str = '' if self.edition is None else f' - {self.edition} edition'
        return f'{self.base} {self.year}{edition_str}'

    def set_current_festival(self):
        current_festivals = Festival.festivals.filter(is_current_festival=True)
        for festival in current_festivals:
            festival.is_current_festival = False
            festival.save()
        self.is_current_festival = True
        self.save()

