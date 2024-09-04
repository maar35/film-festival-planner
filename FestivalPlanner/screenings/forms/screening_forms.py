from django import forms
from django.db import transaction

from festival_planner.tools import add_log
from screenings.models import Attendance


class DummyForm(forms.Form):
    dummy_field = forms.SlugField(required=False)


def log_add(session, e):
    pass


class AttendanceForm(forms.Form):
    attendance = forms.CheckboxInput()

    @staticmethod
    def update_attendances(session, screening, changed_attendance_by_fan, update_log):
        manager = Attendance.attendances
        transaction_committed = True
        try:
            with transaction.atomic():
                for fan, attends in changed_attendance_by_fan.items():
                    kwargs = {'screening': screening, 'fan': fan}
                    if attends:
                        manager.update_or_create(**kwargs)
                    else:
                        existing_attendances = manager.filter(**kwargs)
                        if len(existing_attendances) > 0:
                            existing_attendances.delete()
                    update_log(fan, attends)
        except Exception as e:
            transaction_committed = False
            add_log(session, f'{e}, transaction rolled back')
        return transaction_committed

