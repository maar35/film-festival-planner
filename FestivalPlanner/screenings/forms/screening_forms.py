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
    festival_screenings = None
    getter = None
    eligible_films_count_by_rating = None
    planned_screenings_count = None
    planned_screenings_count_by_rating = None
    session = None

    # TODO: Protect against fan-switching!

    @classmethod
    def auto_plan_screenings(cls, session, eligible_films):
        pr_debug('start', with_time=True)
        cls.session = session
        cls.form_errors = []
        initialize_log(session, 'Plan screenings')

        # Check existence of already planned screenings.
        auto_planned = Screening.screenings.filter(film__in=eligible_films, auto_planned=True)
        if auto_planned:
            add_log(session, f'{len(auto_planned)} screenings already planned, Bailing out')
            pr_debug('stopped', with_time=True)
            return False

        # Initialize planning.
        indent = 0
        cls._set_screening_status_getter(session)
        sorted_ratings = sorted(FilmFanFilmRating.get_eligible_ratings(), reverse=True)
        ratings = [str(r) for r in sorted_ratings]
        ratings.extend([f'{r}?' for r in sorted_ratings])
        add_log(session, f'Planning {len(eligible_films) if eligible_films else "0"} films')
        add_log(session, f'Ratings considered are {", ".join(ratings)}')
        transaction_committed = True
        cls.eligible_films_count_by_rating = {}
        cls.planned_screenings_count = 0
        cls.planned_screenings_count_by_rating = {}

        # Plan the best screening for this fan for this festival.
        try:
            with transaction.atomic():
                for rating in ratings:
                    # Get the screenings to be considered for planning films with this rating.
                    rating_films = [f for f in eligible_films if f.rating_string() == str(rating)]
                    cls.eligible_films_count_by_rating[rating] = len(rating_films)
                    add_log(session, f'{len(rating_films)} films with rating {rating}')
                    if not rating_films:
                        continue
                    rating_screenings = cls.get_eligible_screenings(rating_films)

                    # Plan films with this rating.
                    indent += 1
                    add_log(session, f'{rating_screenings.count()} screenings with rating {rating}', indent=indent)
                    cls._plan_rating_screenings(rating, rating_screenings, rating_films, indent)

                    if cls.planned_screenings_count_by_rating[rating]:
                        # Report the results of the planning.
                        planned_screenings_count = cls.planned_screenings_count_by_rating[rating]
                        text = f'{planned_screenings_count} screenings planned with rating {rating}'
                        add_log(session, text, indent=indent)

                        # Check whether there are eligible films with this rating left unplanned.
                        if rating_films:
                            text = f'{len(rating_films)} films with rating {rating} not planned:'
                            add_log(session, text, indent=indent)
                            indent += 1
                            for not_planned_film in rating_films:
                                add_log(session, f'{str(not_planned_film)}', indent=indent)
                            indent -= 1
                        else:
                            film_count = cls.eligible_films_count_by_rating[rating]
                            add_log(session, f'All {film_count} films planned', indent=indent)

                    indent -= 1
        except Exception as e:
            cls._log_error(e, f'{cls.planned_screenings_count} updates rolled back')
            transaction_committed = False
            cls.planned_screenings_count = 0

        add_log(session, f'{cls.planned_screenings_count} screenings planned')
        pr_debug('done', with_time=True)
        return transaction_committed

    @classmethod
    def undo_auto_planning(cls, session, festival):
        transaction_committed = True
        cls.form_errors = []
        initialize_log(session, 'Undo automatic planning')
        manager = Screening.screenings
        fan = current_fan(session)
        add_log(session, f'Undoing automatic planning of {festival}')

        # Find the automatically planned screenings.
        kwargs = {
            'film__festival': festival,
            'auto_planned': True,
        }
        auto_planned_screenings = manager.filter(**kwargs)
        add_log(session, f'{auto_planned_screenings.count()} auto planned screenings')

        # Undo the planning.
        try:
            with transaction.atomic():
                for screening in auto_planned_screenings:
                    screening.auto_planned = False
                    AttendanceForm.update_attendance(screening, fan, attends=False)
                updated_count = manager.bulk_update(auto_planned_screenings, ['auto_planned'])
                add_log(session, f'{updated_count} screenings updated')
        except Exception as e:
            cls._log_error(e, 'Transaction rolled back')
            transaction_committed = False

        return transaction_committed

    @classmethod
    def get_eligible_screenings(cls, films, auto_planned=False):
        kwargs = {
            'film__in': films,
            'auto_planned': auto_planned,
            'screen__theater__priority': Theater.Priority.HIGH,
        }
        eligible_screenings = Screening.screenings.filter(**kwargs)
        return eligible_screenings

    @classmethod
    def _set_screening_status_getter(cls, session):
        festival = current_festival(session)
        cls.festival_screenings = Screening.screenings.filter(film__festival=festival)
        add_log(session, f'{len(cls.festival_screenings)} festival screenings')
        cls.getter = ScreeningStatusGetter(session, cls.festival_screenings)

    @classmethod
    def _get_sorted_eligible_screenings(cls, screenings):
        getter = cls.getter
        try:
            tuple_list = []
            for screening in screenings:
                attendants = [fan for fan in getter.get_attendants(screening) if fan != getter.fan]
                tuple_list.append((screening, len(attendants), screening.start_dt))
            sorted_screenings = [s for s, a, d in sorted(tuple_list, key=itemgetter(1, 2), reverse=True)]
        except Exception as e:
            cls._add_error([f'{e}'])
            raise e
        return sorted_screenings

    @classmethod
    def _plan_rating_screenings(cls, rating, eligible_screenings, films, indent):
        sorted_eligible_screenings = cls._get_sorted_eligible_screenings(eligible_screenings)
        indent += 1
        for eligible_screening in sorted_eligible_screenings:
            if cls._screening_is_plannable(eligible_screening, films):
                # Update the screening.
                add_log(cls.session, f'Planning {eligible_screening} with film rating {rating}', indent=indent)
                eligible_screening.auto_planned = True
                AttendanceForm.update_attendance(eligible_screening, cls.getter.fan)
                eligible_screening.save()

                # Update the status of other screenings.
                cls.getter.update_attendances_by_screening(eligible_screening)
                if eligible_screening.film in films:
                    films.remove(eligible_screening.film)

                # Update statistics.
                cls.planned_screenings_count += 1
                try:
                    cls.planned_screenings_count_by_rating[rating] += 1
                except KeyError:
                    cls.planned_screenings_count_by_rating[rating] = 1
        indent -= 1

    @classmethod
    def _get_screening_status(cls, screening):
        attendants = cls.getter.get_attendants(screening)
        return cls.getter.get_screening_status(screening, attendants)

    @classmethod
    def _screening_is_plannable(cls, screening, films):
        plannable = False
        status = cls._get_screening_status(screening)
        if cls._status_ok(status):
            plannable = cls._still_valid(screening, films) and cls._no_overlap(screening)
        return plannable

    @classmethod
    def _status_ok(cls, status):
        return status in [Screening.ScreeningStatus.FREE, Screening.ScreeningStatus.FRIEND_ATTENDS]

    @classmethod
    def _still_valid(cls, screening, films):
        valid_screenings = Screening.screenings.filter(film__in=films)
        return valid_screenings.contains(screening)

    @classmethod
    def _no_overlap(cls, eligible_screening):
        screenings = cls.festival_screenings
        overlap_screenings = [s for s in screenings if cls._overlaps_attended(s, eligible_screening)]
        return not overlap_screenings

    @classmethod
    def _overlaps_attended(cls, day_screening, eligible_screening):
        overlaps_attended = False
        attends = cls.getter.attends_by_screening[day_screening]
        if attends and day_screening.overlaps(eligible_screening, use_travel_time=True):
            overlaps_attended = True
        return overlaps_attended

    @classmethod
    def _add_error(cls, errors):
        def pr_trace(frm):
            try:
                frame_infos = inspect.trace()
                for info in frame_infos:
                    cls.form_errors.append(f'{info.filename} line {info.lineno} in {info.function}')
                    cls.form_errors.extend(info.code_context)
                    skip_line()
            finally:
                del frm

        def skip_line():
            cls.form_errors.append('')

        cls.form_errors.extend(errors)
        skip_line()
        pr_trace(inspect.currentframe())

    @classmethod
    def _log_error(cls, error, msg):
        cls._add_error([f'{error}', f'{msg}'])
        add_log(cls.session, f'ERROR {error}, {msg}')


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
