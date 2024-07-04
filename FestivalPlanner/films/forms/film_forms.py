import copy
from datetime import datetime

from django import forms
from django.core.validators import RegexValidator
from django.forms import CharField

from authentication.models import FilmFan
from festivals.models import rating_action_key
from films.models import FilmFanFilmRating, get_rating_name, current_fan, fan_rating_str, field_by_post_attendance, \
    manager_by_post_attendance

SEARCH_TEST_VALIDATOR = RegexValidator(r'^[a-z0-9]+$', 'Type only lower case letters and digits')
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
        validators=[SEARCH_TEST_VALIDATOR],
        min_length=2,
    )
    film_rating_cache = None

    @classmethod
    def update_rating(cls, session, film, fan, rating_value, post_attendance=False):
        field = field_by_post_attendance[post_attendance]
        manager = manager_by_post_attendance[post_attendance]
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


class RatingForm(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)


def init_rating_action(session, old_rating_str, new_rating, field):
    new_rating_value = getattr(new_rating, field)
    new_rating_name = get_rating_name(new_rating_value)
    now = datetime.now()
    rating_action = {
        'fan': str(current_fan(session)),
        'rating_type': field,
        'old_rating': old_rating_str,
        'new_rating': str(new_rating_value),
        'new_rating_name': new_rating_name,
        'rated_film': str(new_rating.film),
        'rated_film_id': new_rating.film.id,
        'action_time': now.isoformat(),
    }

    # Store the current time as a string in the cookie, then
    # recover the time variable.
    key = rating_action_key(session, field)
    session[key] = copy.deepcopy(rating_action)
    rating_action['action_time'] = now


def refreshed_rating_action(session, tag):
    key = rating_action_key(session, tag)
    if key in session:
        action = copy.deepcopy(session[key])
        action['action_time'] = datetime.fromisoformat(action['action_time'])
    else:
        action = None
    return action
