from django import forms


class DummyForm(forms.Form):
    dummy_field = forms.SlugField(required=False)
