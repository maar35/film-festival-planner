import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views.generic import ListView, FormView
from django.views.generic.detail import SingleObjectMixin

from authentication.models import FilmFan, get_sorted_fan_list
from availabilities.models import Availabilities
from availabilities.views import get_festival_dt, DAY_START_TIME, DAY_BREAK_TIME
from festival_planner.cookie import Filter, FestivalDay, Cookie, get_filter_props, get_fan_filter_props
from festival_planner.debug_tools import pr_debug, profiled_method, SETUP_PROFILER, QUERY_PROFILER, \
    GET_CONTEXT_PROFILER, SCREENING_DICT_PROFILER, SCREEN_ROW_PROFILER, SELECTED_PROPS_PROFILER, \
    FAN_PROPS_PROFILER, LISTVIEW_DISPATCH_PROFILER, ProfiledListView
from festival_planner.fan_action import FanAction
from festival_planner.fragment_keeper import ScreenFragmentKeeper, FRAGMENT_INDICATOR, ScreeningFragmentKeeper, \
    TOP_CORRECTION_ROWS
from festival_planner.screening_status_getter import ScreeningStatusGetter, ScreeningWarning, \
    get_screening_warnings, get_warning_color, get_warnings_keys, get_warnings, get_same_film_attendances, \
    get_overlapping_attended_screenings
from festival_planner.shared_template_referrer_view import SharedTemplateReferrerView
from festival_planner.tools import add_base_context, get_log, unset_log, initialize_log, add_log
from festivals.models import current_festival
from films.models import current_fan, fan_rating, minutes_str, get_present_fans, Film, FilmFanFilmRating
from films.views import FilmDetailView
from screenings.forms.screening_forms import DummyForm, AttendanceForm, PlannerForm, \
    ScreeningCalendarForm, PlannerSortKeyKeeper, TicketForm, ERRORS, ScreeningWarningsForm, ERRORS_IN_WARNING_FIXES
from screenings.models import Screening, Attendance, COLOR_PAIR_SELECTED, filmscreenings, \
    get_available_filmscreenings, COLOR_PAIR_SCREEN
from theaters.models import Theater

AUTO_PLANNED_INDICATOR = '𝛑'


class DaySchemaView(SharedTemplateReferrerView):
    """
    Class-based view to visualise the screenings of a festival day.
    """
    template_name = 'screenings/day_schema.html'
    current_day = FestivalDay('day')

    def __init__(self):
        super().__init__()
        self.list_view = DaySchemaListView
        self.form_view = DaySchemaFormView

    def dispatch(self, request, *args, **kwargs):
        self.current_day.day_cookie.handle_get_request(request)
        ScreeningStatusGetter.handle_screening_get_request(request)
        return super().dispatch(request, *args, **kwargs)


class DaySchemaListView(LoginRequiredMixin, ProfiledListView):
    template_name = DaySchemaView.template_name
    http_method_names = ['get']
    context_object_name = 'screen_rows'
    fans = FilmFan.film_fans.all()
    start_hour = datetime.time(hour=9)
    hour_count = 16
    pixels_per_hour = 120

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fan = None
        self.sorted_fans = None
        self.rating_by_fan_by_film = None
        self.warning_row_nr_by_screening_id = None
        self.first_screening_warning_count = None
        self.sorted_warnings = None
        self.festival = None
        self.selected_screening = None
        self.selected_screening_props = None
        self.status_getter = None
        self.day_screenings = None
        self.screen_fragment_keeper = None

    @profiled_method(duration_profiler=SETUP_PROFILER)
    def setup(self, request, *args, **kwargs):
        pr_debug('start', with_time=True)
        super().setup(request, *args, **kwargs)
        session = request.session
        self.fan = current_fan(session)
        self.sorted_fans = get_sorted_fan_list(self.fan)
        self.festival = DaySchemaView.current_day.check_session(session)
        current_date = DaySchemaView.current_day.get_date(session)
        self.selected_screening = ScreeningStatusGetter.get_selected_screening(request)
        self.day_screenings = Screening.screenings.filter(film__festival=self.festival, start_dt__date=current_date)
        self.rating_by_fan_by_film = self._get_rating_by_fan_by_film()
        self.status_getter = ScreeningStatusGetter(request.session, self.day_screenings)
        self.screen_fragment_keeper = ScreenFragmentKeeper()
        self._get_top_fragments_data()
        pr_debug('done', with_time=True)

    def dispatch(self, request, *args, **kwargs):
        cookie = DaySchemaView.current_day.day_cookie
        DaySchemaView.current_day.set_str(request.session, cookie.get(request.session))
        return super().dispatch(request, *args, **kwargs)

    @profiled_method(duration_profiler=QUERY_PROFILER)
    def get_queryset(self):
        pr_debug('start', with_time=True)
        screenings_by_screen = self._get_screenings_by_screen()
        self.screen_fragment_keeper.add_fragments(screenings_by_screen.keys())
        screen_rows = [self._get_screen_row(i, s, screenings_by_screen[s]) for i, s in enumerate(screenings_by_screen)]
        pr_debug('done', with_time=True)
        return screen_rows

    @profiled_method(GET_CONTEXT_PROFILER)
    def get_context_data(self, **kwargs):
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
            'prev_day': self._next_festival_day(session, current_day, day_choices, days=-1),
            'next_day': self._next_festival_day(session, current_day, day_choices, days=1),
            'first_day': day_choices[0].split()[1],
            'last_day': day_choices[-1].split()[1],
            'screening': self.selected_screening,
            'selected_screening_props': selected_screening_props,
            'timescale': self._get_timescale(),
            'availability_props': availability_props,
            'total_width': self.hour_count * self.pixels_per_hour,
            'stats': ScreeningWarning.get_warning_stats(self.festival, self.sorted_warnings),
            'form_errors': ERRORS.get(session),
            'log': get_log(session),
            'action': ScreeningDetailView.fan_action.get_refreshed_action(session),
        }
        ERRORS.remove(session)
        unset_log(session)
        return add_base_context(self.request, super_context | new_context)

    @staticmethod
    def _next_festival_day(session, current_day, day_choices, days):
        next_date = current_day.get_date(session) + datetime.timedelta(days=days)
        within_festival = next_date.strftime(FestivalDay.day_str_format) in day_choices
        return next_date.strftime(FestivalDay.date_str_format) if within_festival else None

    @profiled_method(SCREEN_ROW_PROFILER)
    def _get_screen_row(self, screen_nr, screen, screenings):
        screening_props = [self._screening_props(s) for s in screenings]
        selected = len([prop['selected'] for prop in screening_props if prop['selected']])
        fragment_name = self.screen_fragment_keeper.get_fragment_name(screen_nr)
        screen_row = {
            'screen': screen,
            'fragment_name': fragment_name,
            'color': Theater.color_by_priority[screen.theater.priority],
            'total_width': self.hour_count * self.pixels_per_hour,
            'screening_props': sorted(screening_props, key=lambda prop: prop['screening'].start_dt),
            'background': COLOR_PAIR_SELECTED['background'] if selected else COLOR_PAIR_SCREEN['background'],
        }
        return screen_row

    @profiled_method(SCREENING_DICT_PROFILER)
    def _get_screenings_by_screen(self):
        screenings_by_screen = {}
        sorted_screenings = sorted(self.day_screenings, key=lambda s: str(s.screen))
        for screening in sorted(sorted_screenings, key=lambda s: s.screen.theater.priority, reverse=True):
            try:
                screenings_by_screen[screening.screen].append(screening)
            except KeyError:
                screenings_by_screen[screening.screen] = [screening]
        return screenings_by_screen

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

    def _get_rating_by_fan_by_film(self):
        day_films = {screening.film for screening in self.day_screenings}
        ratings = FilmFanFilmRating.film_ratings.filter(film__in=day_films)
        rating_by_fan_by_film = {}
        for rating in ratings:
            fan = rating.film_fan
            film = rating.film
            try:
                rating_by_fan_by_film[fan][film] = rating
            except KeyError:
                rating_by_fan_by_film[fan] = {film: rating}
        return rating_by_fan_by_film

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

    def _screening_props(self, screening):
        getter = self.status_getter
        attendants = getter.get_attendants(screening)
        status, pair = self._screening_color_pair(screening, attendants)

        selected = screening == self.selected_screening
        if selected:
            self._set_selected_screening_props(status, pair, attendants)

        left_pixels = self._pixels_from_dt(screening.start_dt)
        day = screening.start_dt.date().isoformat()
        line_2 = f'{screening.start_dt.strftime("%H:%M")} - {screening.end_dt.strftime("%H:%M")}'
        pair_selected = Screening.color_pair_selected_by_screening_status[status]
        festival_color = screening.film.festival.festival_color
        _, film_rating_str, rating_color = screening.film_rating_data(status)
        info_str = ("Q " if screening.q_and_a else "") + self._get_fan_props_str(screening)
        warnings = get_screening_warnings(screening, self.sorted_fans, getter.keeper, getter)
        warnings_props = self._get_warning_props(status, warnings)
        frame_color = pair_selected['color'] if selected else festival_color
        section_color = screening.film.subsection.section.color if screening.film.subsection else frame_color
        warn_query_key = ScreeningStatusGetter.screening_cookie.get_cookie_key()
        warn_querystring = Filter.get_querystring(**{warn_query_key: screening.pk})
        warn_fragment = self._get_warning_fragment(screening)
        warning_wordings = [f'{w.fan} {ScreeningWarning.wording_by_warning[w.warning]}' for w in warnings]
        schema_querystring = Filter.get_querystring(**{'day': day, 'screening': screening.pk})
        schema_fragment = ScreenFragmentKeeper.fragment_code(screening.screen)
        screening_prop = {
            'screening': screening,
            'line_1': f'{screening.film.title}',
            'line_2': line_2,
            'left': left_pixels,
            'width': self._pixels_from_dt(screening.end_dt) - left_pixels,
            'pair': pair,
            'auto_planned': AUTO_PLANNED_INDICATOR if screening.auto_planned else "",
            'film_rating': film_rating_str,
            'rating_color': rating_color,
            'selected': selected,
            'frame_color': frame_color,
            'section_color': section_color,
            'info_pair': pair_selected if selected else pair,
            'info_spot': info_str or 'info',
            'warnings': warning_wordings,
            'warnings_debug': True,
            'warnings_props': warnings_props,
            'warn_fragment': warn_fragment,
            'warn_querystring': warn_querystring,
            'schema_querystring': '' if selected else schema_querystring,
            'schema_fragment': f'{FRAGMENT_INDICATOR}header_screening' if selected else schema_fragment,
        }
        return screening_prop

    @profiled_method(FAN_PROPS_PROFILER)
    def _get_fan_props_str(self, screening):
        initials = []
        for fan in self.sorted_fans:
            attending = self.status_getter.attendance_by_screening_by_fan[screening][fan]
            initial = fan.initial() if attending else fan.initial().lower()
            try:
                rating = self.rating_by_fan_by_film[fan][screening.film]
            except KeyError:
                rating = None
            if rating:
                initial += str(rating.rating)
            if attending or rating:
                initials.append(initial)
        return ''.join(initials)

    @staticmethod
    def _get_warning_props(screening_status, warnings):
        props = []
        if warnings:
            warning_types = sorted({warning.warning for warning in warnings}, key=lambda t: t.value)
            for warning_type in warning_types:
                symbol = ScreeningWarning.symbol_by_warning[warning_type]
                prop = {
                    'symbol': symbol,
                    'small': ScreeningWarning.small_by_symbol[symbol],
                    'color': get_warning_color(screening_status, warning_type),
                }
                props.append(prop)
        return props

    def _screening_color_pair(self, screening, attendants):
        status = self.status_getter.get_screening_status(screening, attendants)
        return status, Screening.color_pair_by_screening_status[status]

    def _get_filmscreening_props(self):
        session = self.request.session
        return ScreeningStatusGetter.get_filmscreening_props(session, self.selected_screening.film)

    def _get_selected_screening_props(self):
        return self.selected_screening_props

    @profiled_method(SELECTED_PROPS_PROFILER)
    def _set_selected_screening_props(self, status, pair, attendants):
        screening = self.selected_screening
        film = screening.film
        rating_by_fan = {fan: fan_rating(fan, film) for fan in self.sorted_fans}
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

    @staticmethod
    def _get_warning(warning):
        warning_props = {'warning': warning, 'screening': warning.screening, 'fan': warning.fan}
        return warning_props

    def _get_top_fragments_data(self):
        # Get all warnings, sorted as in the warnings view.
        sort_key = ScreeningWarningsListView.get_sort_key
        sorted_warning_rows = sorted(get_warnings(self.festival, self._get_warning), key=sort_key)

        # Create a dictionary to find the row by screening.
        self.warning_row_nr_by_screening_id = {row['screening'].id: i for i, row in enumerate(sorted_warning_rows)}

        # Get the number of warnings of the first screening.
        first_screening = sorted_warning_rows[0]['screening']
        warning_count = 0
        index = 0
        max_iter = len(sorted_warning_rows)
        while index < max_iter and sorted_warning_rows[index]['screening'].id == first_screening.id:
            index += 1
            warning_count += 1
        self.first_screening_warning_count = warning_count

        # Store the warnings for use in warning stats mini-view.
        self.sorted_warnings = [row['warning'] for row in sorted_warning_rows]

    def _get_warning_fragment(self, screening):
        warn_fragment = ScreeningFragmentKeeper.fragment_code(screening)
        try:
            row = self.warning_row_nr_by_screening_id[screening.id]
        except KeyError:
            pass
        else:
            if row < max(TOP_CORRECTION_ROWS, self.first_screening_warning_count):
                warn_fragment = '#top'
        return warn_fragment


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
    update_by_has_ticket = {True: 'got a ticket', False: 'sold a ticket'}
    update_by_confirmed = {True: 'had a ticket confirmed', False: 'had a ticket unconfirmed'}
    fans = None
    object = None
    screening = None
    initial_attendance_by_fan = None
    initial_tickets_by_fan = None
    initial_confirmed_by_fan = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        session = request.session
        initialize_log(session, 'Update attendance statuses')
        fans = get_present_fans(session)
        self.fans = get_sorted_fan_list(current_fan(session), fan_query_set=fans)
        self.screening = self.get_object()
        self.initial_attendance_by_fan = {f: bool(self.screening.fan_attends(f)) for f in self.fans}
        self.initial_tickets_by_fan = {f: bool(self.screening.fan_has_ticket(f)) for f in self.fans}
        self.initial_confirmed_by_fan = {f: bool(self.screening.fan_ticket_confirmed(f)) for f in self.fans}

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        duration = self.screening.end_dt - self.screening.start_dt
        fan_props = [{
            'fan': fan.name,
            'attends': self.initial_attendance_by_fan[fan],
            'ticket_fan': fan.name + '_ticket',
            'has_ticket': self.initial_tickets_by_fan[fan],
            'confirmed_fan': fan.name + '_confirmed',
            'confirmed': self.initial_confirmed_by_fan[fan],
        } for fan in self.fans]
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
        post = self.request.POST
        new_attendance_by_fan = {fan: fan.name in post for fan in self.fans}
        new_has_ticket_by_fan = {fan: fan.name + '_ticket' in post for fan in self.fans}
        new_confirmed_by_fan = {fan: fan.name + '_confirmed' in post for fan in self.fans}
        self._update_attendance_statuses(new_attendance_by_fan, new_has_ticket_by_fan, new_confirmed_by_fan)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('screenings:day_schema')

    def _update_attendance_statuses(self, new_attendance_by_fan, new_has_ticket_by_fan, new_confirmed_by_fan):
        self.fan_action.init_action(self.request.session, screening=self.screening)
        updated_count = self._update_attendance(new_attendance_by_fan)
        updated_count += self._update_tickets(new_has_ticket_by_fan)
        updated_count += self._update_confirmed(new_confirmed_by_fan)
        if not updated_count:
            session = self.request.session
            add_log(session, f'No attendance statuses of {self.screening} were updated by {current_fan(session)}.')

    def _update_attendance(self, new_attendance_by_fan):
        update_method = AttendanceForm.update_attendances
        updated_count = self._update_fan_screening_props(
            new_attendance_by_fan, self.update_by_attends, self.initial_attendance_by_fan, update_method
        )
        return updated_count

    def _update_tickets(self, new_has_ticket_by_fan):
        update_method = TicketForm.update_has_ticket
        updated_count = self._update_fan_screening_props(
            new_has_ticket_by_fan, self.update_by_has_ticket, self.initial_tickets_by_fan, update_method
        )
        return updated_count

    def _update_confirmed(self, new_confirmed_by_fan):
        update_method = TicketForm.update_ticket_confirmations
        updated_count = self._update_fan_screening_props(
            new_confirmed_by_fan, self.update_by_confirmed, self.initial_confirmed_by_fan, update_method
        )
        return updated_count

    def _update_fan_screening_props(self, new_prop_by_fan, update_by_prop, initial_prop_by_fan, update_method):
        def update_log(film_fan, fan_action):
            self.fan_action.add_detail(session, f'{film_fan} {update_by_prop[fan_action]}')

        session = self.request.session
        changed_prop_by_fan = {}
        for fan, initial_prop in initial_prop_by_fan.items():
            prop = new_prop_by_fan[fan]
            if initial_prop != prop:
                changed_prop_by_fan[fan] = prop
        if changed_prop_by_fan:
            _ = update_method(session, self.screening, changed_prop_by_fan, update_log)
        return len(changed_prop_by_fan)

    def _get_filmscreening_props(self):
        session = self.request.session
        return ScreeningStatusGetter.get_filmscreening_props(session, self.screening.film)


class PlannerView(SharedTemplateReferrerView):
    template_name = 'screenings/planner.html'
    festival = None
    eligible_films = None

    def __init__(self):
        super().__init__()
        self.list_view = PlannerListView
        self.form_view = PlannerFormView


class PlannerListView(LoginRequiredMixin, ListView):
    template_name = PlannerView.template_name
    http_method_names = ['get']
    context_object_name = 'planned_screening_rows'
    fan = None

    def __init__(self):
        super().__init__()
        self.planned_screening_count = None
        self.sorted_eligible_screenings = None

    def setup(self, request, *args, **kwargs):
        pr_debug('start', with_time=True)
        super().setup(request, *args, **kwargs)
        PlannerView.festival = current_festival(request.session)
        PlannerView.eligible_films = self._get_eligible_films()
        self.fan = current_fan(request.session)
        pr_debug('done', with_time=True)

    def get_queryset(self):
        pr_debug('start', with_time=True)

        # Get the planned screening rows.
        get_row = self._get_planned_screening_row
        films = PlannerView.eligible_films
        eligible_screenings = PlannerForm.get_eligible_screenings(films, auto_planned=True).order_by('start_dt')
        planned_screening_rows = [get_row(s) for s in eligible_screenings if s.auto_planned]

        # Derive extra information for use in context.
        self.planned_screening_count = len(planned_screening_rows)
        sorted_screenings = self._get_sorted_screenings(films)
        self.sorted_eligible_screenings = [self._get_sorted_screening_row(s) for s in sorted_screenings]
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
            'eligible_screening_count': len(self.sorted_eligible_screenings),
            'eligible_screening_rows': self.sorted_eligible_screenings,
            'warning_stats': ScreeningWarning.get_warning_stats(PlannerView.festival),
            'form_errors': PlannerForm.tracer.get_errors() if PlannerForm.tracer else [],
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

    def _get_planned_screening_row(self, screening):
        film = screening.film
        fans_rating_str, film_rating_str, _ = screening.film.rating_strings()
        planned_screening_row = {
            'start_dt': screening.start_dt,
            'end_dt': screening.end_dt,
            'screen_name': str(screening.screen),
            'film': film,
            'filmscreening_count': filmscreenings(film).count(),
            'available_filmscreening_count': len(get_available_filmscreenings(film, self.fan)),
            'attendants': screening.attendants_str(),
            'fan_ratings_str': fans_rating_str,
            'film_rating_str': film_rating_str,
        }
        return planned_screening_row

    def _get_sorted_screening_row(self, screening):
        film = screening.film
        day = screening.start_dt.date().isoformat()
        querystring = Filter.get_querystring(**{'day': day, 'screening': screening.pk})
        fragment = ScreenFragmentKeeper.fragment_code(screening.screen)
        highest_rating, second_highest_rating = PlannerSortKeyKeeper.get_highest_ratings(film)
        eligible_screening_row = {
            'screening': screening,
            'query_string': querystring,
            'fragment': fragment,
            'available_fans_str': ', '.join([fan.name for fan in screening.get_available_fans()]),
            'highest_rating': highest_rating,
            'second_highest_rating': second_highest_rating,
            'q_and_a': screening.q_and_a,
            'attendants_str': screening.attendants_str(),
            'available_filmscreening_count': len(get_available_filmscreenings(film, self.fan)),
            'duration': screening.duration(),
            'start_dt': screening.start_dt,
            'auto_planned': screening.auto_planned,
            'auto_planned_indicator': AUTO_PLANNED_INDICATOR,
        }
        return eligible_screening_row

    def _get_sorted_screenings(self, films):
        kwargs = {
            'film__in': films,
            'screen__theater__priority': Theater.Priority.HIGH,
        }
        screenings = Screening.screenings.filter(**kwargs)
        fan = current_fan(self.request.session)
        sorted_screenings = PlannerForm.get_sorted_eligible_screenings(screenings, fan)
        return sorted_screenings


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
            _ = PlannerForm.undo_auto_planning(session, PlannerView.festival)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('screenings:planner')


class ScreeningCalendarView(SharedTemplateReferrerView):
    template_name = 'screenings/calendar.html'
    calendar_item_rows = None

    def __init__(self):
        super().__init__()
        self.list_view = ScreeningCalendarListView
        self.form_view = ScreeningCalendarFormView


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
        attendance_row = {
            'screening': screening,
            'attendants': screening.attendants_str(),
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


class ScreeningWarningsView(SharedTemplateReferrerView):
    template_name = 'screenings/warnings.html'

    def __init__(self):
        super().__init__()
        self.list_view = ScreeningWarningsListView
        self.form_view = ScreeningWarningsFormView


class ScreeningWarningsListView(LoginRequiredMixin, ProfiledListView):
    template_name = ScreeningWarningsView.template_name
    http_method_names = ['get']
    context_object_name = 'warning_rows'
    fans = None
    status_getter = None
    fragment_keeper = None
    warnings = None

    def __init__(self):
        super().__init__()
        self.fan = None
        self.filter_by_fan = None
        self.filter_by_warning_type = None
        self.reset_filter = None
        self.filters = None
        self.display_filmscreenings = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.fan = current_fan(request.session)
        self.fans = get_sorted_fan_list(self.fan)
        self.fragment_keeper = ScreeningFragmentKeeper()
        self._setup_filters(request.session)
        self.display_filmscreenings = self.reset_filter.on(request.session)

    @profiled_method(LISTVIEW_DISPATCH_PROFILER)
    def dispatch(self, request, *args, **kwargs):
        # Set the selected screening if requested.
        ScreeningStatusGetter.handle_screening_get_request(request)

        # Reset filters if requested.
        session = request.session
        self.reset_filter.handle_get_request(request)
        if self.reset_filter.on(session):
            for _filter in self.filters:
                if _filter.on(session):
                    _filter.remove(session)

        # Handle all filter requests conform the querystring in the URL.
        for _filter in self.filters:
            _filter.handle_get_request(request)

        # Switch off the reset filter.
        self.reset_filter.remove(session)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        pr_debug('start', with_time=True)
        session = self.request.session
        festival = current_festival(session)

        # Prepare a screening status getter.
        keys_set = get_warnings_keys(festival)
        screenings = {screening for screening, fan in keys_set}
        self.status_getter = ScreeningStatusGetter(session, screenings)

        # Get the queryset.
        warning_rows = get_warnings(festival, self._get_warning_details, keys_set=keys_set)
        sorted_warning_rows = sorted(warning_rows, key=self.get_sort_key)

        # Store the warnings for use in warning stats mini-view.
        self.warnings = [row['warning'] for row in sorted_warning_rows]
        self._set_warnings(self.warnings)

        # Set fragments for the screenings in the view.
        self.fragment_keeper.add_fragment_data(sorted_warning_rows)

        # Apply filters to the warnings
        filtered_warning_rows = self._filter_warnings(session, sorted_warning_rows)

        pr_debug('done', with_time=True)
        return filtered_warning_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        base_context = add_base_context(self.request, super_context)
        new_context = {
            'title': 'Warnings',
            'sub_header': 'Warnings per screening per fan',
            'warnings': len(ScreeningWarningsListView.warnings),
            'screening': ScreeningStatusGetter.get_selected_screening(self.request),
            'selected_background': COLOR_PAIR_SELECTED['background'],
            'fan_filter_props': self._get_fan_filter_props(),
            'warning_filter_props': self._get_warning_filter_props(),
            'stats': ScreeningWarning.get_warning_stats(base_context['festival'], warnings=self.warnings),
            'log': get_log(session),
            'form_errors': ERRORS_IN_WARNING_FIXES.get(session),
            'action': ScreeningWarningsForm.fix_action.get_refreshed_action(session),
        }
        ERRORS_IN_WARNING_FIXES.remove(session)
        unset_log(session)
        return base_context | new_context

    @classmethod
    def get_sort_key(cls, row):
        return row['screening'].film.sort_title, row['screening'].start_dt, row['fan'].name

    def _get_warning_details(self, warning):
        screening = warning.screening
        fan = warning.fan
        warning_type = warning.warning
        attendants = self.status_getter.get_attendants(screening)
        status = self.status_getter.get_screening_status(screening, attendants)
        color = get_warning_color(status, warning_type)
        background = Screening.color_pair_by_screening_status[status]['background']
        day = screening.start_dt.date().isoformat()
        schema_querystring = Filter.get_querystring(**{'day': day, 'screening': screening.pk})
        return {
            'warning': warning,
            'screening': screening,
            'fan': fan,
            'warning_type': warning_type,
            'warning_wording': ScreeningWarning.wording_by_warning[warning_type],
            'wording_color': ScreeningWarning.color_by_warning[warning_type],
            'warning_fix': ScreeningWarning.fix_by_warning[warning_type],
            'choices': self._get_choices(warning),
            'symbol': ScreeningWarning.symbol_by_warning[warning_type],
            'color': color,
            'background': background,
            'fragment_name': None,
            'schema_querystring': schema_querystring,
            'fragment': ScreenFragmentKeeper.fragment_code(screening.screen),
        }

    def _setup_filters(self, session):
        self.filter_by_fan = {}
        self.filter_by_warning_type = {}
        self.filters = []
        festival_str = str(current_festival(session)).replace(' ', '')

        # Setup reset filters filter
        reset_kwargs = {
            'cookie_key': f'{festival_str}-reset-filters',
            'action_false': 'Reset',
            'action_true': 'Leave',
        }
        self.reset_filter = Filter('reset_filters', **reset_kwargs)

        # Setup fan filters.
        self.reset_filter = Filter('filters', **reset_kwargs)
        for fan in self.fans:
            fan_kwargs = {
                'cookie_key': f'{festival_str}-fan-{fan.name}',
                'action_false': 'Select',
                'action_true': 'Remove filter',
            }
            self.filter_by_fan[fan] = Filter('fan', **fan_kwargs)

        # Setup warning type filters.
        for warning_type in ScreeningWarning.WarningType:
            warning_kwargs = {
                'cookie_key': f'{festival_str}-warning-{warning_type.name}',
                'action_false': 'Select',
                'action_true': 'Remove filter',
            }
            self.filter_by_warning_type[warning_type] = Filter('warning_type', **warning_kwargs)

        # Add all filters to the list.
        self.filters.append(self.reset_filter)
        self.filters.extend(self.filter_by_fan[fan] for fan in self.filter_by_fan)
        self.filters.extend(self.filter_by_warning_type[_type] for _type in self.filter_by_warning_type)

    def _filter_warnings(self, session, warning_rows):
        filter_fan = None
        filter_warn = None

        # Apply active filters.
        for fan in self.fans:
            if self.filter_by_fan[fan].on(session):
                filter_fan = fan
                break
        for warning_type in ScreeningWarning.WarningType:
            if self.filter_by_warning_type[warning_type].on(session):
                filter_warn = warning_type
                break

        filtered_screenings = []
        for r in warning_rows:
            if (r['fan'] == filter_fan or not filter_fan) and (r['warning_type'] == filter_warn or not filter_warn):
                filtered_screenings.append(r['screening'])

        filtered_warning_rows = [r for r in warning_rows if r['screening'] in filtered_screenings]
        return filtered_warning_rows

    def _get_warning_filter_props(self):
        session = self.request.session
        queryset = self.warnings
        objects = ScreeningWarning.WarningType
        obj_field = 'warning'
        filter_by_obj = self.filter_by_warning_type
        label_by_obj = ScreeningWarning.wording_by_warning
        return get_filter_props(session, queryset, objects, obj_field, filter_by_obj, label_by_obj)

    def _get_fan_filter_props(self):
        session = self.request.session
        return get_fan_filter_props(session, self.warnings, self.fans, self.filter_by_fan)

    @classmethod
    def _set_warnings(cls, warnings):
        cls.warnings = warnings

    def _get_choices(self, warning):
        fan = warning.fan
        screening = warning.screening
        warning_type = warning.warning
        match warning_type:
            case ScreeningWarning.WarningType.NEEDS_TICKET\
                 | ScreeningWarning.WarningType.AWAITS_CONFIRMATION\
                 | ScreeningWarning.WarningType.SHOULD_SELL_TICKET:
                choices = self._get_ticket_warning_choices(warning_type, fan, screening)
            case ScreeningWarning.WarningType.ATTENDS_SAME_FILM:
                choices = self._get_choices_with_link(warning_type, fan, screening)
            case ScreeningWarning.WarningType.ATTENDS_OVERLAPPING:
                choices = self._get_choices_with_link(warning_type, fan, screening)
            case ScreeningWarning.WarningType.ATTENDS_WHILE_UNAVAILABLE:
                choices = self._get_unavailable_fan_choices(warning_type, fan, screening)
            case _:
                choices = [{
                    'value': 'Sorry, work in progress',
                    'submit_name': None,
                }]
        return choices

    @staticmethod
    def _get_ticket_warning_choices(warning_type, fan, screening):
        fix_wording = ScreeningWarning.fix_by_warning[warning_type]
        all_of_screening_wording = ScreeningWarning.all_of_screening_wording_by_ticket_warning[warning_type]
        all_of_fan_wording = ScreeningWarning.all_of_fan_wording_by_ticket_warning[warning_type]
        choices = [{
            'value': f'{fix_wording} for {fan}',
            'submit_name': f'{warning_type.name}:{fan.name}:{screening.id}:',
        }, {
            'value': f'{fix_wording} {all_of_screening_wording}',
            'submit_name': f'{warning_type.name}::{screening.id}:',
        }, {
            'value': f'{fix_wording} {all_of_fan_wording} {fan}',
            'submit_name': f'{warning_type.name}:{fan.name}::',
        }]
        return choices

    def _get_choices_with_link(self, warning_type, fan, screening):
        fix_wording = ScreeningWarning.fix_by_warning[warning_type]

        # Set up the queryset to select screenings with the given fan and warning.
        filters = [self.reset_filter, self.filter_by_fan[fan], self.filter_by_warning_type[warning_type]]
        querystring = Filter.get_display_query_from_keys([f.get_cookie_key() for f in filters], on=True)

        # Create choices for related screenings.
        other_screening_choices = []
        match warning_type:
            case ScreeningWarning.WarningType.ATTENDS_OVERLAPPING:
                other_screening_choices = self._get_attends_overlapping_choices(warning_type, fan, screening)
            case ScreeningWarning.WarningType.ATTENDS_SAME_FILM:
                other_screening_choices = self._get_attends_same_film_choices(warning_type, fan, screening)

        # Define the choice properties.
        choices = [{
            'value': f'{fix_wording}',
            'submit_name': f'{warning_type.name}:{fan.name}:{screening.id}:',
        }] + other_screening_choices + [{
            'value': f'Display overlapping screenings',
            'link': '/screenings/warnings' + querystring
        }]

        return choices

    @staticmethod
    def _get_attends_overlapping_choices(warning_type, fan, screening):
        fix_wording = ScreeningWarning.fix_by_warning[warning_type]

        # Create choices for each overlapping screening.
        overlap_screenings = get_overlapping_attended_screenings(screening, fan, first_only=False)\
            if warning_type == ScreeningWarning.WarningType.ATTENDS_OVERLAPPING else None
        overlap_choices = []
        for screening in overlap_screenings:
            overlap_choice = {
                'value': f'{fix_wording} {screening.film.title}',
                'submit_name': f'{warning_type.name}:{fan.name}::{screening.id}',
            }
            overlap_choices.append(overlap_choice)

        return overlap_choices

    @staticmethod
    def _get_attends_same_film_choices(warning_type, fan, screening):
        fix_wording = ScreeningWarning.fix_by_warning[warning_type]

        # Create choices for each attended screening of the same film.
        same_film_attendances = get_same_film_attendances(screening, fan)
        other_attended_screenings = [a.screening for a in same_film_attendances if a.screening != screening]
        same_film_choices = []
        for screening in other_attended_screenings:
            same_film_choice = {
                'value': f'{fix_wording} {screening.str_short()}',
                'submit_name': f'{warning_type.name}:{fan.name}::{screening.id}',
            }
            same_film_choices.append(same_film_choice)

        return same_film_choices

    @staticmethod
    def _get_unavailable_fan_choices(warning_type, fan, screening):
        fix_wording = ScreeningWarning.fix_by_warning[warning_type]
        querystring = Cookie.get_querystring(**{'warning_name': warning_type.name, 'fan_name': fan.name})
        choices = [{
            'value': f'{fix_wording}',
            'submit_name': f'{warning_type.name}:{fan.name}:{screening.id}:',
        }, {
            'value': 'To availability page',
            'link': '/availabilities/list' + querystring,
        }]
        return choices


class ScreeningWarningsFormView(LoginRequiredMixin, FormView):
    template_name = ScreeningWarningsView.template_name
    form_class = ScreeningWarningsForm
    http_method_names = ['post']
    success_url = '/screenings/warnings'
    fix_method_by_warning = {
        ScreeningWarning.WarningType.NEEDS_TICKET: form_class.buy_tickets,
        ScreeningWarning.WarningType.AWAITS_CONFIRMATION: form_class.confirm_tickets,
        ScreeningWarning.WarningType.SHOULD_SELL_TICKET: form_class.delete_tickets,
        ScreeningWarning.WarningType.ATTENDS_SAME_FILM: form_class.delete_attendances,
        ScreeningWarning.WarningType.ATTENDS_OVERLAPPING: form_class.delete_attendances,
        ScreeningWarning.WarningType.ATTENDS_WHILE_UNAVAILABLE: form_class.delete_attendances,
    }

    def __init__(self):
        super().__init__()
        self.session = None

    def form_valid(self, form):
        self.session = self.request.session
        initialize_log(self.session, 'Fixed warnings')

        # Get the individual parameters from the post data.
        submitted_name = list(self.request.POST)[-1]
        warning_name, fan_name, screening_id, other_id = submitted_name.split(':')
        warning_type = ScreeningWarning.WarningType[warning_name]

        # Feed the parameters to warning fixing machinery.
        fix_method = self.fix_method_by_warning[warning_type]
        self._fix_ticket_warnings(warning_type, fan_name, screening_id, other_id, fix_method)

        return super().form_valid(form)

    def _fix_ticket_warnings(self, warning_type, fan_name, screening_id, other_id, fix_method):
        wording = self._get_wording_for_fix(warning_type)
        if fan_name and screening_id:
            _ = fix_method(self.session, [fan_name], [screening_id], wording)
        elif other_id:
            _ = fix_method(self.session, [fan_name], [other_id], wording)
        elif screening_id:
            self._fix_screening_tickets(warning_type, screening_id, fix_method)
        elif fan_name:
            self._fix_fan_tickets(warning_type, fan_name, fix_method)

    def _fix_screening_tickets(self, warning_type, screening_id, fix_method):
        warnings = ScreeningWarningsListView.warnings
        fan_names = [w.fan.name for w in warnings if w.screening.id == int(screening_id) and w.warning == warning_type]
        wording = self._get_wording_for_fix(warning_type)
        _ = fix_method(self.session, fan_names, [screening_id], wording)

    def _fix_fan_tickets(self, warning_type, fan_name, fix_method):
        warnings = ScreeningWarningsListView.warnings
        screening_ids = [w.screening.id for w in warnings if w.fan.name == fan_name and w.warning == warning_type]
        wording = self._get_wording_for_fix(warning_type)
        _ = fix_method(self.session, [fan_name], screening_ids, wording)

    @staticmethod
    def _get_wording_for_fix(warning_type):
        noun = ScreeningWarning.fix_noun_by_warning[warning_type]
        verb = ScreeningWarning.fix_verb_by_warning[warning_type]
        wording = f'{noun} {verb}'
        return wording
