from django import forms

from authentication.models import FilmFan
from availabilities.models import Availabilities


class AvailabilityForm(forms.Form):
    dummy = forms.SlugField(required=False)

    @staticmethod
    def add_availability(fan_name=None, start_dt=None, end_dt=None):
        fan = FilmFan.film_fans.get(name=fan_name)
        Availabilities.availabilities.create(fan=fan, start_dt=start_dt, end_dt=end_dt)
