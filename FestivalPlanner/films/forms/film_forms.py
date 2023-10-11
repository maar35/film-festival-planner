from django import forms

from films.models import FilmFanFilmRating, FilmFan


class UserForm(forms.Form):
    selected_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=[(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')],
    )


class PickRating(forms.Form):
    dummy_field = forms.SlugField(required=False)


class RatingForm(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)
