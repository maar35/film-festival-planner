from django.db import models

from authentication.models import FilmFan
from festivals.config import Config
from festivals.models import Festival, current_festival
from sections.models import Subsection

MINUTES_STR = "'"
UNRATED_STR = '-'
FANS_IN_RATINGS_TABLE = ['Maarten', 'Adrienne']
MIN_ALARM_RATING_DIFF = 3
constants = Config().config['Constants']
LOWEST_PLANNABLE_RATING = constants['LowestPlannableRating']
HIGHEST_NOT_PLANNABLE_RATING = constants['HighestNotPlannableRating']
FAN_NAMES_BY_FESTIVAL_BASE = {
    'IFFR': ['Maarten', 'Adrienne', 'Manfred', 'Piggel', 'Rijk', 'Martin'],
    'MTMF': ['Maarten', 'Adrienne', 'Manfred'],
    'NFF': [],
    'Imagine': ['Maarten', 'Adrienne', 'Piggel'],
    'IDFA': ['Maarten', 'Adrienne'],
}


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

    def rating_strings(self):
        """
        Returns a string of fan initials with their ratings, the representative
        rating of the film, and the maximum rating of the film.
        The representative rating string is the highest rating, with a question
        mark added when the lowest rating significantly differs.
        """

        ordered_ratings = FilmFanFilmRating.film_ratings.filter(film=self).order_by('rating')

        # Get a summary of fans and their ratings.
        fans_rating_str = ''.join([r.str_fan_rating() for r in ordered_ratings])

        # Get the representative rating.
        min_rating = get_rating_as_int(ordered_ratings.first())
        max_rating = get_rating_as_int(ordered_ratings.last())
        film_rating_str = str(max_rating)
        if min_rating != FilmFanFilmRating.Rating.INDECISIVE and max_rating - min_rating >= MIN_ALARM_RATING_DIFF:
            film_rating_str += '?'

        return fans_rating_str, film_rating_str, max_rating

    def rating_string(self):
        film_rating_str = self.rating_strings()[1]
        return film_rating_str


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

    def __int__(self):
        return self.rating

    def __lt__(self, other):
        return self.rating < other.rating

    @classmethod
    def get_eligible_ratings(cls):
        return cls.Rating.values[LOWEST_PLANNABLE_RATING:]

    @classmethod
    def get_interesting_ratings(cls):
        return [cls.Rating.UNRATED] + cls.get_eligible_ratings()

    def str_fan_rating(self):
        return f'{self.film_fan.initial()}{self.rating}'

    @classmethod
    def get_not_plannable_ratings(cls):
        return cls.Rating.values[:HIGHEST_NOT_PLANNABLE_RATING]


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
    festival = current_festival(session)
    base = festival.base.mnemonic
    fan_names = FAN_NAMES_BY_FESTIVAL_BASE[base]
    return FilmFan.film_fans.filter(name__in=fan_names)


def get_judging_fans():
    return FilmFan.film_fans.filter(name__in=FANS_IN_RATINGS_TABLE)


def get_rating_as_int(rating):
    if rating:
        return int(rating)
    return FilmFanFilmRating.Rating.UNRATED


def get_rating_name(rating_value):
    choices = FilmFanFilmRating.Rating.choices
    try:
        name = [name for value, name in choices if value == int(rating_value)][0]
    except IndexError:
        name = None
    return name


def fan_rating(fan, film, manager=None):
    manager = manager or FilmFanFilmRating.film_ratings
    kwargs = {'film': film, 'film_fan': fan}
    ratings = manager.filter(**kwargs)
    rating = ratings.get(**kwargs) if ratings.exists() else None
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
