from django import forms


class PickRating(forms.Form):
    dummy_field = forms.SlugField(required=False)
