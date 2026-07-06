from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import Form, CharField, BaseFormSet

from festival_planner.tools import add_log
from screenings.models import Screening

TheaterAbbreviationValidator = RegexValidator(
    r'^[a-z]*[-]?$',
    'Only lower case characters are allowed, optionally followed by "-".'
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
        max_length=24,
    )

    @staticmethod
    def delete_screen(session, screen):
        add_log(session, f'Deleting screen {screen.parse_name}.')
        screening_count = Screening.screenings.filter(screen=screen).count()
        add_log(session, f'{screening_count} screenings linked to this screen.')
        if screening_count:
            add_log(session, 'Screenings linked to this screen, bailing out.')
            return False

        count, _ = screen.delete()
        add_log(session, f'Deleted {count} screen{'s' if count > 1 else ''}.')
        return True


class TheaterScreenDetailsForm(Form):
    abbreviation = CharField(
        empty_value='EMPTY',
        label='Screen abbreviation',
        validators=[ScreenAbbreviationValidator],
        required=False,
    )


class TheaterScreenFormSet(BaseFormSet):
    def clean(self):
        """Check that no two screens of the same theater have the same abbreviation."""
        if any(self.errors):
            # Don't bother validating the formset unless each form is valid on its own.
            return

        abbreviations = set()
        for form in self.forms:
            abbreviation = form.cleaned_data.get('abbreviation')
            if abbreviation in abbreviations:
                non_form_error = f'Screen abbreviation "{abbreviation}" is duplicate.'
                validator_output = 'Screens of one theater must have distinct abbreviations.'
                message = [non_form_error, validator_output]
                raise ValidationError(message)
            abbreviations.add(abbreviation)
