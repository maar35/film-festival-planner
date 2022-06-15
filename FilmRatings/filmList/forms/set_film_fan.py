from django import forms
from filmList.models import FilmFan


class User(forms.Form):
    logged_in_fan = forms.ChoiceField(
        label='Select a film fan',
        choices=[(fan.name, fan) for fan in FilmFan.film_fans.order_by('seq_nr')],
    )

