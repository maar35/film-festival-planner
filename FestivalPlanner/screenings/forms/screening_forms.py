import heapq
from operator import attrgetter

from django import forms
from django.db import transaction

from festival_planner.debug_tools import pr_debug, ExceptionTracer
from festival_planner.screening_status_getter import ScreeningStatusGetter
from festival_planner.tools import add_log, initialize_log
from festivals.models import current_festival
from films.models import FilmFanFilmRating, current_fan, get_rating_as_int, fan_rating
from loader.forms.loader_forms import CalendarDumper
from screenings.models import Attendance, Screening, get_available_filmscreenings
from theaters.models import Theater


class DummyForm(forms.Form):
    dummy_field = forms.SlugField(required=False)


class PlannerSortKeyKeeper:
    reverse_by_attr_name = {
        'highest_rating': True,
        'second_highest_rating': True,
        'attending_friend_count': True,
        'q_and_a': True,
        'filmscreening_count': False,
        'duration': False,
        'start_dt': True,
    }

    def __init__(self, screening, fan, attending_friends):
        self.screening = screening
        film = screening.film
        self.highest_rating, self.second_highest_rating = self.get_highest_ratings(film)
        self.attending_friend_count = len(attending_friends)
        self.q_and_a = screening.q_and_a
        self.filmscreening_count = len(get_available_filmscreenings(film, fan))
        self.duration = screening.duration()
        self.start_dt = screening.start_dt

    def __repr__(self):
        return f'{__name__} object from {str(self.screening)}, {self.attending_friend_count=}'

    @classmethod
    def get_sorted_screenings(cls, sort_keys):
        for attr_name, reverse in reversed(cls.reverse_by_attr_name.items()):
            sort_keys.sort(key=attrgetter(attr_name), reverse=reverse)
        return [sort_key.screening for sort_key in sort_keys]

    @staticmethod
    def get_highest_ratings(film):
        film_ratings = FilmFanFilmRating.film_ratings.filter(film=film)
        highest_two = heapq.nlargest(2, film_ratings)
        highest_rating = get_rating_as_int(highest_two[0] if highest_two else None)
        second_rating = get_rating_as_int(highest_two[1] if len(highest_two) > 1 else highest_rating)
        return highest_rating, second_rating


class PlannerReporter:
    def __init__(self, session, action):
        self.session = session
        self.highest_rating_by_film = {}
        self.film_count_by_rating = {}
        self.screening_count_by_rating = {}
        self.planned_screenings_by_rating = {}
        self.not_planned_films_by_rating = {}
        self.planned_film_count_by_rating = {}
        initialize_log(session, action)
        self.indent = 0
        self.ratings = sorted(FilmFanFilmRating.get_eligible_ratings(), reverse=True)
        for rating in self.ratings:
            self.film_count_by_rating[rating] = 0
            self.screening_count_by_rating[rating] = 0
            self.planned_screenings_by_rating[rating] = []

    def set_film_dicts(self, films):
        self.highest_rating_by_film = {f: self._get_highest_rating(f) for f in films}
        for film in films:
            rating = self.highest_rating_by_film[film]
            self.film_count_by_rating[rating] += 1

    def set_screening_count_by_rating(self, screenings):
        for screening in screenings:
            self.screening_count_by_rating[self.highest_rating_by_film[screening.film]] += 1

    def report(self, not_planned_films):
        self._set_not_planned_films_by_rating(not_planned_films)
        for rating in self.ratings:
            with_rating_str = f'with rating {int(rating)}'
            film_count = self.film_count_by_rating[rating]
            self._add_log(f'{film_count} films {with_rating_str}')
            if film_count:
                planned_screenings = self.planned_screenings_by_rating[rating]
                self.indent += 1
                self._add_log(f'{self.screening_count_by_rating[rating]} screenings {with_rating_str}')
                self.indent += 1
                for screening in planned_screenings:
                    self._add_log(f'Planning {screening}')
                self.indent -= 1
                if len(planned_screenings) == film_count:
                    self._add_log(f'All {film_count} films planned')
                else:
                    self._add_log(f'{len(planned_screenings)} screenings planned {with_rating_str}')
                    self._add_log(f'Not planned:')
                    self.indent += 1
                    for film in self.not_planned_films_by_rating[rating]:
                        self._add_log(f'{film}')
                self.indent -= 1

    @staticmethod
    def _get_highest_rating(film):
        highest_rating, _ = PlannerSortKeyKeeper.get_highest_ratings(film)
        return highest_rating

    def _set_not_planned_films_by_rating(self, not_planned_films):
        self.not_planned_films_by_rating = {rating: [] for rating in self.ratings}
        for film in not_planned_films:
            rating = self.highest_rating_by_film[film]
            self.not_planned_films_by_rating[rating].append(film)

    def _add_log(self, text):
        add_log(self.session, text, indent=self.indent)


class PlannerForm(DummyForm):
    tracer = None
    getter = None
    reporter = None
    festival_screenings = None
    planned_screenings_count = None
    session = None

    @classmethod
    def auto_plan_screenings(cls, session, eligible_films):
        pr_debug('start', with_time=True)
        cls.session = session
        cls.tracer = ExceptionTracer()
        cls.reporter = PlannerReporter(session, 'Plan screenings')

        # Check existence of already planned screenings.
        auto_planned = Screening.screenings.filter(film__in=eligible_films, auto_planned=True)
        if auto_planned:
            add_log(session, f'{len(auto_planned)} screenings already planned, Bailing out')
            pr_debug('stopped', with_time=True)
            return False

        # Initialize planning.
        cls._set_screening_status_getter(session)
        cls.reporter.set_film_dicts(eligible_films)
        add_log(session, f'Planning {len(eligible_films) if eligible_films else "0"} films')
        transaction_committed = True
        cls.planned_screenings_count = 0

        # Plan the best screenings for this fan for this festival.
        try:
            with transaction.atomic():
                eligible_screenings = cls.get_eligible_screenings(eligible_films)
                cls.reporter.set_screening_count_by_rating(eligible_screenings)
                cls._plan_rating_screenings(eligible_screenings, eligible_films)
        except Exception as e:
            cls._log_error(e, f'{cls.planned_screenings_count} updates rolled back')
            transaction_committed = False
            return transaction_committed

        cls.reporter.report(eligible_films)
        add_log(session, f'{cls.planned_screenings_count} screenings planned')
        pr_debug('done', with_time=True)
        return transaction_committed

    @classmethod
    def undo_auto_planning(cls, session, festival):
        transaction_committed = True
        cls.tracer = ExceptionTracer()
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
    def get_sorted_eligible_screenings(cls, screenings, fan=None):
        sort_keys = []
        for screening in screenings:
            attending_friends = screening.attending_friends(fan) if fan else cls.getter.get_attending_friends(screening)
            fan = fan or current_fan(cls.session)
            sort_keys.append(PlannerSortKeyKeeper(screening, fan, attending_friends))
        sorted_screenings = PlannerSortKeyKeeper.get_sorted_screenings(sort_keys)
        return sorted_screenings

    @classmethod
    def _set_screening_status_getter(cls, session):
        festival = current_festival(session)
        cls.festival_screenings = Screening.screenings.filter(film__festival=festival)
        add_log(session, f'{len(cls.festival_screenings)} festival screenings')
        cls.getter = ScreeningStatusGetter(session, cls.festival_screenings)

    @classmethod
    def _plan_rating_screenings(cls, eligible_screenings, films):
        sorted_eligible_screenings = cls.get_sorted_eligible_screenings(eligible_screenings)
        for eligible_screening in sorted_eligible_screenings:
            if cls._screening_is_plannable(eligible_screening, films):
                rating, _ = PlannerSortKeyKeeper.get_highest_ratings(eligible_screening.film)

                # Update the screening.
                cls.reporter.planned_screenings_by_rating[rating].append(eligible_screening)
                eligible_screening.auto_planned = True
                AttendanceForm.update_attendance(eligible_screening, cls.getter.fan)
                eligible_screening.save()

                # Update the status of other screenings.
                cls.getter.update_attendances_by_screening(eligible_screening)
                if eligible_screening.film in films:
                    films.remove(eligible_screening.film)

                # Update statistics.
                cls.planned_screenings_count += 1

    @classmethod
    def _get_screening_status(cls, screening):
        attendants = cls.getter.get_attendants(screening)
        return cls.getter.get_screening_status(screening, attendants)

    @classmethod
    def _screening_is_plannable(cls, screening, films):
        plannable = False
        if cls.getter.fits_availability(screening):
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
    def _log_error(cls, error, msg):
        cls.tracer.add_error([f'{error}', f'{msg}'])
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
