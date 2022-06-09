from django.db import models


# Exercise class to change table border colors.
class TableColor(models.Model):
    RED = 'red'
    MAROON = 'maroon'
    GREEN = 'green'
    LIME = 'lime'
    BLUE = 'blue'
    NAVY = 'navy'
    BLACK = 'black'
    COLOR_CHOICES = [
        (RED, 'red'),
        (MAROON, 'maroon'),
        (GREEN, 'green'),
        (LIME, 'lime'),
        (BLUE, 'blue'),
        (NAVY, 'navy'),
        (BLACK, 'black'),
    ]

    border_color = models.CharField(max_length=10, choices=COLOR_CHOICES, default=LIME)
    picked_count = models.IntegerField(default=0)
    vote_count = models.IntegerField(default=0)

    # Default retrieval with .objects.all, with a manager it's .film_fans.all
    table_colors = models.Manager()

    class Meta:
        db_table = 'table_color'

    def __str__(self):
        return self.border_color
