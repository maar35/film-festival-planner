from django.db import models


# Exercise class to change table border colors.
class TableColor(models.Model):
    RED = 'red'
    IVORY = 'ivory'
    BLUE = 'blue'
    COLOR_CHOICES = [
        (RED, 'red'),
        (IVORY, 'ivory'),
        (BLUE, 'blue'),
    ]

    border_color = models.CharField(max_length=10, choices=COLOR_CHOICES, default=BLUE)
    picked_count = models.IntegerField(default=0)
    vote_count = models.IntegerField(default=0)

    # Default retrieval with .objects.all, with a manager it's .film_fans.all
    table_colors = models.Manager()

    class Meta:
        db_table = 'table_color'

    def __str__(self):
        return self.border_color
