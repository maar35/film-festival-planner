from django import forms

from FilmRatings.tools import initialize_log, add_log
from loader.forms.loader_forms import FilmLoader


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
