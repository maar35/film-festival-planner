from datetime import datetime

from django import forms

from festivals.models import current_festival
from films.models import FilmFanFilmRating, FilmFan, get_rating_name, current_fan


class UserForm(forms.Form):
    selected_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=[(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')],
    )


class PickRating(forms.Form):
    dummy_field = forms.SlugField(required=False)

    @staticmethod
    def update_rating(session, film, fan, rating_value):
        old_rating_str = fan.fan_rating_str(film)
        new_rating, created = FilmFanFilmRating.film_ratings.update_or_create(
            film=film,
            film_fan=fan,
            defaults={'rating': rating_value},
        )
        zero_ratings = FilmFanFilmRating.film_ratings.filter(film=film, film_fan=fan, rating=0)
        if len(zero_ratings) > 0:
            zero_ratings.delete()
        PickRating.init_rating_action(session, old_rating_str, new_rating)

    @staticmethod
    def init_rating_action(session, old_rating_str, new_rating):
        new_rating_name = get_rating_name(new_rating.rating)
        rating_action = {
            'fan': str(current_fan(session)),
            'old_rating': old_rating_str,
            'new_rating': str(new_rating.rating),
            'new_rating_name': new_rating_name,
            'rated_film': str(new_rating.film),
            'rated_film_id': new_rating.film.id,
            'action_time': datetime.now().isoformat(),
        }
        session[PickRating.rating_action_key(session)] = rating_action

    @staticmethod
    def refresh_rating_action(session, context):
        key = PickRating.rating_action_key(session)
        if key in session:
            action = session[key]
            context['action'] = action
            context['action']['action_time'] = datetime.fromisoformat(action['action_time'])

    @staticmethod
    def rating_action_key(session):
        return f'rating_action_{current_festival(session).id}'


class RatingForm(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)

