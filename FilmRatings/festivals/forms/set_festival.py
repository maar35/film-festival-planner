from django import forms
from festivals.models import Festival


class FestivalEdition(forms.Form):
    festival = forms.ChoiceField(
        label='Pick a festival',
        choices=[(festival.id, festival) for festival in Festival.festivals.order_by('-start_date')]
    )
