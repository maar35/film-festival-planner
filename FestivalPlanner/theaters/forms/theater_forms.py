from django import forms
from django.core.validators import RegexValidator

TheaterAbbreviationValidator = RegexValidator(
    r'^[a-z]*[-]?$',
    'Only lower case characters are allowed, optionally followed by "-".'
)


class TheaterDetailsForm(forms.Form):
    abbreviation = forms.CharField(
        empty_value='EMPTY',
        label='Abbreviation',
        validators=[TheaterAbbreviationValidator]
    )
