from django import forms
from festivals.models import Festival


class FestivalDetail(forms.Form):
    border_color = forms.ChoiceField(label='Pick a festival color', choices=Festival.COLOR_CHOICES)
