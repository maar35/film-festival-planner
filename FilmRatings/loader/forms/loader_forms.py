from django import forms


class Loader(forms.Form):
    keep_ratings = forms.BooleanField(
        label='Save existing ratings before loading',
        required=False,
        initial=True
    )
