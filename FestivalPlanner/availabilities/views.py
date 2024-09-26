import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, FormView

from authentication.models import FilmFan
from availabilities.forms.availabilities_forms import AvailabilityForm
from availabilities.models import Availabilities
from festival_planner.cookie import Cookie, Filter
from festival_planner.tools import add_base_context, wrap_up_form_errors
from festivals.models import current_festival
from films.models import current_fan
from screenings.views import FestivalDay

DAY_BREAK_TIME = datetime.time(hour=6)
DAY_START_TIME = datetime.time(hour=8)
ERRORS_COOKIE = Cookie('form_errors', [])


def get_festival_dt(date, time):
    if time <= DAY_BREAK_TIME:
        date += datetime.timedelta(days=1)
    dt = datetime.datetime.combine(date, time)
    return dt


def set_error(session, error):
    ERRORS_COOKIE.set(session, [error])


class AvailabilityDay(FestivalDay):
    def alternative_day_str(self):
        return self.festival.start_date.isoformat()


class AvailabilityView(LoginRequiredMixin, View):
    """
    Class te receive and forward requests on availabilities.
    """
    template_name = 'availabilities/list.html'
    initial_start_time = DAY_START_TIME.strftime('%H:%M')
    initial_end_time = DAY_BREAK_TIME.strftime('%H:%M')
    fan_cookie = Cookie('available_fan')
    start_day = AvailabilityDay('start_day')
    start_time = Cookie('start_time', initial_value=initial_start_time)
    end_day = AvailabilityDay('end_day')
    end_time = Cookie('end_time', initial_value=initial_end_time)

    @staticmethod
    def get(request, *args, **kwargs):
        view = AvailabilityListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = AvailabilityFormView.as_view()
        return view(request, *args, **kwargs)

    @classmethod
    def get_dt(cls, session, date_field, time_field):
        date_attr = getattr(cls, date_field)
        date = date_attr.get_date(session)
        time_attr = getattr(cls, time_field)
        time = datetime.time.fromisoformat(time_attr.get(session))
        return get_festival_dt(date, time)


class AvailabilityListView(LoginRequiredMixin, ListView):
    """
    Lists the known availability periods of all fans within the current festival.
    """
    template_name = AvailabilityView.template_name
    context_object_name = 'availability_rows'
    http_method_names = ['get']
    object_list = []
    fan_list = FilmFan.film_fans.all().order_by('seq_nr')
    form = AvailabilityForm
    title = 'Availabilities List'
    festival = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.filters = None
        self.fan_filters = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.festival = current_festival(request.session)

        # Set up the fan filters. TODO: Generalize fan, section and subsection filtering.
        self.filters = []
        self.fan_filters = {}
        for fan in self.fan_list:
            self.fan_filters[fan] = Filter('fan',
                                           cookie_key=f'fan-{fan.id}',
                                           action_false='Select fan',
                                           action_true='Remove filter')
            self.filters.append(self.fan_filters[fan])

        # Get festival period form session.
        AvailabilityView.start_day.check_session(request.session)
        AvailabilityView.end_day.check_session(request.session)

    def dispatch(self, request, *args, **kwargs):
        for f in self.filters:
            f.handle_get_request(request)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        manager = Availabilities.availabilities
        kwargs = {
            'start_dt__gte': get_festival_dt(self.festival.start_date, DAY_START_TIME),
            'start_dt__lte': get_festival_dt(self.festival.end_date, DAY_BREAK_TIME),
        }
        for fan in self.fan_list:
            if self.fan_filters[fan].on(self.request.session):
                kwargs['fan'] = fan
                break
        selected_availabilities = manager.filter(**kwargs).order_by('start_dt', 'end_dt', 'fan__name')
        return selected_availabilities  # availability_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        self.festival = current_festival(session)
        fan = AvailabilityView.fan_cookie.get(session, default=current_fan(session))
        fan_filter_props = self._get_filter_props()
        day_start_str = DAY_START_TIME.strftime('%H:%M')
        day_break_str = DAY_BREAK_TIME.strftime('%H:%M')
        time_choices = [day_start_str, '10:00', '12:00', '15:00', '18:00', '20:00', '23:00', '00:30', day_break_str]
        new_context = {
            'title': self.title,
            'fan_picker_label': 'Filmfan:',
            'fan': fan,
            'fan_choices': self.fan_list,
            'date_picker_label': 'Start date:',
            'day': AvailabilityView.start_day.get_str(session),
            'day_choices': AvailabilityView.start_day.get_festival_days(),
            'time_picker_label': 'Start time:',
            'time': AvailabilityView.start_time.get(session),
            'time_choices': time_choices,
            'alt_date_picker_label': 'End date:',
            'alt_day': AvailabilityView.end_day.get_str(session),
            'alt_day_choices': AvailabilityView.end_day.get_festival_days(),
            'alt_time_picker_label': 'End time:',
            'alt_time': AvailabilityView.end_time.get(session),
            'alt_time_choices': time_choices,
            'can_submit': self._can_submit(session),
            'add_form': self.form(),
            'festival_start_dt': get_festival_dt(self.festival.start_date, DAY_START_TIME),
            'festival_end_dt': get_festival_dt(self.festival.end_date, DAY_BREAK_TIME),
            'fan_filter_props': fan_filter_props,
            'form_errors': ERRORS_COOKIE.get(session),
        }
        ERRORS_COOKIE.remove(self.request.session)
        context = add_base_context(self.request, super_context | new_context)
        return context

    def _get_filter_props(self):
        session = self.request.session
        fan_filter_props = []
        for fan in self.fan_list:
            fan_filter = self.fan_filters[fan]
            filter_on = fan_filter.on(session)
            fan_filter_props_dict = {
                'fan': fan,
                'href_filter': fan_filter.get_href_filter(session),
                'action': fan_filter.action(session),
                'on': filter_on,
            }
            if filter_on:
                fan_filter_props = [fan_filter_props_dict]
                break
            fan_filter_props.append(fan_filter_props_dict)
        return fan_filter_props

    @staticmethod
    def _can_submit(session):
        fan = AvailabilityView.fan_cookie.get(session)
        start_dt = AvailabilityView.get_dt(session, 'start_day', 'start_time')
        end_dt = AvailabilityView.get_dt(session, 'end_day', 'end_time')
        if end_dt <= start_dt:
            set_error(session, 'End of period earlier than begin')
            return False
        elif Availabilities.availabilities.filter(fan__name=fan, start_dt=start_dt).exists():
            set_error(session, 'A period with this fan and start already exists')
            return False
        return True


class AvailabilityFormView(LoginRequiredMixin, FormView):
    template_name = AvailabilityView.template_name
    http_method_names = ['post']
    form_class = AvailabilityForm
    success_url = '/availabilities/list'

    def form_valid(self, form):
        session = self.request.session
        post = self.request.POST
        if 'day' in post:
            AvailabilityView.start_day.set_str(session, post['day'], is_choice=True)
        if 'time' in post:
            AvailabilityView.start_time.set(session, post['time'])
        if 'alt_day' in post:
            AvailabilityView.end_day.set_str(session, post['alt_day'], is_choice=True)
        if 'alt_time' in post:
            AvailabilityView.end_time.set(session, post['alt_time'])
        if 'fan' in post:
            AvailabilityView.fan_cookie.set(session, post['fan'])
        if 'add' in post:
            fan_name = AvailabilityView.fan_cookie.get(session)
            start_dt = AvailabilityView.get_dt(session, 'start_day', 'start_time')
            end_dt = AvailabilityView.get_dt(session, 'end_day', 'end_time')
            AvailabilityForm.add_availability(fan_name=fan_name, start_dt=start_dt, end_dt=end_dt)
        return super().form_valid(form)

    def form_invalid(self, form):
        ERRORS_COOKIE.set(self.request.session, wrap_up_form_errors(form.errors))
        super().form_invalid(form)
        return HttpResponseRedirect(reverse('availabilities:list'))
