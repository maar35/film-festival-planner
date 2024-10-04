from copy import deepcopy

from django import forms
from django.db.transaction import atomic

from authentication.models import FilmFan
from availabilities.models import Availabilities
from festival_planner.tools import add_log


class AvailabilityForm(forms.Form):
    dummy = forms.SlugField(required=False)

    @staticmethod
    def add_availability(session, fan_name=None, start_dt=None, end_dt=None):
        add_log(session, 'Add availability.')
        fan = FilmFan.film_fans.get(name=fan_name)
        new_obj = Availabilities.availabilities.create(fan=fan, start_dt=start_dt, end_dt=end_dt)
        add_log(session, f'"{new_obj}" inserted.')

    @staticmethod
    def delete_part_of_availability(session, original_obj, first_remaining_obj, last_remaining_obj):
        try:
            with atomic():
                original_obj.delete()
                add_log(session, f'"{original_obj}" deleted.')
                AvailabilityForm._insert_if_has_length(session, first_remaining_obj)
                AvailabilityForm._insert_if_has_length(session, last_remaining_obj)
        except Exception as e:
            add_log(session, f'Exception: {e}.')
            add_log(session, 'Database rolled back.')

    @staticmethod
    def merge_availabilities(session, merge_objects, new_obj):
        current_obj = None
        try:
            with atomic():
                for merge_object in merge_objects:
                    current_obj = deepcopy(merge_object)
                    merge_object.delete()
                    add_log(session, f'"{merge_object}" deleted.')
                new_obj.save()
                add_log(session, f'"{new_obj}" inserted.')
        except Exception as e:
            add_log(session, f'"{current_obj}" not processed.')
            add_log(session, f'Exception: {e}')
            add_log(session, 'Database rolled back.')

    @staticmethod
    def _insert_if_has_length(session, availability_obj):
        if availability_obj.start_dt == availability_obj.end_dt:
            add_log(session, f'"{availability_obj}" not inserted, no period.')
        else:
            availability_obj.save()
            add_log(session, f'"{availability_obj}" inserted.')
