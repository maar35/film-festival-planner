from django.db import models

from festivals.models import Festival

FANS_IN_RATINGS_TABLE = ['Maarten', 'Adrienne']


class Film(models.Model):
    """
    Film table.
    """

    # Define the fields.
    festival = models.ForeignKey(Festival, on_delete=models.CASCADE)
    film_id = models.IntegerField()
    seq_nr = models.IntegerField()
    sort_title = models.CharField(max_length=128)
    title = models.CharField(max_length=128)
    title_language = models.CharField(max_length=2)
    subsection = models.CharField(max_length=32, null=True)
    duration = models.DurationField(null=False)
    medium_category = models.CharField(max_length=32)
    url = models.URLField(max_length=200)

    # Define a manager.
    films = models.Manager()

    class Meta:
        db_table = 'film'
        unique_together = ('festival', 'film_id')

    def __str__(self):
        return f"{self.title} ({self.duration.total_seconds() / 60:.0f}')"

    def duration_str(self):
        return ':'.join(f'{self.duration}'.split(':')[:2])


def me():
    fans = FilmFan.film_fans.all()
    return fans[0] if len(fans) > 0 else None


def set_current_fan(request):
    user_fan = get_user_fan(request.user)
    if user_fan is not None:
        request.session['fan_name'] = user_fan.name


def current_fan(session):
    fan_name = session.get('fan_name')
    fan = FilmFan.film_fans.get(name=fan_name) if fan_name is not None else None
    return fan


def unset_current_fan(session):
    if session.get('fan_name', False):
        del session['fan_name']


def user_name_to_fan_name(user_name):
    return f'{user_name[0].upper()}{user_name[1:]}'


def get_user_fan(user):
    if not user.is_authenticated:
        return None
    user_fan_name = user_name_to_fan_name(user.username)
    user_fan = FilmFan.film_fans.get(name=user_fan_name) if user_fan_name is not None else None
    return user_fan


def get_present_fans():
    return FilmFan.film_fans.filter(name__in=FANS_IN_RATINGS_TABLE)


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
        return self.name[:1] if self != me() else ""

    def switch_current(self, session):
        session['fan_name'] = self.name

    def fan_rating(self, film):
        try:
            fan_rating = FilmFanFilmRating.film_ratings.get(film=film, film_fan=self)
        except (KeyError, FilmFanFilmRating.DoesNotExist):
            fan_rating = None
        return fan_rating

    def fan_rating_str(self, film):
        fan_rating = self.fan_rating(film)
        return f'{fan_rating.rating}' if fan_rating is not None else '-'

    def fan_rating_name(self, film):
        fan_rating = self.fan_rating(film)
        if fan_rating is None:
            fan_rating = FilmFanFilmRating(film=film, film_fan=self, rating=0)
        name_by_rating = dict(FilmFanFilmRating.Rating.choices)
        return name_by_rating[fan_rating.rating]


def get_rating_name(rating_value):
    choices = FilmFanFilmRating.Rating.choices
    try:
        name = [name for value, name in choices if value == int(rating_value)][0]
    except IndexError:
        name = None
    return name


class FilmFanFilmRating(models.Model):
    """
    Film Fan Film Rating table.
    """

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

    # Define a manager.
    film_ratings = models.Manager()

    class Meta:
        db_table = 'film_rating'
        unique_together = ('film', 'film_fan')

    def __str__(self):
        return f"{self.film} - {self.film_fan.initial()}{self.rating}"
