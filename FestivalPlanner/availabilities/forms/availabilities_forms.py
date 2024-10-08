from copy import deepcopy

from django import forms
from django.db.transaction import atomic

from festival_planner.tools import add_log


class AvailabilityForm(forms.Form):
    dummy = forms.SlugField(required=False)

    @classmethod
    def add_availability(cls, session, new_obj):
        try:
            with atomic():
                cls._insert_if_has_length(session, new_obj)
        except Exception as e:
            cls._handle_exception(session, e, new_obj)

    @classmethod
    def delete_part_of_availability(cls, session, original_obj, first_remaining_obj, last_remaining_obj):
        try:
            with atomic():
                current_obj = deepcopy(original_obj)
                original_obj.delete()
                add_log(session, f'"{original_obj}" deleted.')
                current_obj = deepcopy(first_remaining_obj)
                cls._insert_if_has_length(session, first_remaining_obj)
                current_obj = deepcopy(last_remaining_obj)
                cls._insert_if_has_length(session, last_remaining_obj)
        except Exception as e:
            cls._handle_exception(session, e, current_obj)

    @classmethod
    def merge_availabilities(cls, session, merge_objects, new_obj):
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
            cls._handle_exception(session, e, current_obj)

    @staticmethod
    def _insert_if_has_length(session, availability_obj):
        if availability_obj.start_dt == availability_obj.end_dt:
            add_log(session, f'"{availability_obj}" not inserted, no period.')
        else:
            availability_obj.save()
            add_log(session, f'"{availability_obj}" inserted.')

    @staticmethod
    def _handle_exception(session, exception, availability_obj):
        add_log(session, f'"{availability_obj}" not processed.')
        add_log(session, f'Exception: {exception}')
        add_log(session, 'Database rolled back.')
        raise Exception(exception)
