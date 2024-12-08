from django.db import models

from authentication.models import FilmFan
from festivals.models import Festival, current_festival
from sections.models import Subsection

MINUTES_STR = "'"
UNRATED_STR = '-'
FANS_IN_RATINGS_TABLE = ['Maarten', 'Adrienne']
MIN_ALARM_RATING_DIFF = 3


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
    subsection = models.ForeignKey(Subsection, null=True, on_delete=models.SET_NULL)
    duration = models.DurationField(null=False)
    medium_category = models.CharField(max_length=32)
    reviewer = models.CharField(max_length=32, null=True)
    url = models.URLField(max_length=200)

    # Define a manager.
    films = models.Manager()

    class Meta:
        db_table = 'film'
        unique_together = ('festival', 'film_id')

    def __str__(self):
        return f"{self.title} ({minutes_str(self.duration)})"

    def duration_str(self):
        return ':'.join(f'{self.duration}'.split(':')[:2])


class FilmFanFilmRating(models.Model):
    """
    Film Fan Film Rating table.
    This rating is an estimate in advance, used to choose which films to see in a festival.
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
        return f"{self.film} - {self.str_fan_rating()}"

    @classmethod
    def super_ratings(cls):
        # TODO: Be consequent: have either the list below or [LOWEST_PLANNABLE_RATING:]
        return [cls.Rating.GOOD, cls.Rating.VERY_GOOD, cls.Rating.EXCELLENT]

    @classmethod
    def interesting_ratings(cls):
        return [cls.Rating.UNRATED] + cls.super_ratings()

    def str_fan_rating(self):
        return f'{self.film_fan.initial()}{self.rating}'


class FilmFanFilmVote(models.Model):
    """
    Film Fan Film Vote table.
    This vote is a retrospective judgement of a film that a fan saw on a festival.
    """
    choices = [(member.value, member.label) for member in FilmFanFilmRating.Rating if member.name not in ['ALREADY_SEEN', 'WILL_SEE']]

    # Define the fields.
    film = models.ForeignKey(Film, on_delete=models.CASCADE)
    film_fan = models.ForeignKey(FilmFan, on_delete=models.CASCADE)
    vote = models.IntegerField(choices=choices)

    # Define a manager.
    film_votes = models.Manager()

    class Meta:
        db_table = 'film_vote'
        unique_together = ('film', 'film_fan')

    def __str__(self):
        return f"{self.film} - {self.film_fan.initial()}{self.vote}"


def minutes_str(duration):
    return f'{duration.total_seconds() / 60:.0f}{MINUTES_STR}'


def set_current_fan(request):
    user_fan = get_user_fan(request.user)
    if user_fan is not None:
        request.session['fan_name'] = user_fan.name


def current_fan(session):
    fan_name = session.get('fan_name')
    fan = FilmFan.film_fans.get(name=fan_name) if fan_name else None
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


def initial(fan, session):
    return '' if fan == current_fan(session) else fan.initial()


def get_present_fans(session):
    fan_names_by_festival_base = {
        'IFFR': ['Maarten', 'Adrienne', 'Manfred', 'Piggel', 'Rijk'],
        'MTMF': ['Maarten', 'Adrienne'],
        'NNF': [],
        'Imagine': ['Maarten', 'Adrienne'],
        'IDFA': ['Maarten', 'Adrienne'],
    }
    festival = current_festival(session)
    base = festival.base.mnemonic
    fan_names = fan_names_by_festival_base[base]
    return FilmFan.film_fans.filter(name__in=fan_names)


def get_judging_fans():
    return FilmFan.film_fans.filter(name__in=FANS_IN_RATINGS_TABLE)


def get_rating_name(rating_value):
    choices = FilmFanFilmRating.Rating.choices
    try:
        name = [name for value, name in choices if value == int(rating_value)][0]
    except IndexError:
        name = None
    return name


def fan_rating(fan, film, manager=None):
    manager = manager or FilmFanFilmRating.film_ratings
    try:
        rating = manager.get(film=film, film_fan=fan)
    except (KeyError, FilmFanFilmRating.DoesNotExist, FilmFanFilmVote.DoesNotExist):
        rating = None
    return rating


FIELD_BY_POST_ATTENDANCE = {False: 'rating', True: 'vote'}
MANAGER_BY_POST_ATTENDANCE = {False: FilmFanFilmRating.film_ratings, True: FilmFanFilmVote.film_votes}


def fan_rating_str(fan, film, post_attendance=False):
    manager = MANAGER_BY_POST_ATTENDANCE[post_attendance]
    field = FIELD_BY_POST_ATTENDANCE[post_attendance]
    rating = fan_rating(fan, film, manager)
    return f'{getattr(rating, field)}' if rating is not None else UNRATED_STR


def rating_str(rating):
    return UNRATED_STR if rating == '0' else rating
