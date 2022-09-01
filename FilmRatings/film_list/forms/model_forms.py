from django import forms

from film_list.models import FilmFan,  FilmFanFilmRating


class User(forms.Form):
    selected_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=[(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')],
    )


class Rating(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)
