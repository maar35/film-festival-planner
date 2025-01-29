from django.core.exceptions import ValidationError
from django.utils.translation import gettext_lazy as gettext
from django.core.validators import RegexValidator
from django.forms import Form, CharField

from theaters.models import Theater

TheaterAbbreviationValidator = RegexValidator(
    r'^[a-z]*[-]?$',
    'Only lower case characters are allowed,optionally followed by "-".'
)


def validate_theater_abbreviation_unique(value):
    try:
        _ = Theater.theaters.get(abbreviation=value)
    except Theater.DoesNotExist:
        pass
    else:
        raise ValidationError(gettext('Theater abbreviation "%(value)s" already exists.'),
                              params={'value': value})


ScreenAbbreviationValidator = RegexValidator(
    r'^[a-z]*[0-9]*$',
    'Only lower case characters and digits are allowed, both optional.'
    ' When both are present, characters must precede digits.'
)


class TheaterDetailsForm(Form):
    abbreviation = CharField(
        empty_value='EMPTY',
        label='Theater abbreviation',
        validators=[TheaterAbbreviationValidator, validate_theater_abbreviation_unique],
        required=False,
    )


class TheaterScreenDetailsForm(Form):
    screen_abbreviation = CharField(
        empty_value='EMPTY',
        label='Screen abbreviation',
        validators=[ScreenAbbreviationValidator],
        required=False,
    )
