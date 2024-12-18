import datetime
import inspect
from operator import itemgetter

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


class DummyForm(forms.Form):
    dummy_field = forms.SlugField(required=False)


class PlannerForm(DummyForm):
    form_errors = None
    eligible_films_count_by_rating = None
    planned_screenings_count = None
    planned_screenings_count_by_rating = None
    session = None

    # TODO: Protect against fan-switching!

    @classmethod
    def auto_plan_screenings(cls, session, eligible_films):
        pr_debug('start', with_time=True)
        cls.form_errors = []
        cls.session = session
        initialize_log(session, 'Plan screenings')
        indent = 0
        fan = current_fan(session)
        sorted_ratings = sorted(FilmFanFilmRating.get_eligible_ratings(), reverse=True)
        ratings = [str(r) for r in sorted_ratings]
        ratings.extend([f'{r}?' for r in sorted_ratings])
        add_log(session, f'Planning {len(eligible_films)} films.')
        add_log(session, f'Ratings considered are {", ".join(ratings)}')
        transaction_committed = True
        cls.eligible_films_count_by_rating = {}
        cls.planned_screenings_count = 0
        cls.planned_screenings_count_by_rating = {}
        try:
            with transaction.atomic():
                for rating in ratings:
                    rating_films = [f for f in eligible_films if f.rating_string() == str(rating)]
                    cls.eligible_films_count_by_rating[rating] = len(rating_films)
                    add_log(session, f'{len(rating_films)} films with rating {rating}.')
                    if not rating_films:
                        continue
                    rating_screenings = cls.get_eligible_screenings(rating_films)
                    indent += 1
                    add_log(session, f'{rating_screenings.count()} screenings with rating {rating}.', indent=indent)
                    dates = rating_screenings.dates('start_dt', 'day').reverse()
                    if dates:
                        add_log(session, f'dates {", ".join([d.isoformat() for d in dates])}.', indent=indent)

                    # Plan the screenings for this fan and rating.
                    indent += 1
                    for day in dates:
                        cls._plan_fan_rating_day_screenings(session, fan, rating, day, rating_screenings, rating_films, indent)
                    if cls.planned_screenings_count_by_rating[rating]:
                        indent -= 1
                        add_log(
                            session,
                            f'{cls.planned_screenings_count_by_rating[rating]} screenings planned with rating {rating}.',
                            indent=indent)
                        add_log(session, f'Not planned films with rating {rating}:', indent=indent)
                        indent += 1
                    for not_planned_film in rating_films:
                        add_log(session, f'{str(not_planned_film)}', indent=indent)
                    indent -= 1
                    indent -= 1
        except Exception as e:
            transaction_committed = False
            msg = f'{cls.planned_screenings_count} updates rolled back'
            cls.form_errors.extend([f'{e}', f'{msg}'])
            add_log(session, f'{debug(frame=inspect.currentframe())}, {e}, {msg}.')
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
        eligible_screenings = Screening.screenings.filter(**kwargs)
        # eligible_screenings = Screening.screenings.filter(**kwargs).order_by('-start_dt')
        return eligible_screenings

    @classmethod
    def get_sorted_eligible_screenings(cls, screenings, getter):
        try:
            tuple_list = []
            for screening in screenings:     # .order_by('-start_dt'):
                attendants = [fan for fan in getter.get_attendants(screening) if fan != getter.fan]
                tuple_list.append((screening, len(attendants), screening.start_dt))
            sorted_screenings = [s for s, a, d in sorted(tuple_list, key=itemgetter(1, 2), reverse=True)]
        except Exception as e:
            cls.form_errors.extend([f'in {__name__}', f'{inspect.currentframe().f_code.co_name}'])
            raise e
        return sorted_screenings

    @classmethod
    def _plan_fan_rating_day_screenings(cls, session, fan, rating, day, screenings, films, indent):
        add_log(session, f'date {day}.', indent=indent)
        eligible_screenings = screenings.filter(start_dt__date=day)
        day_screenings = Screening.screenings.filter(start_dt__date=day)
        add_log(session, f'{len(day_screenings)} day screenings', indent=indent)
        if not day_screenings:
            return
        getter = ScreeningStatusGetter(session, day_screenings)
        sorted_eligible_screenings = cls.get_sorted_eligible_screenings(eligible_screenings, getter)
        if day == datetime.date(2024, 3, 29):
            add_log(session, f'Considered screenings of {day}:', indent=indent)
            indent += 1
            for screening in sorted_eligible_screenings:
                add_log(session, str(screening), indent=indent)
            indent -= 1
        indent += 1
        for eligible_screening in sorted_eligible_screenings:
            # Find out whether the screening is plannable.
            status = cls._get_screening_status(eligible_screening, getter)
            if cls._status_ok(status) and cls._no_overlap(eligible_screening, getter):
                # Update the screening.
                add_log(session, f'Planning {eligible_screening} with film rating {rating}.', indent=indent)
                eligible_screening.auto_planned = True
                AttendanceForm.update_attendance(eligible_screening, fan)
                eligible_screening.save()
                getter.update_attendances_by_screening(eligible_screening)
                cls.planned_screenings_count += 1
                try:
                    cls.planned_screenings_count_by_rating[rating] += 1
                except KeyError:
                    cls.planned_screenings_count_by_rating[rating] = 1
                films.remove(eligible_screening.film)
        indent -= 1

    @classmethod
    def _get_screening_status(cls, screening, getter):
        attendants = getter.get_attendants(screening)
        return getter.get_screening_status(screening, attendants)

    @classmethod
    def _status_ok(cls, status):
        return status in [Screening.ScreeningStatus.FREE, Screening.ScreeningStatus.FRIEND_ATTENDS]

    @classmethod
    def _no_overlap(cls, eligible_screening, getter):
        day_screenings = getter.day_screenings
        overlap_screenings = [s for s in day_screenings if cls._overlaps_attended(s, eligible_screening, getter)]
        return not overlap_screenings

    @classmethod
    def _overlaps_attended(cls, day_screening, eligible_screening, getter):
        overlaps_attended = False
        attends = getter.attends_by_screening[day_screening]
        if attends and day_screening.overlaps(eligible_screening, use_travel_time=True):
            overlaps_attended = True
        return overlaps_attended

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
            cls.form_errors.append(f'{e}')
            add_log(session, f'{debug(frame=inspect.currentframe())}, {e}, transaction rolled back')


class ScreeningCalendarForm(DummyForm):

    @classmethod
    def dump_calendar_items(cls, session, attended_screening_rows):
        initialize_log(session, 'Dump calendar')
        add_log(session, f'Dumping {len(attended_screening_rows) if attended_screening_rows else 0} calendar items.')
        festival = current_festival(session)
        if CalendarDumper(session).dump_objects(festival.agenda_file(), objects=attended_screening_rows):
            add_log(session, 'Please adapt and run script MoviesToAgenda.scpt in the Tools directory.')


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
