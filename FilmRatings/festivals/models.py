from django.db import models


# Festival table, to keep festival information.
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

    mnemonic = models.CharField(max_length=10)
    name = models.CharField(max_length=40)
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
        unique_together = ('mnemonic', 'year', 'edition')

    def __str__(self):
        edition_str = '' if self.edition is None else f' - {self.edition} edition'
        return f'{self.mnemonic} {self.year}{edition_str}'
