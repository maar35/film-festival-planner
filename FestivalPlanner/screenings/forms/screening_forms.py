from django import forms
from django.db import transaction

from festival_planner.tools import add_log, initialize_log
from festivals.models import current_festival
from loader.forms.loader_forms import CalendarDumper
from screenings.models import Attendance


def dump_calendar_items(session, attended_screening_rows):
    initialize_log(session, 'Dump calendar')
    add_log(session, f'Dumping {len(attended_screening_rows) if attended_screening_rows else 0} calendar items.')
    festival = current_festival(session)
    if CalendarDumper(session).dump_objects(festival.agenda_file(), objects=attended_screening_rows):
        add_log(session, 'Please adapt and run script MoviesToAgenda.scpt in the Tools directory.')


class DummyForm(forms.Form):
    dummy_field = forms.SlugField(required=False)


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

