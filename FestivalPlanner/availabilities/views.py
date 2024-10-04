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
from festival_planner.tools import add_base_context, wrap_up_form_errors, get_log, unset_log, add_log, initialize_log
from festivals.models import current_festival
from films.models import current_fan
from screenings.views import FestivalDay

DAY_BREAK_TIME = datetime.time(hour=6)
DAY_START_TIME = datetime.time(hour=8)
ERRORS_COOKIE = Cookie('form_errors', initial_value=[])
WARNING_COOKIE = Cookie('warnings', initial_value=[])
ACTION_COOKIE = Cookie('form_action')
DEFAULT_FAN = FilmFan.film_fans.get(name='Maarten')


def get_festival_dt(date, time):
    if time <= DAY_BREAK_TIME:
        date += datetime.timedelta(days=1)
    dt = datetime.datetime.combine(date, time)
    return dt


def set_error(session, error, action):
    ERRORS_COOKIE.set(session, [error])
    ACTION_COOKIE.set(session, action)


def set_warning(session, warning, action):
    WARNING_COOKIE.set(session, [warning])
    ACTION_COOKIE.set(session, action)


def set_info(session, action):
    ACTION_COOKIE.set(session, action)


class AvailabilityDay(FestivalDay):
    def alternative_day_str(self, last=False):
        if last:
            return self.festival.end_date.isoformat()
        else:
            return self.festival.start_date.isoformat()


class AvailabilityView(LoginRequiredMixin, View):
    """
    Class te receive and forward requests on availabilities.
    """
    template_name = 'availabilities/list.html'
    initial_start_time = DAY_START_TIME.strftime('%H:%M')
    initial_end_time = DAY_BREAK_TIME.strftime('%H:%M')
    fan_cookie = Cookie('available_fan', initial_value=DEFAULT_FAN.name)
    start_day = AvailabilityDay('start_day')
    start_time = Cookie('start_time', initial_value=initial_start_time)
    end_day = AvailabilityDay('end_day')
    end_time = Cookie('end_time', initial_value=initial_end_time)
    confirm = None
    delete_queryset = None
    merge_queryset = None

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

    @classmethod
    def check_dt_from_session(cls, session, date_field, time_field):
        festival = current_festival(session)
        date_attr = getattr(cls, date_field)
        time_attr = getattr(cls, time_field)
        last = 'end' in date_field
        default = (festival.end_date if last else festival.start_date).isoformat()
        date = date_attr.get_date(session, default=default)
        if not (date and festival.has_date(date)):
            time_attr.set(session, (DAY_BREAK_TIME if last else DAY_START_TIME).strftime('%H:%M'))
        _ = date_attr.check_session(session, last=last)


class AvailabilityListView(LoginRequiredMixin, ListView):
    """
    Lists the known availability periods of all fans within the current festival.
    """
    template_name = AvailabilityView.template_name
    context_object_name = 'availability_rows'
    http_method_names = ['get']
    object_list = []
    button_text_by_action = {
        'add': 'Add period',
        'delete': 'Delete from existing',
        'merge': 'Merge periods',
        'earlier': 'End before start',
        'exists': 'Fan&start exists',
        'get': '',
        'def': 'DEFAULT',
    }
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
        session = request.session
        try:
            add_log(session, 'Setup list view.')
        except TypeError:
            initialize_log(session, 'Update availabilities')

        # Get festival period from session.
        self.festival = current_festival(session)

        # Set up the fan filters. TODO: Generalize fan, section and subsection filtering.
        self.filters = []
        self.fan_filters = {}
        for fan in self.fan_list:
            self.fan_filters[fan] = Filter('fan',
                                           cookie_key=f'fan-{fan.id}',
                                           action_false='Select fan',
                                           action_true='Remove filter')
            self.filters.append(self.fan_filters[fan])

        # Reset form times if the festival changed.
        AvailabilityView.check_dt_from_session(session, 'start_day', 'start_time')
        AvailabilityView.check_dt_from_session(session, 'end_day', 'end_time')

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
        filtered = [prop['on'] for prop in fan_filter_props if prop['on']]
        day_start_str = DAY_START_TIME.strftime('%H:%M')
        day_break_str = DAY_BREAK_TIME.strftime('%H:%M')
        time_choices = [day_start_str, '10:00', '12:00', '15:00', '18:00', '20:00', '23:00', '00:30', day_break_str]
        can_submit = self._can_submit(session)
        action = ACTION_COOKIE.get(session, 'get') or 'def'
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
            'can_submit': can_submit,
            'action': action,
            'value': self.button_text_by_action[action],
            'confirm': AvailabilityView.confirm,
            'festival_start_dt': get_festival_dt(self.festival.start_date, DAY_START_TIME),
            'festival_end_dt': get_festival_dt(self.festival.end_date, DAY_BREAK_TIME),
            'fan_filter_props': fan_filter_props,
            'filtered': filtered,
            'log': get_log(session),
            'warnings': WARNING_COOKIE.get(session),
            'form_errors': ERRORS_COOKIE.get(session),
        }
        AvailabilityView.confirm = False
        unset_log(session)
        initialize_log(session, 'Manage availability')
        ERRORS_COOKIE.remove(session)
        WARNING_COOKIE.remove(session)
        ACTION_COOKIE.remove(session)
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

    def _can_submit(self, session):
        add_log(session, 'Check submit.')
        fan_name = AvailabilityView.fan_cookie.get(session)
        start_dt = AvailabilityView.get_dt(session, 'start_day', 'start_time')
        end_dt = AvailabilityView.get_dt(session, 'end_day', 'end_time')
        strf_spec = "%Y-%m-%d %H:%M"
        add_log(session, f'Selected {fan_name} {start_dt.strftime(strf_spec)} - {end_dt.strftime(strf_spec)}.')
        if end_dt <= start_dt:
            set_error(session, 'End of period earlier than begin', action='earlier')
            return False
        elif self._period_in_existing_period(session, fan_name, start_dt, end_dt):
            set_warning(session, 'Period fits in existing period, overlap will be deleted', 'delete')
            handle_period_in_existing_period(session)
            return True
        elif self._period_overlaps_existing_period(session, fan_name, start_dt, end_dt):
            set_warning(session, 'Period overlaps existing period, they will be merged', 'merge')
            handle_period_overlaps_existing_period(session)
            return True
        set_info(session, 'add')
        return True

    @staticmethod
    def _period_in_existing_period(session, fan_name, start_dt, end_dt):
        add_log(session, f'Checking existence of {fan_name}, start<={start_dt}, end>={end_dt}.')
        manager = Availabilities.availabilities
        existing_set = manager.filter(fan__name=fan_name, start_dt__lte=start_dt, end_dt__gte=end_dt)
        if existing_set:
            add_log(session, f'Found {existing_set.count()} object(s):')
            for queryset in existing_set:
                add_log(session, f'"{str(queryset)}" contains the new period.')
            AvailabilityView.delete_queryset = existing_set
            return True
        add_log(session, 'No availabilities that contain the new period.')
        return False

    @staticmethod
    def _period_overlaps_existing_period(session, fan_name, start_dt, end_dt):
        add_log(session, f'Checking overlap of {fan_name}, start_dt<={end_dt}, end_dt>={start_dt}.')
        manager = Availabilities.availabilities
        overlapping_set = manager.filter(fan__name=fan_name, start_dt__lte=end_dt, end_dt__gte=start_dt)
        if overlapping_set:
            add_log(session, f'Found {overlapping_set.count()} object(s):')
            for queryset in overlapping_set:
                add_log(session, f'"{str(queryset)}" can be merged.')
            AvailabilityView.merge_queryset = overlapping_set
            return True
        add_log(session, 'No overlapping availabilities.')
        return False


def get_new_availability_data(session):
    fan_name = AvailabilityView.fan_cookie.get(session)
    start_dt = AvailabilityView.get_dt(session, 'start_day', 'start_time')
    end_dt = AvailabilityView.get_dt(session, 'end_day', 'end_time')
    return fan_name, start_dt, end_dt


def get_containing_objects(session):
    fan_name, start_dt, end_dt = get_new_availability_data(session)
    fan = FilmFan.film_fans.get(name=fan_name)
    for org_obj in AvailabilityView.delete_queryset:
        first_remaining_period = Availabilities(fan=fan, start_dt=org_obj.start_dt, end_dt=start_dt)
        last_remaining_period = Availabilities(fan=fan, start_dt=end_dt, end_dt=org_obj.end_dt)
        yield org_obj, first_remaining_period, last_remaining_period


def handle_period_in_existing_period(session, update_db=False):
    add_log(session, 'Delete part of existing availability.')
    for org_obj, first_remaining_obj, last_remaining_obj in get_containing_objects(session):
        add_log(session, f'"{org_obj}" will be deleted.')
        add_log(session, f'"{first_remaining_obj}" will be inserted.')
        add_log(session, f'"{last_remaining_obj}" will be inserted.')
        if update_db:
            AvailabilityForm.delete_part_of_availability(session, org_obj,
                                                         first_remaining_obj,
                                                         last_remaining_obj)


def get_overlapping_objects(session):
    fan_name, start_dt, end_dt = get_new_availability_data(session)
    fan = FilmFan.film_fans.get(name=fan_name)
    input_obj = Availabilities(fan=fan, start_dt=start_dt, end_dt=end_dt)
    merge_objects_set = set(AvailabilityView.merge_queryset) | {input_obj}
    new_start_dt = min([availability.start_dt for availability in merge_objects_set])
    new_end_dt = max([availability.end_dt for availability in merge_objects_set])
    new_obj = Availabilities(fan=fan, start_dt=new_start_dt, end_dt=new_end_dt)
    return AvailabilityView.merge_queryset, new_obj


def handle_period_overlaps_existing_period(session, update_db=False):
    add_log(session, 'Merge overlapping periods.')
    merge_objects, new_obj = get_overlapping_objects(session)
    for merge_obj in merge_objects:
        add_log(session, f'"{merge_obj}" will be deleted.')
    add_log(session, f'"{new_obj}" will be inserted.')
    if update_db:
        AvailabilityForm.merge_availabilities(session, merge_objects, new_obj)


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
            AvailabilityView.confirm = True
        if 'add_confirmed' in post:
            fan_name, start_dt, end_dt = get_new_availability_data(session)
            AvailabilityForm.add_availability(session, fan_name=fan_name, start_dt=start_dt, end_dt=end_dt)
        if 'add_canceled' in post:
            add_log(session, 'Add new availability period canceled.')
        if 'merge' in post:
            AvailabilityView.confirm = True
        if 'merge_confirmed' in post:
            handle_period_overlaps_existing_period(session, update_db=True)
        if 'merge_canceled' in post:
            add_log(session, 'Merge of overlapping availabilities canceled.')
        if 'delete' in post:
            AvailabilityView.confirm = True
        if 'delete_confirmed' in post:
            handle_period_in_existing_period(session, update_db=True)
        if 'delete_canceled' in post:
            add_log(session, 'Partly delete of an existing availability canceled.')

        return super().form_valid(form)

    def form_invalid(self, form):
        ERRORS_COOKIE.set(self.request.session, wrap_up_form_errors(form.errors))
        super().form_invalid(form)
        return HttpResponseRedirect(reverse('availabilities:list'))
