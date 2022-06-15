from django import forms
from filmList.models import FilmFanFilmRating


class Rating(forms.Form):
    fan_rating = forms.ChoiceField(label='Pick a rating', choices=FilmFanFilmRating.Rating.choices)
