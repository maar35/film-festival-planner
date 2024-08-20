import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, FormView

from festival_planner.cookie import Cookie
from festival_planner.tools import add_base_context, get_log, unset_log
from festivals.models import current_festival
from loader.forms.loader_forms import ScreeningsLoaderForm
from screenings.models import Screening
from theaters.models import Theater


class FestivalDay:
    day_str_format = '%a %Y-%m-%d'

    def __init__(self, cookie_key):
        self.festival = None
        self.day_cookie = Cookie(cookie_key)

    def check_session(self, session):
        self.festival = current_festival(session)
        day_str = self.day_cookie.get(session) or datetime.date.today().isoformat()
        if day_str < self.festival.start_date.isoformat() or day_str > self.festival.end_date.isoformat():
            day_str = ''
        if not day_str:
            day_str = self.festival.start_date.isoformat()
            self.day_cookie.set(session, day_str)
        return self.festival

    def get_date(self, session):
        day_str = self.day_cookie.get(session)
        return datetime.date.fromisoformat(day_str)

    def get_str(self, session):
        return self.day_cookie.get(session)

    def day_str(self, session):
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
        self.festival = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.festival = DaySchemaView.current_day.check_session(request.session)

    def get_queryset(self):
        festival_screenings = Screening.screenings.filter(film__festival=self.festival)
        current_date = DaySchemaView.current_day.get_date(self.request.session)
        day_screenings = [s for s in festival_screenings if s.start_dt.date() == current_date]
        screenings_by_screen = {}
        sorted_screenings = sorted(day_screenings, key=lambda s: str(s.screen))
        for screening in sorted(sorted_screenings, key=lambda s: s.screen.theater.priority, reverse=True):
            try:
                screenings_by_screen[screening.screen].append(screening)
            except KeyError:
                screenings_by_screen[screening.screen] = [screening]
        screen_rows = [self._get_screen_row(screen, screenings) for screen, screenings in screenings_by_screen.items()]
        return screen_rows

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        current_day_str = DaySchemaView.current_day.day_str(self.request.session)
        day_choices = DaySchemaView.current_day.get_festival_days()
        new_context = {
            'title': 'Screenings Day Schema',
            'sub_header': 'The screenings of the current festival day are visualized',
            'day': current_day_str,
            'day_choices': day_choices,
            'timescale': self._get_timescale(),
            'timebox_length': 60,
            'px_per_hour': self.pixels_per_hour,
            'log': get_log(self.request.session),
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

    def _pixels_from_dt(self, dt):
        start_date = DaySchemaView.current_day.get_date(self.request.session)
        start_dt = datetime.datetime.combine(start_date, self.start_hour)
        pixel_minutes = (dt.replace(tzinfo=start_dt.tzinfo) - start_dt).total_seconds() / 60
        pixels = self.pixels_per_hour * pixel_minutes / 60
        return pixels

    def _screening_spec(self, screening):
        left_pixels = self._pixels_from_dt(screening.start_dt)
        screening_spec = {
            'line_1': f'{screening.film.title}',
            'line_2': f'{screening.start_dt.strftime("%H:%M")} - {screening.end_dt.strftime("%H:%M")}',
            'screening': screening,
            'left': left_pixels,
            'width': self._pixels_from_dt(screening.end_dt) - left_pixels,
        }
        return screening_spec

    def _get_timescale(self):
        hour_list = []
        delta = datetime.timedelta(hours=1)
        start_date = DaySchemaView.current_day.get_date(self.request.session)
        start_dt = datetime.datetime.combine(start_date, self.start_hour)
        for hour in range(self.hour_count):
            dt = (start_dt + hour * delta)
            specs_by_hour = {
                'text': dt.strftime('%H:%M %Z'),
                'left': self._pixels_from_dt(dt),
            }
            hour_list.append(specs_by_hour)
        return hour_list


class DaySchemaFormView(LoginRequiredMixin, FormView):
    template_name = DaySchemaView.template_name
    form_class = ScreeningsLoaderForm
    http_method_names = ['post']

    def form_valid(self, form):
        day_str = self.request.POST['day']
        DaySchemaView.current_day.set_str(self.request.session, day_str, is_choice=True)
        return super().form_valid(form)

    def get_success_url(self):
        return reverse('screenings:day_schema')

