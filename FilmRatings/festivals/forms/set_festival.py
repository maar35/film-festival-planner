from django import forms
from festivals.models import Festival


class FestivalEdition(forms.Form):
    festival = forms.ChoiceField(
        label='Pick a festival',
        choices=[(festival.id, festival) for festival in Festival.festivals.order_by('-start_date')]
    )


class TestNearestFestival(forms.Form):
    sample_date = forms.DateField(
        widget=forms.SelectDateWidget(years=[2019, 2020, 2021, 2022, 2023, 2024, 2025])
    )
