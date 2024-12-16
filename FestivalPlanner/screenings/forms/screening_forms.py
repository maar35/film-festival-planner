import datetime
import inspect

from django import forms
from django.db import transaction

from festival_planner.debug_tools import debug, pr_debug
from festival_planner.screening_status_getter import ScreeningStatusGetter
from festival_planner.tools import add_log, initialize_log
from festivals.models import current_festival
from films.models import FilmFanFilmRating, current_fan
from loader.forms.loader_forms import CalendarDumper
from screenings.models import Attendance, Screening
from theaters.models import Theater


class PlannerForm(forms.Form):
    dummy_field = forms.SlugField(required=False)
    planned_screenings_count = None

    def __init__(self, session):
        super().__init__()
        # TODO: Protect against fan-switching!

    @classmethod
    def auto_plan_screenings(cls, session, eligible_films):
        pr_debug('start', with_time=True)
        initialize_log(session, 'Plan screenings')
        indent = 0
        fan = current_fan(session)
        sorted_ratings = sorted(FilmFanFilmRating.get_eligible_ratings(), reverse=True)
        ratings = [str(r) for r in sorted_ratings]
        ratings.extend([f'{r}?' for r in sorted_ratings])
        add_log(session, f'Planning {len(eligible_films)} films.')
        add_log(session, f'Ratings considered are {", ".join(ratings)}')
        transaction_committed = True
        cls.planned_screenings_count = 0
        try:
            with transaction.atomic():
                for rating in ratings:
                    films = [f for f in eligible_films if f.rating_string() == str(rating)]
                    add_log(session, f'{len(films)} films with rating {rating}.')
                    if not films:
                        continue
                    rating_screenings = cls.get_eligible_screenings(films)
                    indent += 1
                    add_log(session, f'{rating_screenings.count()} screenings with rating {rating}.', indent=indent)
                    dates = rating_screenings.dates('start_dt', 'day').reverse()
                    if dates:
                        add_log(session, f'dates {", ".join([d.isoformat() for d in dates])}.', indent=indent)

                    # Plan the screenings for this fan and rating.
                    indent += 1
                    for day in dates:
                        cls._plan_fan_rating_day_screenings(session, fan, rating, day, rating_screenings, indent)
                    indent -= 2
        except Exception as e:
            transaction_committed = False
            msg = f'{cls.planned_screenings_count} updates rolled back.'
            add_log(session, f'{debug(frame=inspect.currentframe())}, {e}, {msg}')
            cls.planned_screenings_count = 0
        add_log(session, f'{cls.planned_screenings_count} screenings planned.')
        pr_debug('done', with_time=True)
        return transaction_committed

    @classmethod
    def get_eligible_screenings(cls, films, auto_planned=False):
        kwargs = {
            'film__in': films,
            'auto_planned': auto_planned,
            'screen__theater__priority': Theater.Priority.HIGH,
        }
        eligible_screenings = Screening.screenings.filter(**kwargs).order_by('-start_dt')
        return eligible_screenings

    @classmethod
    def _plan_fan_rating_day_screenings(cls, session, fan, rating, day, screenings, indent):
        add_log(session, f'date {day}.', indent=indent)
        eligible_screenings = screenings.filter(start_dt__date=day)
        day_screenings = Screening.screenings.filter(start_dt__date=day)
        add_log(session, f'{len(day_screenings)} day screenings', indent=indent)
        if not day_screenings:
            return
        getter = ScreeningStatusGetter(session, day_screenings)
        indent += 1
        prev_planned_screening = None
        for screening in eligible_screenings:
            # Find out whether the screening is plannable.
            attendants = getter.get_attendants(screening)
            status = getter.get_screening_status(screening, attendants)
            if status in [Screening.ScreeningStatus.FREE, Screening.ScreeningStatus.FRIEND_ATTENDS]:
                if prev_planned_screening and screening.overlaps(prev_planned_screening, use_travel_time=True):
                    continue
                # Update the screening.
                add_log(session, f'Planning {screening} with film rating {rating}.', indent=indent)
                screening.auto_planned = True
                AttendanceForm.update_attendance(screening, fan)
                screening.save()
                prev_planned_screening = screening
                cls.planned_screenings_count += 1

        indent -= 1

    @classmethod
    def undo_auto_planning(cls, session, festival):
        initialize_log(session, 'Undo automatic planning')
        manager = Screening.screenings
        fan = current_fan(session)
        add_log(session, f'Undoing automatic planning of {festival}.')
        kwargs = {
            'film__festival': festival,
            'auto_planned': True,
        }
        auto_planned_screenings = manager.filter(**kwargs)
        add_log(session, f'{auto_planned_screenings.count()} auto planned screenings.')
        try:
            with transaction.atomic():
                for screening in auto_planned_screenings:
                    screening.auto_planned = False
                    AttendanceForm.update_attendance(screening, fan, attends=False)
                updated_count = manager.bulk_update(auto_planned_screenings, ['auto_planned'])
                add_log(session, f'{updated_count} screenings updated.')
        except Exception as e:
            # transaction_committed = False
            add_log(session, f'{debug(frame=inspect.currentframe())}, {e}, transaction rolled back')


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

    @classmethod
    def update_attendances(cls, session, screening, changed_attendance_by_fan, update_log):
        transaction_committed = True
        try:
            with transaction.atomic():
                for fan, attends in changed_attendance_by_fan.items():
                    cls.update_attendance(screening, fan, attends=attends)
                    update_log(fan, attends)
        except Exception as e:
            transaction_committed = False
            add_log(session, f'{e}, transaction rolled back')
        return transaction_committed

    @classmethod
    def update_attendance(cls, screening, fan, attends=True):
        manager = Attendance.attendances
        kwargs = {'screening': screening, 'fan': fan}
        if attends:
            manager.update_or_create(**kwargs)
        else:
            existing_attendances = manager.filter(**kwargs)
            if len(existing_attendances) > 0:
                existing_attendances.delete()
