import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, FormView
from django.views.generic.detail import SingleObjectMixin

from authentication.models import FilmFan
from festival_planner.cookie import Cookie
from festival_planner.debug_tools import pr_debug
from festival_planner.fan_action import FanAction
from festival_planner.tools import add_base_context, get_log, unset_log, initialize_log, add_log
from festivals.models import current_festival
from films.models import current_fan, initial, MINUTES_STR
from films.views import ResultsView
from screenings.forms.screening_forms import DummyForm, AttendanceForm
from screenings.models import Screening, Attendance
from theaters.models import Theater


class FestivalDay:
    day_str_format = '%a %Y-%m-%d'

    def __init__(self, cookie_key):
        self.festival = None
        self.day_cookie = Cookie(cookie_key)

    def get_date(self, session):
        day_str = self.day_cookie.get(session)
        return datetime.date.fromisoformat(day_str)

    def get_datetime(self, session, time):
        date = self.get_date(session)
        return datetime.datetime.combine(date, time)

    def get_str(self, session):
        date = self.get_date(session)
        return date.strftime(self.day_str_format)

    def set_str(self, session, day_str, is_choice=False):
        day_str = day_str.split()[1] if is_choice else day_str
        self.day_cookie.set(session, day_str)

    def get_festival_days(self):
        day = self.festival.start_date
        delta = datetime.timedelta(days=1)
        all_days = self.festival.end_date - self.festival.start_date + delta
        day_choices = []
        for factor in range(all_days.days):
            day_choices.append((day + factor * delta).strftime(self.day_str_format))
        return day_choices

    def check_session(self, session):
        self.festival = current_festival(session)
        day_str = self.day_cookie.get(session)
        if day_str:
            if day_str < self.festival.start_date.isoformat() or day_str > self.festival.end_date.isoformat():
                day_str = ''
        if not day_str:
            try:
                first_screening = (Screening.screenings.filter(film__festival=self.festival).earliest('start_dt'))
                day_str = first_screening.start_dt.date().isoformat()
            except Screening.DoesNotExist:
                day_str = self.festival.start_date.isoformat()
            self.day_cookie.set(session, day_str)
        return self.festival


class DaySchemaView(LoginRequiredMixin, View):
    """
    Class-based view to visualise the screenings of a festival day.
    """
    template_name = 'screenings/day_schema.html'
    current_day = FestivalDay('day')

    @staticmethod
    def get(request, *args, **kwargs):
        view = DaySchemaListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = DaySchemaFormView.as_view()
        return view(request, *args, **kwargs)


class DaySchemaListView(LoginRequiredMixin, ListView):
    template_name = DaySchemaView.template_name
    http_method_names = ['get']
    context_object_name = 'screen_rows'
    start_hour = datetime.time(hour=9)
    hour_count = 16
    pixels_per_hour = 120

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.day_screenings = None
        self.attendances_by_screening = None
        self.attends_by_screening = None
        self.has_attended_film_by_screening = None

    def setup(self, request, *args, **kwargs):
        pr_debug('start', with_time=True)
        super().setup(request, *args, **kwargs)
        festival = DaySchemaView.current_day.check_session(request.session)
        current_date = DaySchemaView.current_day.get_date(request.session)
        self.day_screenings = Screening.screenings.filter(film__festival=festival, start_dt__date=current_date)
        fan = current_fan(request.session)
        attendance_manager = Attendance.attendances
        self.attendances_by_screening = {s: attendance_manager.filter(screening=s) for s in self.day_screenings}
        self.attends_by_screening = {s: self.attendances_by_screening[s].filter(fan=fan) for s in self.day_screenings}
        self.has_attended_film_by_screening = {s: attendance_manager.filter(screening__film=s.film, fan=fan) for s in self.day_screenings}
        pr_debug('done', with_time=True)

    def get_queryset(self):
        pr_debug('start', with_time=True)
        screenings_by_screen = {}
        sorted_screenings = sorted(self.day_screenings, key=lambda s: str(s.screen))
        for screening in sorted(sorted_screenings, key=lambda s: s.screen.theater.priority, reverse=True):
            try:
                screenings_by_screen[screening.screen].append(screening)
            except KeyError:
                screenings_by_screen[screening.screen] = [screening]
        screen_rows = [self._get_screen_row(screen, screenings) for screen, screenings in screenings_by_screen.items()]
        pr_debug('done', with_time=True)
        return screen_rows

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        current_day_str = DaySchemaView.current_day.get_str(session)
        day_choices = DaySchemaView.current_day.get_festival_days()
        new_context = {
            'title': 'Screenings Day Schema',
            'sub_header': 'Visualized screenings of the current festival day',
            'day': current_day_str,
            'day_choices': day_choices,
            'timescale': self._get_timescale(),
            'timebox_length': 60,
            'px_per_hour': self.pixels_per_hour,
            'log': get_log(session),
            'action': ScreeningDetailView.fan_action.get_refreshed_action(session),
        }
        unset_log(self.request.session)
        return add_base_context(self.request, super_context | new_context)

    def _get_screen_row(self, screen, screenings):
        screening_specs = [self._screening_spec(s) for s in screenings]
        screen_row = {
            'screen': screen,
            'color': Theater.color_by_priority[screen.theater.priority],
            'total_width': self.hour_count * self.pixels_per_hour,
            'screening_specs': sorted(screening_specs, key=lambda spec: spec['screening'].start_dt),
        }
        return screen_row

    def _get_start_dt(self):
        return DaySchemaView.current_day.get_datetime(self.request.session, self.start_hour)

    def _pixels_from_dt(self, dt):
        start_dt = self._get_start_dt()
        pixel_minutes = (dt - start_dt).total_seconds() / 60
        pixels = self.pixels_per_hour * pixel_minutes / 60
        return pixels

    def _screening_spec(self, screening):
        left_pixels = self._pixels_from_dt(screening.start_dt)
        attendants = self._get_attendants(screening)
        attendants_str = self._attendants_str(attendants)
        line_2 = f'{screening.start_dt.strftime("%H:%M")} - {screening.end_dt.strftime("%H:%M")} {attendants_str}'
        screening_spec = {
            'line_1': f'{screening.film.title}',
            'line_2': line_2,
            'screening': screening,
            'left': left_pixels,
            'width': self._pixels_from_dt(screening.end_dt) - left_pixels,
            'pair': self._screening_color_pair(screening, attendants),
        }
        return screening_spec

    def _get_timescale(self):
        hour_list = []
        delta = datetime.timedelta(hours=1)
        start_dt = self._get_start_dt()
        for hour in range(self.hour_count):
            dt = (start_dt + hour * delta)
            specs_by_hour = {
                'text': dt.strftime('%H:%M %Z'),
                'left': self._pixels_from_dt(dt),
            }
            hour_list.append(specs_by_hour)
        return hour_list

    def _attendants_str(self, attendants):
        attendance_str = ''
        for attendant in attendants:
            attendance_str += initial(attendant, self.request.session)
        return attendance_str

    def _get_screening_status(self, screening, attendants):
        if current_fan(self.request.session) in attendants:
            status = Screening.ScreeningStatus.ATTENDS
        elif attendants:
            status = Screening.ScreeningStatus.FRIEND_ATTENDS
        elif self._has_attended_film(screening):
            status = Screening.ScreeningStatus.ATTENDS_FILM
        else:
            status = self._get_overlap_status(screening)
        return status

    def _get_attendants(self, screening):
        attendances = self.attendances_by_screening[screening]
        attendants = [attendance.fan for attendance in attendances]
        return attendants

    def _has_attended_film(self, screening):
        """ Returns whether another screening of the same film is already attended. """
        film_screenings = self.has_attended_film_by_screening[screening]
        return film_screenings

    def _get_overlap_status(self, screening):
        status = Screening.ScreeningStatus.FREE
        overlapping_screenings = []
        no_travel_time_screenings = []
        for s in self.day_screenings:
            if self.attends_by_screening[s]:
                if s.start_dt.date() == screening.start_dt.date():
                    if screening.overlaps(s):
                        overlapping_screenings.append(s)
                    elif screening.overlaps(s, use_travel_time=True):
                        no_travel_time_screenings.append(s)
        if overlapping_screenings:
            status = Screening.ScreeningStatus.TIME_OVERLAP
        elif no_travel_time_screenings:
            status = Screening.ScreeningStatus.NO_TRAVEL_TIME
        return status

    def _screening_color_pair(self, screening, attendants):
        status = self._get_screening_status(screening, attendants)
        return Screening.color_pair_by_screening_status[status]


class DaySchemaFormView(LoginRequiredMixin, FormView):
    template_name = DaySchemaView.template_name
    form_class = DummyForm
    http_method_names = ['post']

    def form_valid(self, form):
        day_str = self.request.POST['day']
        DaySchemaView.current_day.set_str(self.request.session, day_str, is_choice=True)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('screenings:day_schema')


class ScreeningDetailView(LoginRequiredMixin, SingleObjectMixin, FormView):
    model = Screening
    form_class = AttendanceForm
    template_name = 'screenings/details.html'
    http_method_names = ['get', 'post']
    fan_action = FanAction('update')
    update_by_attends = {True: 'joins', False: "couldn't come"}
    fans = FilmFan.film_fans.all()
    object = None
    screening = None
    initial_attendance_by_fan = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        session = self.request.session
        initialize_log(request.session, 'Update attendances')
        self.screening = self.get_object()
        self.fan_action.init_action(session, screening=self.screening)
        manager = Attendance.attendances
        self.initial_attendance_by_fan = {f: bool(manager.filter(screening=self.screening, fan=f)) for f in self.fans}

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        duration = self.screening.end_dt - self.screening.start_dt
        fan_specs = []
        for fan in self.fans:
            attends = self.initial_attendance_by_fan[fan]
            fan_specs.append({
                'fan': fan.name,
                'attends': attends,
            })
        new_context = {
            'title': 'Screening Details',
            'subtitle': f'Screening of {self.screening.film}',
            'screening': self.screening,
            'duration': duration,
            'minutes': f'{duration.total_seconds() / 60:.0f}{MINUTES_STR}',
            'film_description': ResultsView.get_description(self.screening.film),
            'fan_specs': fan_specs,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    def form_valid(self, form):
        new_attendance_by_fan = {fan: fan.name in self.request.POST for fan in self.fans}
        self._update_attendance(new_attendance_by_fan)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('screenings:day_schema')

    def _update_attendance(self, new_attendance_by_fan):
        def update_log(film_fan, fan_attends):
            self.fan_action.add_update(session, f'{film_fan} {self.update_by_attends[fan_attends]}')

        session = self.request.session
        changed_attendance_by_fan = {}
        for fan, initial_attendance in self.initial_attendance_by_fan.items():
            attends = new_attendance_by_fan[fan]
            if initial_attendance != attends:
                changed_attendance_by_fan[fan] = attends
        if changed_attendance_by_fan:
            _ = AttendanceForm.update_attendances(session, self.screening, changed_attendance_by_fan, update_log)
        else:
            add_log(session, f'No attendances of {self.screening} were updated by {current_fan(session)}.')
