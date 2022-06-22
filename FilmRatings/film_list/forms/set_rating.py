from django import forms
from film_list.models import FilmFanFilmRating


class Rating(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)
