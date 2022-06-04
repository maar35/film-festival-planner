from django.db import models


# Film table.
class Film(models.Model):

    # Define the fields.
    film_id = models.IntegerField(primary_key=True, serialize=False)
    seq_nr = models.IntegerField()
    sort_title = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    title_language = models.CharField(max_length=2)
    section = models.CharField(max_length=32, null=True)
    duration = models.DurationField(null=False)
    medium_category = models.CharField(max_length=32)
    url = models.URLField(max_length=200)

    # Default retrieval with .objects.all, with a manager it's .films.all
    films = models.Manager()

    class Meta:
        db_table = "films"

    def __str__(self):
        return f"{self.title} ({self.duration.total_seconds() / 60:.0f}')"

    def duration_str(self):
        return ":".join(f"{self.duration}".split(":")[:2])


# Film Fan table.
def me():
    fans = FilmFan.film_fans.all()
    return fans[0] if len(fans) > 0 else None


class FilmFan(models.Model):

    # Define the fields.
    name = models.CharField(max_length=16, primary_key=True, serialize=False)
    seq_nr = models.IntegerField(unique=True)

    # Default retrieval with .objects.all, with a manager it's .film_fans.all
    film_fans = models.Manager()

    class Meta:
        db_table = "film_fans"

    def __str__(self):
        return self.name

    def initial(self):
        return self.name[:1] if self != me() else ""


# Film Fan Film Rating table.
class FilmFanFilmRating(models.Model):

    class Rating(models.IntegerChoices):
        UNRATED = 0
        VERY_BAD = 1
        BAD = 2
        VERY_INSUFFICIENT = 3
        INSUFFICIENT = 4
        BELOW_MEDIOCRE = 5
        MEDIOCRE = 6
        INDECISIVE = 7
        GOOD = 8
        VERY_GOOD = 9
        EXCELLENT = 10

    # Define the fields.
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    film_fan = models.ForeignKey(FilmFan, db_column='name', on_delete=models.CASCADE)
    rating = models.IntegerField(choices=Rating.choices)

    # Default retrieval with .objects.all, with a manager it's .fan_ratings.all
    fan_ratings = models.Manager()

    class Meta:
        db_table = 'film_fan_film_rating'
        unique_together = ('film', 'film_fan')

    def __str__(self):
        return f"{self.film} - {self.film_fan.initial()}{self.rating}"
