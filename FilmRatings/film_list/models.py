from django.core.exceptions import ObjectDoesNotExist
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


def current_fan():
    logged_in_fans = FilmFan.film_fans.filter(is_logged_in=True)
    return logged_in_fans[0] if len(logged_in_fans) == 1 else None


class FilmFan(models.Model):

    # Define the fields.
    name = models.CharField(max_length=16, unique=True)
    seq_nr = models.IntegerField(unique=True)
    is_logged_in = models.BooleanField(default=False)

    # Default retrieval with .objects.all, with a manager it's .film_fans.all
    film_fans = models.Manager()

    class Meta:
        db_table = "film_fans"

    def __str__(self):
        return self.name

    def initial(self):
        return self.name[:1] if self != me() else ""

    def fan_rating(self, film):
        try:
            fan_rating = FilmFanFilmRating.fan_ratings.get(film=film, film_fan=self)
        except (KeyError, ObjectDoesNotExist):
            fan_rating = None
        return fan_rating

    def fan_rating_str(self, film):
        fan_rating = self.fan_rating(film)
        return f'{fan_rating.rating}' if fan_rating is not None else ''

    def fan_rating_name(self, film):
        fan_rating = self.fan_rating(film)
        if fan_rating is None:
            fan_rating = FilmFanFilmRating(film=film, film_fan=self, rating=0)
        name_by_rating = dict(FilmFanFilmRating.Rating.choices)
        return name_by_rating[fan_rating.rating]


# Film Fan Film Rating table.
class FilmFanFilmRating(models.Model):

    class Rating(models.IntegerChoices):
        UNRATED = 0
        ALREADY_SEEN = 1
        WILL_SEE = 2
        VERY_BAD = 3
        BAD = 4
        BELOW_MEDIOCRE = 5
        MEDIOCRE = 6
        INDECISIVE = 7
        GOOD = 8
        VERY_GOOD = 9
        EXCELLENT = 10

    # Define the fields.
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    film_fan = models.ForeignKey(FilmFan, on_delete=models.CASCADE)
    rating = models.IntegerField(choices=Rating.choices)

    # Default retrieval with .objects.all, with a manager it's .fan_ratings.all
    fan_ratings = models.Manager()

    class Meta:
        db_table = 'film_fan_film_rating'
        unique_together = ('film', 'film_fan')

    def __str__(self):
        return f"{self.film} - {self.film_fan.initial()}{self.rating}"
