from django import forms

from festivals.models import Festival


class Loader(forms.Form):
    festival = forms.ChoiceField(
        label='Pick a festival',
        choices=[(festival.id, str(festival)) for festival in Festival.festivals.order_by('-start_date')]
    )
    keep_ratings = forms.BooleanField(
        label='Save existing ratings first',
        required=False,
        initial=True
    )
