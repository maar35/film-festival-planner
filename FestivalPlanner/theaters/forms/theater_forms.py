from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.forms import Form, CharField, BaseFormSet

from festival_planner.tools import add_log
from screenings.models import Screening
from theaters.models import Theater

TheaterAbbreviationValidator = RegexValidator(
    r'^[a-z]*[-]?$',
    'In a theater abbreviation only lower case characters are allowed,'
    ' optionally followed by "-".'
)


ScreenAbbreviationValidator = RegexValidator(
    r'^[a-z]*[0-9]*$',
    'In a screen abbreviation only lower case characters and digits are'
    ' allowed, both optional. When both are present, characters must precede digits.'
)


class TheaterDetailsForm(Form):
    theater_initial_data = None
    theater = None
    abbreviation = CharField(
        empty_value='EMPTY',
        label='Theater abbreviation',
        validators=[TheaterAbbreviationValidator],
        required=False,
        max_length=24,
    )

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.initial = self.initial or TheaterDetailsForm.theater_initial_data

    def clean(self):
        """Check that no two theaters in the same city have the same abbreviation."""
        if any(self.errors):
            # Don't bother validating the form unless it is valid.
            return

        if self.has_changed():
            field = 'abbreviation'
            try:
                _ = Theater.theaters.get(abbreviation=self.data[field], city=self.theater.city)
            except Theater.DoesNotExist:
                pass    # Not duplicate.
            else:
                non_form_error = f'Theater abbreviation "{self.data[field]}" is duplicate.'
                validator_output = 'Theater abbreviations are unique within a city'
                exception = [non_form_error, validator_output]
                raise ValidationError(exception)

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
