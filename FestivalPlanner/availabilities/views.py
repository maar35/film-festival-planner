import datetime

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import FormView

from authentication.models import FilmFan, get_sorted_fan_list, get_fan_by_name
from availabilities.forms.availabilities_forms import AvailabilityForm
from availabilities.models import Availabilities
from festival_planner.cookie import Cookie, Filter, FestivalDay, get_fan_filter_props
from festival_planner.debug_tools import ProfiledListView
from festival_planner.screening_status_getter import ScreeningWarning, get_warnings
from festival_planner.shared_template_referrer_view import SharedTemplateReferrerView
from festival_planner.tools import add_base_context, wrap_up_form_errors, get_log, unset_log, add_log, initialize_log
from festivals.models import current_festival
from films.models import current_fan

DAY_BREAK_TIME = datetime.time(hour=6)
DAY_START_TIME = datetime.time(hour=8)
TIME_CHOICES = [
    DAY_START_TIME.strftime('%H:%M'),
    '10:00', '11:00', '12:00', '13:00', '15:00', '18:00', '20:00', '23:00', '00:30',
    DAY_BREAK_TIME.strftime('%H:%M')
]
START_TIME_CHOICES = TIME_CHOICES[:-1]
END_TIME_CHOICES = TIME_CHOICES[1:]

ERRORS_COOKIE = Cookie('form_errors', initial_value=[])
WARNING_COOKIE = Cookie('warnings', initial_value=[])
ACTION_COOKIE = Cookie('form_action')


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


class AvailabilityView(SharedTemplateReferrerView):
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
    confirm = None
    delete_queryset = None
    merge_queryset = None

    def __init__(self):
        super().__init__()
        self.list_view = AvailabilityListView
        self.form_view = AvailabilityFormView

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
        date_attr.check_festival_day(session, last=last)


class AvailabilityListView(LoginRequiredMixin, ProfiledListView):
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
    reminder_cookie = Cookie('reminder')
    fan_list = None
    form = AvailabilityForm
    title = 'Availabilities List'
    festival = None

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.fan = None
        self.warning_rows = None
        self.filters = None
        self.filter_by_fan = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        session = request.session
        try:
            add_log(session, 'Setup list view.')
        except (TypeError, KeyError):
            initialize_log(session, 'Update availabilities')

        # Get festival period from session.
        self.festival = current_festival(session)

        # Get warnings.
        self.warning_rows = get_warnings(self.festival, self._get_warning_details)

        # Set up the fan filters. TODO: Generalize fan, section and subsection filtering, #393.
        self.fan = current_fan(session)
        self.fan_list = get_sorted_fan_list(self.fan)
        self.filters = []
        self.filter_by_fan = {}
        for fan in self.fan_list:
            self.filter_by_fan[fan] = Filter('fan',
                                             cookie_key=f'fan-{fan.id}',
                                             action_false='Select fan',
                                             action_true='Remove filter')
            self.filters.append(self.filter_by_fan[fan])

        # Reset form times if the festival changed.
        AvailabilityView.check_dt_from_session(session, 'start_day', 'start_time')
        AvailabilityView.check_dt_from_session(session, 'end_day', 'end_time')

    def dispatch(self, request, *args, **kwargs):
        session = request.session

        # Get reminder cookie data.
        if 'warning_name' in request.GET and 'fan_name' in request.GET:
            warning_name = request.GET['warning_name']
            fan_name = request.GET['fan_name']
            self.reminder_cookie.set(session, {'warning_name': warning_name, 'fan_name': fan_name})

        # Refresh the fan filters.
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
            if self.filter_by_fan[fan].on(self.request.session):
                kwargs['fan'] = fan
                break
        selected_availabilities = manager.filter(**kwargs).order_by('start_dt', 'end_dt', 'fan__name')
        self.queryset = selected_availabilities
        return selected_availabilities  # availability_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        self.festival = current_festival(session)
        fan = self._get_availability_fan(session)
        can_submit = self._can_submit(session, fan.name)
        reminders = self._get_reminders(session)
        action = ACTION_COOKIE.get(session, 'get') or 'def'
        warnings = [row['warning'] for row in self.warning_rows]
        new_context = {
            'title': self.title,

            'fan_label': 'Filmfan:',
            'fan': fan,
            'fan_choices': self.fan_list,

            'start_day_label': 'Start date:',
            'start_day': AvailabilityView.start_day.get_str(session),
            'start_day_choices': AvailabilityView.start_day.get_festival_days(),
            'start_time_label': 'Start time:',
            'start_time': AvailabilityView.start_time.get(session),
            'start_time_choices': START_TIME_CHOICES,

            'end_day_label': 'End day:',
            'end_day': AvailabilityView.end_day.get_str(session),
            'end_day_choices': AvailabilityView.end_day.get_festival_days(),
            'end_time_label': 'End time:',
            'end_time': AvailabilityView.end_time.get(session),
            'end_time_choices': END_TIME_CHOICES,

            'can_submit': can_submit,
            'action': action,
            'value': self.button_text_by_action[action],
            'confirm': AvailabilityView.confirm,
            'festival_start_dt': get_festival_dt(self.festival.start_date, DAY_START_TIME),
            'festival_end_dt': get_festival_dt(self.festival.end_date, DAY_BREAK_TIME),
            'fan_filter_props': self._get_filter_props(),
            'reminders': reminders,
            'log': get_log(session),
            'warnings': WARNING_COOKIE.get(session),
            'form_errors': ERRORS_COOKIE.get(session),
            'stats': ScreeningWarning.get_warning_stats(self.festival, warnings=warnings),
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
        return get_fan_filter_props(session, self.queryset, self.fan_list, self.filter_by_fan)

    @staticmethod
    def _get_warning_details(warning):
        return {
            'warning': warning,
            'fan_name': warning.fan.name,
            'warning_name': warning.warning.name,
            'start_dt': warning.screening.start_dt,
        }

    def _get_reminders(self, session):
        reminder_dict = self.reminder_cookie.get(session)
        if not reminder_dict:
            return []
        fan_name = reminder_dict['fan_name']
        warning_name = reminder_dict['warning_name']
        reminders = []
        for row in sorted(self.warning_rows, key=lambda r: r['start_dt']):
            if row['fan_name'] == fan_name and row['warning_name'] == warning_name:
                warning = row['warning']
                start_dt = warning.screening.start_dt
                end_time = warning.screening.end_dt.time()
                title = warning.screening.film.title
                reminder = f'{fan_name} should be available from {start_dt} till {end_time} to see {title}.'
                reminders.append(reminder)
        return reminders

    def _get_availability_fan(self, session):
        fan_name = AvailabilityView.fan_cookie.get(session, default=self.fan.name)
        fan = get_fan_by_name(fan_name)
        return fan

    def _can_submit(self, session, fan_name):
        add_log(session, 'Check submit.')
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
        handle_new_period(session)
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


class AvailabilityFormView(LoginRequiredMixin, FormView):
    template_name = AvailabilityView.template_name
    http_method_names = ['post']
    form_class = AvailabilityForm
    success_url = '/availabilities/list/'

    def form_valid(self, form):
        session = self.request.session
        match self.request.POST:
            case {'fan': fan}:
                AvailabilityView.fan_cookie.set(session, fan)
            case {'start_day': start_day}:
                AvailabilityView.start_day.set_str(session, start_day, is_choice=True)
            case {'start_time': start_time}:
                AvailabilityView.start_time.set(session, start_time)
            case {'end_day': end_day}:
                AvailabilityView.end_day.set_str(session, end_day, is_choice=True)
            case {'end_time': end_time}:
                AvailabilityView.end_time.set(session, end_time)
            case {'add': _} | {'merge': _} | {'delete': _}:
                AvailabilityView.confirm = True
            case {'add_confirmed': _}:
                handle_new_period(session, update_db=True, action='add')
            case {'merge_confirmed': _}:
                handle_period_overlaps_existing_period(session, update_db=True, action='merge')
            case {'delete_confirmed': _}:
                handle_period_in_existing_period(session, update_db=True, action='delete')
            case {'add_canceled': _}:
                add_log(session, 'Add new availability period canceled.')
            case {'merge_canceled': _}:
                add_log(session, 'Merge of overlapping availabilities canceled.')
            case {'delete_canceled': _}:
                add_log(session, 'Partly delete of an existing availability canceled.')

        return super().form_valid(form)

    def form_invalid(self, form):
        ERRORS_COOKIE.set(self.request.session, wrap_up_form_errors(form.errors))
        super().form_invalid(form)
        return HttpResponseRedirect(reverse('availabilities:list'))


def get_new_availability_data(session):
    fan_name = AvailabilityView.fan_cookie.get(session)
    start_dt = AvailabilityView.get_dt(session, 'start_day', 'start_time')
    end_dt = AvailabilityView.get_dt(session, 'end_day', 'end_time')
    return fan_name, start_dt, end_dt


def handle_new_period(session, update_db=False, action=None):
    fan_name, start_dt, end_dt = get_new_availability_data(session)
    fan = FilmFan.film_fans.get(name=fan_name)
    new_obj = Availabilities(fan=fan, start_dt=start_dt, end_dt=end_dt)
    if update_db:
        try:
            AvailabilityForm.add_availability(session, new_obj)
        except Exception as e:
            set_error(session, str(e), action)


def get_overlapping_objects(session):
    add_log(session, 'Add availability.')
    fan_name, start_dt, end_dt = get_new_availability_data(session)
    fan = FilmFan.film_fans.get(name=fan_name)
    input_obj = Availabilities(fan=fan, start_dt=start_dt, end_dt=end_dt)
    merge_objects_set = set(AvailabilityView.merge_queryset) | {input_obj}
    new_start_dt = min([availability.start_dt for availability in merge_objects_set])
    new_end_dt = max([availability.end_dt for availability in merge_objects_set])
    new_obj = Availabilities(fan=fan, start_dt=new_start_dt, end_dt=new_end_dt)
    return AvailabilityView.merge_queryset, new_obj


def handle_period_overlaps_existing_period(session, update_db=False, action=None):
    add_log(session, 'Merge overlapping periods.')
    merge_objects, new_obj = get_overlapping_objects(session)
    for merge_obj in merge_objects:
        add_log(session, f'"{merge_obj}" will be deleted.')
    add_log(session, f'"{new_obj}" will be inserted.')
    if update_db:
        try:
            AvailabilityForm.merge_availabilities(session, merge_objects, new_obj)
        except Exception as e:
            set_error(session, str(e), action)


def get_containing_objects(session):
    fan_name, start_dt, end_dt = get_new_availability_data(session)
    fan = FilmFan.film_fans.get(name=fan_name)
    for org_obj in AvailabilityView.delete_queryset:
        first_remaining_period = Availabilities(fan=fan, start_dt=org_obj.start_dt, end_dt=start_dt)
        last_remaining_period = Availabilities(fan=fan, start_dt=end_dt, end_dt=org_obj.end_dt)
        yield org_obj, first_remaining_period, last_remaining_period


def handle_period_in_existing_period(session, update_db=False, action=None):
    add_log(session, 'Delete part of existing availability.')
    for org_obj, first_remaining_obj, last_remaining_obj in get_containing_objects(session):
        add_log(session, f'"{org_obj}" will be deleted.')
        add_log(session, f'"{first_remaining_obj}" will be inserted.')
        add_log(session, f'"{last_remaining_obj}" will be inserted.')
        if update_db:
            try:
                AvailabilityForm.delete_part_of_availability(session, org_obj,
                                                             first_remaining_obj,
                                                             last_remaining_obj)
            except Exception as e:
                set_error(session, str(e), action)
