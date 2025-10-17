import datetime

from festivals.models import current_festival
from screenings.models import Screening

FILTERED_INDICATOR = '🔬'


class Cookie:
    """
    Support basic operations on same-keyed cookies.
    """
    def __init__(self, cookie_key, initial_value=None):
        self._cookie_key = cookie_key
        self._initial_value = initial_value

    def _set_value_from_session(self, session, default=None):
        """
        Link the cookie to a session.
        """
        self.set(session, session.get(self._cookie_key, default or self._initial_value))

    def get_cookie_key(self):
        return self._cookie_key

    def handle_get_request(self, request):
        """
        Find cookie in a GET request and update its value accordingly.
        """
        if self._cookie_key in request.GET:
            query_value = request.GET[self._cookie_key]
            self.set(request.session, query_value)

    @staticmethod
    def get_querystring(**kwargs):
        query_list = [f'{key}={value}' for key, value in kwargs.items()]
        return '?' + '&'.join(query_list) if query_list else ''

    def get(self, session, default=None):
        """
        Return the cookie value from the session or default if it doesn't exist.
        """
        self._set_value_from_session(session, default=default)
        value = session.get(self._cookie_key)
        return value

    def set(self, session, value):
        session[self._cookie_key] = value

    def remove(self, session):
        if self._cookie_key in session:
            del session[self._cookie_key]


ERRORS_COOKIE = Cookie('error', initial_value=[])
WARNING_COOKIE = Cookie('warning', initial_value=[])


class Alert:
    alert_cookie = None

    def __init__(self, alert_cookie):
        self.alert_cookie = alert_cookie

    def set(self, session, messages):
        self.alert_cookie.set(session, messages)

    def get(self, session):
        return self.alert_cookie.get(session)

    def add(self, session, message):
        alerts = self.alert_cookie.get(session)
        alerts.append(message)
        self.alert_cookie.set(session, alerts)

    def remove(self, session):
        self.alert_cookie.remove(session)


class Errors(Alert):
    def __init__(self):
        super().__init__(ERRORS_COOKIE)


class Warnings(Alert):
    def __init__(self):
        super().__init__(WARNING_COOKIE)


class Filter(Cookie):
    """
    Provide filtering data on an "on/off" basis.
    """
    filtered_by_query = {'display': False, 'hide': True}
    query_by_filtered = {filtered: query for query, filtered in filtered_by_query.items()}

    def __init__(self, action_subject, cookie_key=None, filtered=False, action_true=None, action_false=None):
        super().__init__(cookie_key or action_subject.strip().replace(' ', '-'), initial_value=filtered)
        action_true = action_true or f'Display {action_subject}'
        action_false = action_false or f'Hide {action_subject}'
        self._action_by_filtered = {True: action_true, False: action_false}

    def __str__(self):
        return f'Filter {self.get_cookie_key()}'

    def handle_get_request(self, request):
        """
        Find cookie in a GET request and update its filter on/off value accordingly.
        """
        if self._cookie_key in request.GET:
            query_key = request.GET[self._cookie_key]
            filtered = self.filtered_by_query[query_key]
            self.set(request.session, filtered)

    def get_href_filter(self, session, extra_filters=None):
        """
        Shortcut filter query as to use in template url tag.
        """
        filters = [self]
        filters.extend(extra_filters or [])
        kwargs = {f.get_cookie_key(): f.next_query(session) for f in filters}
        return self.get_querystring(**kwargs)

    @classmethod
    def get_display_query_from_keys(cls, filter_keys, on=False):
        kwargs = {key: cls.query_by_filtered[on] for key in filter_keys}
        return cls.get_querystring(**kwargs)

    def on(self, session, default=None):
        return self.get(session, default)

    def off(self, session, default=None):
        return not self.on(session, default)

    def next_query(self, session):
        """
        Toggles the filter query.
        """
        return self.query_by_filtered[self.off(session)]

    def action(self, session):
        """
        Return the filter action text belonging to the current filter state.
        """
        return self._action_by_filtered[self.on(session)]

    def label(self, session):
        return self._action_by_filtered[self.off(session)]


class FestivalDay:
    choice_str_format = '%a %Y-%m-%d'
    date_str_format = choice_str_format.split()[1]

    def __init__(self, cookie_key):
        self.festival = None
        self.day_cookie = Cookie(cookie_key)

    @classmethod
    def choice_str(cls, date):
        return date.strftime(cls.choice_str_format)

    @classmethod
    def date_str(cls, date):
        return date.strftime(cls.date_str_format)

    def get_date(self, session, default=None):
        day_str = self.day_cookie.get(session, default=default)
        return datetime.date.fromisoformat(day_str or default)

    def get_datetime(self, session, time):
        date = self.get_date(session)
        return datetime.datetime.combine(date, time)

    def get_str(self, session):
        date = self.get_date(session)
        return self.choice_str(date)

    def set_str(self, session, day_str, is_choice=False):
        day_str = day_str.split()[1] if is_choice else day_str
        self.day_cookie.set(session, day_str)

    def get_festival_days(self):
        day = self.festival.start_date
        delta = datetime.timedelta(days=1)
        all_days = self.festival.end_date - self.festival.start_date + delta
        day_choices = []
        for factor in range(all_days.days):
            day_choices.append(self.choice_str(day + factor * delta))
        return day_choices

    def check_festival_day(self, session, last=False):
        self.festival = current_festival(session)
        day_str = self.day_cookie.get(session)
        if day_str:
            if day_str < self.festival.start_date.isoformat() or day_str > self.festival.end_date.isoformat():
                day_str = ''
        if not day_str:
            day_str = self.alternative_day_str(last=last)
            self.day_cookie.set(session, day_str)

    def alternative_day_str(self, last=False):
        try:
            first_screening = (Screening.screenings.filter(film__festival=self.festival).earliest('start_dt'))
            day_str = first_screening.start_dt.date().isoformat()
        except Screening.DoesNotExist:
            day_str = self.festival.start_date.isoformat()
        return day_str


def get_fan_filter_props(session, queryset, fans, filter_by_fan):
    obj_field = 'fan'
    label_by_fan = {fan: fan.name for fan in fans}
    return get_filter_props(session, queryset, fans, obj_field, filter_by_fan, label_by_fan)


def get_filter_props(session, queryset, choice_objects, choice_field, filter_by_obj, label_by_obj):
    objects_in_list = {getattr(query_obj, choice_field) for query_obj in queryset}
    filter_on = False
    obj_filter_choices = []
    for obj in choice_objects:
        obj_filter = filter_by_obj[obj]
        filter_on = obj_filter.on(session)
        obj_filter_choices_dict = {
            'label': label_by_obj[obj],
            'href_filter': obj_filter.get_href_filter(session),
            'action': obj_filter.action(session),
            'enabled': obj in objects_in_list,
            'on': filter_on,
        }
        if filter_on:
            obj_filter_choices_dict['enabled'] = True
            obj_filter_choices = [obj_filter_choices_dict]
            break
        obj_filter_choices.append(obj_filter_choices_dict)
    obj_filter_props = {
        'title': choice_field,
        'header': f'Select {choice_field}',
        'on': filter_on,
        'choices': obj_filter_choices,
    }
    return obj_filter_props
