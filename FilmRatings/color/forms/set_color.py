from django import forms
from color.models import TableColor


class Color(forms.Form):
    border_color = forms.ChoiceField(label='Pick a color', choices=TableColor.COLOR_CHOICES)
