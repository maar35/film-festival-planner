from django import forms

from festival_planner.tools import initialize_log, add_log
from films.models import FilmFanFilmRating, FilmFan
from loader.forms.loader_forms import FilmLoader


class UserForm(forms.Form):
    selected_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=[(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')],
    )


class PickRating(forms.Form):
    dummy_field = forms.SlugField(required=False)


class SaveRatingsForm(forms.Form):
    dummy_field = forms.SlugField(required=False)

    @staticmethod
    def save_ratings(session, festival):
        initialize_log(session, 'Save')
        add_log(session, f'Saving the {festival} ratings.')
        if not FilmLoader(session, festival, True).save_ratings(festival.ratings_file):
            add_log(session, f'Failed to save the {festival} ratings.')


class RatingForm(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)
