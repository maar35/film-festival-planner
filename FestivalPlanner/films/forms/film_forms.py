import copy
from datetime import datetime

from django import forms
from django.core.validators import RegexValidator
from django.forms import CharField

from authentication.models import FilmFan
from festival_planner.cache import FilmRatingCache
from festival_planner.fan_action import RatingAction
from festivals.models import rating_action_key, current_festival
from films.models import FilmFanFilmRating, fan_rating_str, FIELD_BY_POST_ATTENDANCE, \
    MANAGER_BY_POST_ATTENDANCE

SEARCH_TEXT_VALIDATOR = RegexValidator(r'^\w+$', 'Type letters and digits only')
"""
No spaces allowed (yet) to discourage entering articles while searching and
sorting is based on sort_title.
"""


def eligible_fans():
    return [(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')]


class UserForm(forms.Form):
    selected_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=eligible_fans,
    )


class PickRating(forms.Form):
    search_text = CharField(
        label='Find a title by entering a snippet of it',
        required=False,
        validators=[SEARCH_TEXT_VALIDATOR],
        min_length=2,
    )
    film_rating_cache = None
    rating_action_by_field = {key: RatingAction(key) for key in FIELD_BY_POST_ATTENDANCE.values()}

    @classmethod
    def update_rating(cls, session, film, fan, rating_value, post_attendance=False):
        field = FIELD_BY_POST_ATTENDANCE[post_attendance]
        manager = MANAGER_BY_POST_ATTENDANCE[post_attendance]
        old_rating_str = fan_rating_str(fan, film, post_attendance=post_attendance)

        # Update the indicated rating.
        new_rating, created = manager.update_or_create(
            film=film,
            film_fan=fan,
            defaults={field: rating_value},
        )

        # Remove zero-ratings (unrated).
        kwargs = {'film': film, 'film_fan': fan, field: 0}
        zero_ratings = manager.filter(**kwargs)
        if len(zero_ratings) > 0:
            zero_ratings.delete()

        # Prepare the rating change being displayed.
        init_rating_action(session, old_rating_str, new_rating, field)

        # Update cache if applicable.
        if not post_attendance and cls.film_rating_cache:
            cls.film_rating_cache.update_festival_caches(session, film, fan, rating_value)

    @classmethod
    def invalidate_festival_caches(cls, session, errors=None):
        errors = errors or []
        if not PickRating.film_rating_cache:
            PickRating.film_rating_cache = FilmRatingCache(session, errors)
        PickRating.film_rating_cache.invalidate_festival_caches(current_festival(session))


class RatingForm(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)


def init_rating_action(session, old_rating_str, new_rating, field):
    kwargs = {
        'old_rating_str': old_rating_str,
        'new_rating': new_rating,
        'field': field,
    }
    PickRating.rating_action_by_field[field].init_action(session, **kwargs)


def refreshed_rating_action(session, tag):
    key = rating_action_key(session, tag)
    if key in session:
        action = copy.deepcopy(session[key])
        action['action_time'] = datetime.fromisoformat(action['action_time'])
    else:
        action = None
    return action
