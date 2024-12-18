import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, FormView
from django.views.generic.detail import SingleObjectMixin

from authentication.models import FilmFan
from availabilities.models import Availabilities
from availabilities.views import get_festival_dt, DAY_START_TIME, DAY_BREAK_TIME
from festival_planner.cookie import Filter, FestivalDay
from festival_planner.debug_tools import pr_debug
from festival_planner.fan_action import FanAction
from festival_planner.fragment_keeper import ScreeningFragmentKeeper, FRAGMENT_INDICATOR
from festival_planner.screening_status_getter import ScreeningStatusGetter
from festival_planner.tools import add_base_context, get_log, unset_log, initialize_log, add_log
from festivals.models import current_festival
from films.models import current_fan, initial, fan_rating, minutes_str, get_present_fans, Film, FilmFanFilmRating
from films.views import FilmDetailView
from screenings.forms.screening_forms import DummyForm, AttendanceForm, PlannerForm, \
    ScreeningCalendarForm
from screenings.models import Screening, Attendance, COLOR_PAIR_SELECTED, film_rating_strings
from theaters.models import Theater


class DaySchemaView(LoginRequiredMixin, View):
    """
    Class-based view to visualise the screenings of a festival day.
    """
    template_name = 'screenings/day_schema.html'
    current_day = FestivalDay('day')

    def dispatch(self, request, *args, **kwargs):
        self.current_day.day_cookie.handle_get_request(request)
        ScreeningStatusGetter.handle_screening_get_request(request)
        return super().dispatch(request, *args, **kwargs)

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
    fans = FilmFan.film_fans.all()
    start_hour = datetime.time(hour=9)
    hour_count = 16
    pixels_per_hour = 120

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.row_nr_by_object_id = None
        self.festival = None
        self.selected_screening = None
        self.selected_screening_props = None
        self.status_getter = None
        self.day_screenings = None
        self.attendances_by_screening = None
        self.attends_by_screening = None
        self.fragment_keeper = None

    def setup(self, request, *args, **kwargs):
        pr_debug('start', with_time=True)
        super().setup(request, *args, **kwargs)
        self.festival = DaySchemaView.current_day.check_session(request.session)
        current_date = DaySchemaView.current_day.get_date(request.session)
        self.selected_screening = ScreeningStatusGetter.get_selected_screening(request)
        self.day_screenings = Screening.screenings.filter(film__festival=self.festival, start_dt__date=current_date)
        self.status_getter = ScreeningStatusGetter(request.session, self.day_screenings)
        self.fragment_keeper = ScreeningFragmentKeeper('pk')
        pr_debug('done', with_time=True)

    def dispatch(self, request, *args, **kwargs):
        cookie = DaySchemaView.current_day.day_cookie
        cookie.handle_get_request(request)
        DaySchemaView.current_day.set_str(request.session, cookie.get(request.session))
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        pr_debug('start', with_time=True)
        screenings_by_screen = {}
        sorted_screenings = sorted(self.day_screenings, key=lambda s: str(s.screen))
        for screening in sorted(sorted_screenings, key=lambda s: s.screen.theater.priority, reverse=True):
            try:
                screenings_by_screen[screening.screen].append(screening)
            except KeyError:
                screenings_by_screen[screening.screen] = [screening]
        self.fragment_keeper.add_fragments(screenings_by_screen.keys())
        screen_rows = [self._get_screen_row(i, s, screenings_by_screen[s]) for i, s in enumerate(screenings_by_screen)]
        pr_debug('done', with_time=True)
        return screen_rows

    def get_context_data(self, **kwargs):
        def next_festival_day(choices, days):
            next_date = current_day.get_date(session) + datetime.timedelta(days=days)
            within_festival = next_date.strftime(FestivalDay.day_str_format) in choices
            return next_date.strftime(FestivalDay.date_str_format) if within_festival else None

        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        current_day = DaySchemaView.current_day
        current_day_str = current_day.get_str(session)
        day_choices = DaySchemaView.current_day.get_festival_days()
        availability_props = self._get_available_fan_props(session)
        selected_screening_props = self._get_selected_screening_props()
        new_context = {
            'title': 'Screenings Day Schema',
            'sub_header': 'Visualized screenings of the current festival day',
            'day_label': 'Festival day:',
            'day': current_day_str,
            'day_choices': day_choices,
            'prev_day': next_festival_day(day_choices, days=-1),
            'next_day': next_festival_day(day_choices, days=1),
            'first_day': day_choices[0].split()[1],
            'last_day': day_choices[-1].split()[1],
            'availability_props': availability_props,
            'film_title': self.selected_screening.film.title if self.selected_screening else '',
            'screening': self.selected_screening,
            'total_width': self.hour_count * self.pixels_per_hour,
            'selected_screening_props': selected_screening_props,
            'timescale': self._get_timescale(),
            'log': get_log(session),
            'action': ScreeningDetailView.fan_action.get_refreshed_action(session),
        }
        unset_log(session)
        return add_base_context(self.request, super_context | new_context)

    def _get_screen_row(self, screen_nr, screen, screenings):
        screening_props = [self._screening_prop(s) for s in screenings]
        selected = len([prop['selected'] for prop in screening_props if prop['selected']])
        fragment_name = self.fragment_keeper.get_fragment_name(screen_nr)
        screen_row = {
            'screen': screen,
            'fragment_name': fragment_name,
            'color': Theater.color_by_priority[screen.theater.priority],
            'total_width': self.hour_count * self.pixels_per_hour,
            'screening_props': sorted(screening_props, key=lambda prop: prop['screening'].start_dt),
            'background': COLOR_PAIR_SELECTED['background'] if selected else None,
        }
        return screen_row

    def _get_day_schema_start_dt(self):
        return DaySchemaView.current_day.get_datetime(self.request.session, self.start_hour)

    def _get_day_schema_end_dt(self):
        end_dt = self._get_day_schema_start_dt() + datetime.timedelta(hours=self.hour_count)
        return end_dt

    def _pixels_from_dt(self, dt):
        start_dt = self._get_day_schema_start_dt()
        pixel_minutes = (dt - start_dt).total_seconds() / 60
        pixels = self.pixels_per_hour * pixel_minutes / 60
        return pixels

    def _get_available_fan_props(self, session):
        date = DaySchemaView.current_day.get_date(session)
        dt_kwargs = {
            'start_dt__lte': get_festival_dt(date, DAY_BREAK_TIME),
            'end_dt__gte': get_festival_dt(date, DAY_START_TIME),
        }
        availabilities = Availabilities.availabilities.filter(**dt_kwargs)
        available_fan_dicts = availabilities.values('fan').distinct().order_by('fan__seq_nr')
        available_fans = [FilmFan.film_fans.get(id=fan_dict['fan']) for fan_dict in available_fan_dicts]
        fan_availability_props = [self._availability_props(date, availabilities, fan) for fan in available_fans]
        return fan_availability_props

    def _availability_props(self, date, availabilities, fan):
        periods = []
        for availability in availabilities.filter(fan=fan):
            start_dt = max(availability.start_dt, get_festival_dt(date, DAY_START_TIME))
            end_dt = min(availability.end_dt, get_festival_dt(date, DAY_BREAK_TIME))
            end_pixels_dt = min(end_dt, self._get_day_schema_end_dt())
            left_pixels = self._pixels_from_dt(start_dt)
            period = {
                'start_dt': start_dt,
                'end_dt': end_dt,
                'left': left_pixels,
                'width': self._pixels_from_dt(end_pixels_dt) - left_pixels,
            }
            periods.append(period)
        availability_props = {
            'fan': fan.name,
            'periods': periods,
        }
        return availability_props

    def _screening_prop(self, screening):
        attendants = self.status_getter.get_attendants(screening)
        status, pair = self._screening_color_pair(screening, attendants)

        selected = screening == self.selected_screening
        if selected:
            self._set_selected_screening_props(status, pair, attendants)

        left_pixels = self._pixels_from_dt(screening.start_dt)
        day = screening.start_dt.date().isoformat()
        line_2 = f'{screening.start_dt.strftime("%H:%M")} - {screening.end_dt.strftime("%H:%M")}'
        pair_selected = Screening.color_pair_selected_by_screening_status[status]
        festival_color = screening.film.festival.festival_color
        fans_rating_str, film_rating_str, rating_color = screening.film_rating_data(status)
        info_str = f'{"Q " if screening.q_and_a else ""}{fans_rating_str}'
        frame_color = pair_selected['color'] if selected else festival_color
        section_color = screening.film.subsection.section.color if screening.film.subsection else frame_color
        querystring = Filter.get_querystring(**{'day': day, 'screening': screening.pk})
        fragment = ScreeningFragmentKeeper.fragment_code(screening.screen.pk)
        screening_prop = {
            'screening': screening,
            'line_1': f'{screening.film.title}',
            'line_2': line_2,
            'left': left_pixels,
            'width': self._pixels_from_dt(screening.end_dt) - left_pixels,
            'pair': pair,
            'fan_ratings': fans_rating_str,
            'auto_planned': "𝛑" if screening.auto_planned else "",
            'film_rating': film_rating_str,
            'rating_color': rating_color,
            'selected': selected,
            'frame_color': frame_color,
            'section_color': section_color,
            'info_pair': pair_selected if selected else pair,
            'info_spot': info_str or 'info',
            'query_string': '' if selected else querystring,
            'fragment': f'{FRAGMENT_INDICATOR}header_screening' if selected else fragment,
        }
        return screening_prop

    def _get_timescale(self):
        hour_list = []
        delta = datetime.timedelta(hours=1)
        start_dt = self._get_day_schema_start_dt()
        for hour in range(self.hour_count):
            dt = (start_dt + hour * delta)
            props_by_hour = {
                'text': dt.strftime('%H:%M %Z'),
                'left': self._pixels_from_dt(dt),
            }
            hour_list.append(props_by_hour)
        return hour_list

    def _attendants_str(self, attendants):
        attendance_str = ''
        for attendant in attendants:
            attendance_str += initial(attendant, self.request.session)
        return attendance_str

    def _screening_color_pair(self, screening, attendants):
        status = self.status_getter.get_screening_status(screening, attendants)
        return status, Screening.color_pair_by_screening_status[status]

    def _get_filmscreening_props(self):
        session = self.request.session
        return ScreeningStatusGetter.get_filmscreening_props(session, self.selected_screening.film)

    def _get_selected_screening_props(self):
        return self.selected_screening_props

    def _set_selected_screening_props(self, status, pair, attendants):
        screening = self.selected_screening
        film = screening.film
        rating_by_fan = {fan: fan_rating(fan, film) for fan in self.fans}
        self.selected_screening_props = {
            'selected_screening': self.selected_screening,
            'status': status,
            'pair': pair,
            'attendants': ', '.join([attendant.name for attendant in attendants]),
            'ratings': ', '.join([f'{fan}: {rating.rating}' for fan, rating in rating_by_fan.items() if rating]),
            'film_duration': f'{minutes_str(screening.film.duration)}',
            'screening_duration': f'{minutes_str(screening.end_dt - screening.start_dt)}',
            'q_and_a': screening.str_q_and_a(),
            'description': FilmDetailView.get_description(film),
            'subsection': film.subsection,
            'film_screening_props': self._get_filmscreening_props(),
        }


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
    fans = None
    object = None
    screening = None
    initial_attendance_by_fan = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        initialize_log(request.session, 'Update attendances')
        self.fans = get_present_fans(self.request.session)
        self.screening = self.get_object()
        manager = Attendance.attendances
        self.initial_attendance_by_fan = {f: bool(manager.filter(screening=self.screening, fan=f)) for f in self.fans}

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        duration = self.screening.end_dt - self.screening.start_dt
        fan_props = [{'fan': fan.name, 'attends': self.initial_attendance_by_fan[fan]} for fan in self.fans]
        new_context = {
            'title': 'Screening Details',
            'screening': self.screening,
            'duration': duration,
            'minutes': minutes_str(duration),
            'film_description': FilmDetailView.get_description(self.screening.film),
            'fan_props': fan_props,
            'film_title': self.screening.film.title,
            'film_screening_props': self._get_filmscreening_props(),
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
            self.fan_action.init_action(session, screening=self.screening)
            _ = AttendanceForm.update_attendances(session, self.screening, changed_attendance_by_fan, update_log)
        else:
            add_log(session, f'No attendances of {self.screening} were updated by {current_fan(session)}.')

    def _get_filmscreening_props(self):
        session = self.request.session
        return ScreeningStatusGetter.get_filmscreening_props(session, self.screening.film)


class PlannerView(LoginRequiredMixin, View):
    template_name = 'screenings/planner.html'
    eligible_films = None
    festival = None

    @staticmethod
    def get(request, *args, **kwargs):
        view = PlannerListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = PlannerFormView.as_view()
        return view(request, *args, **kwargs)


class PlannerListView(LoginRequiredMixin, ListView):
    template_name = PlannerView.template_name
    http_method_names = ['get']
    context_object_name = 'planned_screening_rows'

    def __init__(self):
        super().__init__()
        self.planned_screening_count = None

    def setup(self, request, *args, **kwargs):
        pr_debug('start', with_time=True)
        super().setup(request, *args, **kwargs)
        # PlannerForm.form_errors = []
        PlannerView.festival = current_festival(request.session)
        PlannerView.eligible_films = self._get_eligible_films()
        pr_debug('done', with_time=True)

    def get_queryset(self):
        pr_debug('start', with_time=True)
        get_row = self._get_planned_screening_row
        films = PlannerView.eligible_films
        eligible_screenings = PlannerForm.get_eligible_screenings(films, auto_planned=True).order_by('start_dt')
        planned_screening_rows = [get_row(s) for s in eligible_screenings if s.auto_planned]
        self.planned_screening_count = len(planned_screening_rows)
        pr_debug('done', with_time=True)
        return planned_screening_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        new_context = {
            'title': 'Screenings Planner',
            'sub_header': 'Hit the button and plan your films automatically',
            'eligible_film_count': len(PlannerView.eligible_films),
            'planned_screening_count': self.planned_screening_count,
            'form_errors': PlannerForm.form_errors,
            'log': get_log(session),
        }
        unset_log(session)
        return add_base_context(self.request, super_context | new_context)

    @classmethod
    def _get_eligible_films(cls):
        manager = Film.films
        festival_films = manager.filter(festival=PlannerView.festival)
        eligible_ratings = FilmFanFilmRating.get_eligible_ratings()
        rating_films = festival_films.filter(filmfanfilmrating__rating__in=eligible_ratings).distinct()
        eligible_films = [f for f in rating_films if manager.filter(screening__film=f).exists()]
        return eligible_films

    @staticmethod
    def _get_planned_screening_row(screening):
        fans_rating_str, film_rating_str, _ = film_rating_strings(screening)
        planned_screening_row = {
            'start_dt': screening.start_dt,
            'end_dt': screening.end_dt,
            'screen_name': screening.screen.parse_name,
            'film': screening.film,
            'fan_ratings_str': fans_rating_str,
            'film_rating_str': film_rating_str,
        }
        return planned_screening_row


class PlannerFormView(LoginRequiredMixin, FormView):
    template_name = PlannerView.template_name
    form_class = PlannerForm
    http_method_names = ['post']

    def form_valid(self, form):
        post = self.request.POST
        if 'plan' in post:
            session = self.request.session
            _ = PlannerForm.auto_plan_screenings(session, PlannerView.eligible_films)
        elif 'undo' in post:
            session = self.request.session
            PlannerForm.undo_auto_planning(session, PlannerView.festival)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('screenings:planner')


class ScreeningCalendarView(LoginRequiredMixin, View):
    template_name = 'screenings/calendar.html'
    calendar_item_rows = None

    @staticmethod
    def get(request, *args, **kwargs):
        view = ScreeningCalendarListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = ScreeningCalendarFormView.as_view()
        return view(request, *args, **kwargs)


class ScreeningCalendarListView(LoginRequiredMixin, ListView):
    template_name = ScreeningCalendarView.template_name
    http_method_names = ['get']
    context_object_name = 'attended_screening_rows'

    def get_queryset(self):
        manager = Attendance.attendances
        session = self.request.session
        fan = current_fan(session)
        festival = current_festival(session)
        attendances = manager.filter(fan=fan, screening__film__festival=festival).order_by('screening__start_dt')
        attended_screenings = [self._get_attendance_row(attendance) for attendance in attendances]
        self.queryset = attended_screenings
        return attended_screenings

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        ScreeningCalendarView.calendar_item_rows = self.queryset
        new_context = {
            'title': 'Calendar Items',
            'sub_header': 'Prepare calendar items from attended screenings',
            'screening_count': len(self.queryset),
            'log': get_log(session)
        }
        unset_log(session)
        return add_base_context(self.request, super_context | new_context)

    @staticmethod
    def _get_attendance_row(attendance):
        screening = attendance.screening
        attendants = Attendance.attendances.filter(screening=screening)
        attendance_row = {
            'screening': screening,
            'attendants': ', '.join([attendant.fan.name for attendant in attendants]),
        }
        return attendance_row


class ScreeningCalendarFormView(LoginRequiredMixin, FormView):
    template_name = ScreeningCalendarView.template_name
    form_class = ScreeningCalendarForm
    http_method_names = ['post']

    def form_valid(self, form):
        post = self.request.POST
        if 'agenda' in post:
            session = self.request.session
            self.form_class.dump_calendar_items(session, ScreeningCalendarView.calendar_item_rows)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('screenings:calendar')
