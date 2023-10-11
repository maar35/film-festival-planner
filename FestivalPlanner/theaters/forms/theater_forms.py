from django.core.validators import RegexValidator
from django.forms import Form, CharField

TheaterAbbreviationValidator = RegexValidator(
    r'^[a-z]*[-]?$',
    'Only lower case characters are allowed,optionally followed by "-".'
)


ScreenAbbreviationValidator = RegexValidator(
    r'^[a-z]*[0-9]*$',
    'Only lower case characters and digits are allowed, both optional.'
    ' When both are present, characters must precede digits.'
)


class TheaterDetailsForm(Form):
    abbreviation = CharField(
        empty_value='EMPTY',
        label='Theater abbreviation',
        validators=[TheaterAbbreviationValidator],
        required=False,
    )


class TheaterScreenDetailsForm(Form):
    screen_abbreviation = CharField(
        empty_value='EMPTY',
        label='Screen abbreviation',
        validators=[ScreenAbbreviationValidator],
        required=False,
    )
