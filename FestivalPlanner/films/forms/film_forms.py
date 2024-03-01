import copy
from datetime import datetime

from django import forms

from festivals.models import rating_action_key
from films.models import FilmFanFilmRating, get_rating_name, current_fan, fan_rating_str, FilmFanFilmVote
from authentication.models import FilmFan


class UserForm(forms.Form):
    selected_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=[(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')],
    )


class PickRating(forms.Form):
    dummy_field = forms.SlugField(required=False)
    field_by_postview = {False: 'rating', True: 'vote'}
    manager_by_post_view = {False: FilmFanFilmRating.film_ratings, True: FilmFanFilmVote.film_votes}
    film_rating_cache = None

    @classmethod
    def update_rating(cls, session, film, fan, rating_value, post_attendance=False):
        field = cls.field_by_postview[post_attendance]
        manager = cls.manager_by_post_view[post_attendance]
        old_rating_str = fan_rating_str(fan, film, manager=manager, field=field)

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
        cls.init_rating_action(session, old_rating_str, new_rating, field)

        # Update cache if applicable.
        if not post_attendance:
            cls.film_rating_cache.update(session, film, fan, rating_value)

    @staticmethod
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
        key = rating_action_key(session, field)
        session[key] = copy.deepcopy(rating_action)
        rating_action['action_time'] = now

    @staticmethod
    def refresh_rating_action(session, context, field):
        key = rating_action_key(session, field)
        if key in session:
            action = copy.deepcopy(session[key])
            context['action'] = action
            context['action']['action_time'] = datetime.fromisoformat(action['action_time'])


class RatingForm(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)
