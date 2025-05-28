from copy import deepcopy
from enum import Enum, auto

from authentication.models import FilmFan, get_sorted_fan_list
from festival_planner.cookie import Filter, Cookie
from festival_planner.debug_tools import pr_debug
from festival_planner.fragment_keeper import ScreenFragmentKeeper
from festivals.models import current_festival
from films.models import current_fan, get_present_fans
from screenings.models import Screening, Attendance, COLOR_PAIR_SELECTED, Ticket, COLOR_WARNING_ORANGE, \
    COLOR_WARNING_YELLOW, COLOR_WARNING_RED

TICKET_BUY_SELL_WARNING_SYMBOL = '!'
TICKET_CONFIRMATION_WARNING_SYMBOL = '?️'
ATTENDANCE_WARNING_SYMBOL = '⛔'


def get_color_matrix():
    status = Screening.ScreeningStatus
    warning_type = ScreeningWarning.WarningType
    color_by_warning_by_status = {}
    color_by_screening_status = Screening.color_warning_by_screening_status
    for warning in warning_type.__iter__():
        color_by_warning_by_status[warning] = deepcopy(color_by_screening_status)
    color_by_warning_by_status[warning_type.AWAITS_CONFIRMATION][status.ATTENDS] = COLOR_WARNING_RED
    color_by_warning_by_status[warning_type.AWAITS_CONFIRMATION][status.FRIEND_ATTENDS] = COLOR_WARNING_YELLOW
    color_by_warning_by_status[warning_type.AWAITS_CONFIRMATION][status.NEEDS_TICKETS] = COLOR_WARNING_YELLOW
    color_by_warning_by_status[warning_type.AWAITS_CONFIRMATION][status.SHOULD_SELL_TICKETS] = COLOR_WARNING_ORANGE
    color_by_warning_by_status[warning_type.SHOULD_SELL_TICKET][status.UNAVAILABLE] = 'orange'
    color_by_warning_by_status[warning_type.AWAITS_CONFIRMATION][status.UNAVAILABLE] = COLOR_WARNING_ORANGE
    return color_by_warning_by_status


def get_warning_color(screening_status, warning_type):
    color_matrix = ScreeningWarning.color_by_warning_by_status
    if not color_matrix:
        color_matrix = get_color_matrix()

    color = color_matrix[warning_type][screening_status.value]
    return color


def to_sentence_case(sentence):
    lower_case_sentence = sentence.lower().replace('_', ' ')
    return lower_case_sentence[0].upper() + lower_case_sentence[1:]


def get_ticket_holders(screening, current_filmfan, confirmed=None):
    kwargs = {'screening': screening}
    if confirmed is not None:
        kwargs['confirmed'] = confirmed
    fan_ids = Ticket.tickets.filter(**kwargs).values_list('fan', flat=True)
    ticket_holders = FilmFan.film_fans.filter(id__in=fan_ids)
    sorted_holders = get_sorted_fan_list(current_filmfan, fan_query_set=ticket_holders)
    return sorted_holders


def get_warnings_keys(festival):
    """
    Return a set of screening-fan tuples that could have one or more
    warnings.
    """
    pr_debug('start', with_time=True)
    attendances = Attendance.attendances.filter(screening__film__festival=festival)
    a_keys_set = {(attendance.screening, attendance.fan) for attendance in attendances}
    tickets = Ticket.tickets.filter(screening__film__festival=festival)
    t_keys_set = {(ticket.screening, ticket.fan) for ticket in tickets}
    keys_set = a_keys_set | t_keys_set
    pr_debug('done', with_time=True)
    return keys_set


def get_warnings(festival, details_getter, keys_set=None):
    """
    Get all warnings concerning the given festival.
    The details getter should deliver objects that will be the
    elements of the returned list.
    """
    pr_debug('start', with_time=True)
    keys_set = keys_set or get_warnings_keys(festival)
    warning_details = []
    for keys in keys_set:
        for warning in get_fan_warnings(*keys):
            warning_details.append(details_getter(warning))
    pr_debug('done', with_time=True)
    return warning_details


def get_warning_details(warnings, details_getter):
    pr_debug('start', with_time=True)
    warning_details = []
    for warning  in warnings:
        warning_details.append(details_getter(warning))
    pr_debug('done', with_time=True)
    return warning_details


def screening_warnings(fans, screening):
    warnings = []
    for fan in fans:
        warnings.extend(get_fan_warnings(screening, fan))
    return warnings


def get_fan_warnings(screening, fan):
    return ScreeningWarning.get_fan_warnings(screening, fan)


class ScreeningStatusGetter:
    screening_cookie = Cookie('screening')

    def __init__(self, session, day_screenings):
        self.session = session
        self.day_screenings = day_screenings
        self.fan = current_fan(self.session)
        self.fans = get_sorted_fan_list(self.fan)
        self.attendances_by_screening = self._get_attendances_by_screening()
        self.attends_by_screening = {s: self.attendances_by_screening[s].filter(fan=self.fan) for s in day_screenings}
        self.has_attended_film_by_screening = self._get_has_attended_film_by_screening()
        self.available_by_screening_by_fan = self._get_availability_by_screening_by_fan()

    def update_attendances_by_screening(self, screening):
        self.attendances_by_screening[screening] = Attendance.attendances.filter(screening=screening)
        self.attends_by_screening[screening] = True
        self.has_attended_film_by_screening = self._get_has_attended_film_by_screening()

    def get_screening_status(self, screening, attendants):
        fan = current_fan(self.session)
        if fan in attendants:
            if screening.fan_has_ticket(fan):
                status = Screening.ScreeningStatus.ATTENDS
            else:
                status = Screening.ScreeningStatus.NEEDS_TICKETS
        elif screening.fan_has_ticket(fan):
            status = Screening.ScreeningStatus.SHOULD_SELL_TICKETS
        elif attendants:
            status = Screening.ScreeningStatus.FRIEND_ATTENDS
        elif not self.fits_availability(screening):
            status = Screening.ScreeningStatus.UNAVAILABLE
        elif self._has_attended_film(screening):
            status = Screening.ScreeningStatus.ATTENDS_FILM
        else:
            status = self._get_other_status(screening, self.day_screenings)
        return status

    @classmethod
    def get_selected_screening(cls, request):
        cls.handle_screening_get_request(request)
        screening_pk_str = cls.screening_cookie.get(request.session)
        screening_pk = int(screening_pk_str) if screening_pk_str else None
        try:
            selected_screening = Screening.screenings.get(pk=screening_pk) if screening_pk else None
        except Screening.DoesNotExist:
            cls.screening_cookie.remove(request.session)
            selected_screening = None
        return selected_screening

    @classmethod
    def handle_screening_get_request(cls, request):
        cls.screening_cookie.handle_get_request(request)

    @classmethod
    def get_filmscreening_props(cls, session, film):
        pr_debug('start', with_time=True)
        festival = current_festival(session)
        festival_screenings = Screening.screenings.filter(film__festival=festival)
        filmscreenings = festival_screenings.filter(film=film).order_by('start_dt')
        dates = filmscreenings.dates('start_dt', 'day')
        film_screenings_props = []
        for date in dates:
            day_filmscreenings = filmscreenings.filter(start_dt__date=date)
            day_screenings = festival_screenings.filter(start_dt__date=date)
            getter = cls(session, day_screenings)
            film_screenings_props.extend([getter._get_day_props(s) for s in day_filmscreenings])
        pr_debug('done', with_time=True)
        return film_screenings_props

    def fits_availability(self, screening):
        try:
            fits = self.available_by_screening_by_fan[self.fan][screening]
        except KeyError:
            fits = False
        return fits

    def get_attendants(self, screening):
        attendances = self.attendances_by_screening[screening]
        attendant_ids = attendances.values_list('fan', flat=True)
        attendants = FilmFan.film_fans.filter(id__in=attendant_ids)
        sorted_attendants = get_sorted_fan_list(self.fan, fan_query_set=attendants)
        return sorted_attendants

    def get_attendants_str(self, screening):
        attendants = self.get_attendants(screening)
        return ', '.join([attendant.name for attendant in attendants])

    def get_attending_friends(self, screening):
        attendants = self.get_attendants(screening)
        return [fan for fan in attendants if fan != self.fan]

    def _get_attendances_by_screening(self):
        attendances_by_screening = {s: Attendance.attendances.filter(screening=s) for s in self.day_screenings}
        return attendances_by_screening

    def _get_has_attended_film_by_screening(self):
        manager = Attendance.attendances
        return {s: manager.filter(screening__film=s.film, fan=self.fan).exists() for s in self.day_screenings}

    def _has_attended_film(self, screening):
        """ Returns whether the current fan attends another screening of the same film. """
        current_fan_attends_other_filmscreening = self.has_attended_film_by_screening[screening]
        return current_fan_attends_other_filmscreening

    def _get_availability_by_screening_by_fan(self):
        availability_by_screening_by_fan = {}
        for fan in get_present_fans(self.session):
            availability_by_screening_by_fan[fan] = \
                {s: s.available_by_fan(fan) for s in self.day_screenings}
        return availability_by_screening_by_fan

    def _available_fans(self, screening):
        available_fan_ids = []
        for fan, available_by_screening in self.available_by_screening_by_fan.items():
            if available_by_screening[screening]:
                available_fan_ids.append(fan.id)
        fan_query_set = FilmFan.film_fans.filter(id__in=available_fan_ids)
        return get_sorted_fan_list(self.fan, fan_query_set=fan_query_set)

    def _get_other_status(self, screening, screenings):
        status = Screening.ScreeningStatus.FREE
        overlapping_screenings = []
        no_travel_time_screenings = []
        for s in screenings:
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

    def _get_day_props(self, film_screening):
        attendants = self.get_attendants(film_screening)
        ticket_holders = get_ticket_holders(film_screening, self.fan)
        status = self.get_screening_status(film_screening, attendants)
        warnings = screening_warnings(self.fans, film_screening)
        attendants_props = self._get_fan_props('attendant', attendants, warnings)
        ticket_holders_props = self._get_fan_props('ticket_holder', ticket_holders, warnings)
        available_fans = self._available_fans(film_screening)
        day = film_screening.start_dt.date().isoformat()
        day_props = {
            'film_screening': film_screening,
            'status': status,
            'day': day,
            'pair_selected': COLOR_PAIR_SELECTED,
            'pair': Screening.color_pair_by_screening_status[status],
            'attendants_props': attendants_props,
            'ticket_holders_props': ticket_holders_props,
            'confirmed_ticket_holders': self._get_confirmed_ticket_holders_props(film_screening),
            'available_fans': ', '.join([fan.name for fan in available_fans]),
            'q_and_a': film_screening.str_q_and_a(),
            'query_string': Filter.get_querystring(**{'day': day, 'screening': film_screening.pk}),
            'fragment': ScreenFragmentKeeper.fragment_code(film_screening.screen),
        }
        return day_props

    @classmethod
    def _get_warnings_props(cls, warnings):
        warnings_props = []
        for warning in warnings:
            props = {
                'name': warning.fan.name,
                'type': warning.warning,
                'wording': ScreeningWarning.wording_by_warning[warning.warning],
                'color': ScreeningWarning.color_by_warning[warning.warning],
                'fan_status': ScreeningWarning.fan_status_by_warning[warning.warning],
                'delimiter': ', ',
            }
            warnings_props.append(props)
        return warnings_props

    @classmethod
    def _get_fan_props(cls, fan_status, attendants, screening_warnings):
        status_by_warning = ScreeningWarning.fan_status_by_warning
        fan_status_warnings = [w for w in screening_warnings if status_by_warning[w.warning] == fan_status]
        fans_props = []
        for fan in attendants:
            warnings = [w for w in fan_status_warnings if w.fan == fan]
            if warnings:
                fan_props_list = cls._get_warnings_props(warnings)
                fans_props.extend(fan_props_list)
            else:
                fan_props = {'name': fan.name, 'delimiter': ', '}
                fans_props.append(fan_props)
        if fans_props:
            fans_props[-1]['delimiter'] = ''
        return fans_props

    def _get_confirmed_ticket_holders_props(self, screening):
        confirmed_ticket_holders = get_ticket_holders(screening, self.fan, confirmed=True)
        return confirmed_ticket_holders


class ScreeningWarning:
    """
    Represents a warning that concerns a screening and a filmfan.
    """

    class WarningType(Enum):
        ATTENDS_SAME_FILM = auto()
        ATTENDS_OVERLAPPING = auto()
        ATTENDS_WHILE_UNAVAILABLE = auto()
        NEEDS_TICKET = auto()
        AWAITS_CONFIRMATION = auto()
        SHOULD_SELL_TICKET = auto()

    wording_by_warning = {w: w.name.lower().replace('_', ' ') for w in WarningType}
    wording_by_warning[WarningType.NEEDS_TICKET] = 'needs a ticket'
    wording_by_warning[WarningType.SHOULD_SELL_TICKET] = 'should sell'

    color_by_warning_by_status = None
    color_by_warning = {
        WarningType.NEEDS_TICKET: COLOR_WARNING_ORANGE,
        WarningType.AWAITS_CONFIRMATION: COLOR_WARNING_YELLOW,
        WarningType.SHOULD_SELL_TICKET: COLOR_WARNING_ORANGE,
        WarningType.ATTENDS_SAME_FILM: COLOR_WARNING_RED,
        WarningType.ATTENDS_OVERLAPPING: COLOR_WARNING_RED,
        WarningType.ATTENDS_WHILE_UNAVAILABLE: COLOR_WARNING_RED,
    }

    fan_status_by_warning = {w: 'attendant' for w in WarningType}
    fan_status_by_warning[WarningType.AWAITS_CONFIRMATION] = 'ticket_holder'
    fan_status_by_warning[WarningType.SHOULD_SELL_TICKET] = 'ticket_holder'

    symbol_by_warning = {
        WarningType.NEEDS_TICKET: TICKET_BUY_SELL_WARNING_SYMBOL,
        WarningType.AWAITS_CONFIRMATION: TICKET_CONFIRMATION_WARNING_SYMBOL,
        WarningType.SHOULD_SELL_TICKET: TICKET_BUY_SELL_WARNING_SYMBOL,
        WarningType.ATTENDS_SAME_FILM: ATTENDANCE_WARNING_SYMBOL,
        WarningType.ATTENDS_OVERLAPPING: ATTENDANCE_WARNING_SYMBOL,
        WarningType.ATTENDS_WHILE_UNAVAILABLE: ATTENDANCE_WARNING_SYMBOL,
    }
    small_by_symbol = {
        TICKET_BUY_SELL_WARNING_SYMBOL: False,
        TICKET_CONFIRMATION_WARNING_SYMBOL: False,
        ATTENDANCE_WARNING_SYMBOL: True,
    }
    prio_by_symbol = {
        ATTENDANCE_WARNING_SYMBOL: 0,
        TICKET_BUY_SELL_WARNING_SYMBOL: 1,
        TICKET_CONFIRMATION_WARNING_SYMBOL: 2,
    }
    attended_screenings = None

    def __init__(self, screening, fan, warning):
        self.screening = screening
        self.fan = fan
        self.warning = warning
        self.festival = self.screening.film.festival

    def __str__(self):
        return f'Warning {self.warning.name} for {self.fan} in {self.screening}'

    @classmethod
    def get_fan_warnings(cls, screening, fan):
        warnings = []
        has_ticket = screening.fan_has_ticket(fan).count()
        confirmed = False
        if has_ticket:
            confirmed = screening.fan_ticket_confirmed(fan).count()
        attends = screening.fan_attends(fan).count()

        warning_type = cls.WarningType
        if attends and not has_ticket:
            warnings.append(cls(screening, fan, warning_type.NEEDS_TICKET))
        if has_ticket and not attends:
            warnings.append(cls(screening, fan, warning_type.SHOULD_SELL_TICKET))
        if attends and has_ticket and not confirmed:
            warnings.append(cls(screening, fan, warning_type.AWAITS_CONFIRMATION))

        if attends:
            # Check if screenings of the same film are attended.
            film_screenings = Screening.screenings.filter(film=screening.film)
            multiple_attends = Attendance.attendances.filter(screening__in=film_screenings, fan=fan).count() > 1
            if multiple_attends:
                warnings.append(cls(screening, fan, warning_type.ATTENDS_SAME_FILM))

            # Check if overlapping screenings are attended.
            overlaps = len(cls._get_overlapping_attended_screenings(screening, fan))
            if overlaps:
                # print(f'@@@@ Yes!')
                warnings.append(cls(screening, fan, warning_type.ATTENDS_OVERLAPPING))

            # Check if fan is available for screening.
            available = screening.available_by_fan(fan)
            if not available:
                warnings.append(cls(screening, fan, warning_type.ATTENDS_WHILE_UNAVAILABLE))

        for warning in warnings:
            yield warning

    @classmethod
    def _get_overlapping_attended_screenings(cls, screening, fan):
        if screening.id == 3870:
            pr_debug(f'start for {str(fan)}', with_time=True)
        festival = screening.film.festival
        manager = Attendance.attendances
        cls.attended_screenings = [a.screening for a in manager.filter(fan=fan, screening__film__festival=festival)]
        day_screenings = []
        for s in cls.attended_screenings:
            if s.start_dt.date() == screening.start_dt.date() and s.id != screening.id:
                day_screenings.append(s)
        result_screenings = []
        for day_screening in day_screenings:
            if day_screening.overlaps(screening):
                result_screenings.append(day_screening)
        if screening.id == 3870:
            pr_debug('done', with_time=True)
        return result_screenings

    @classmethod
    def get_warning_stats(cls, festival, warnings=None):
        pr_debug('start', with_time=True)

        # Get the warnings.
        getter = cls._get_warning_details
        warning_details = get_warning_details(warnings, getter) if warnings else get_warnings(festival, getter)

        # Calculate the statistics.
        count_by_symbol = {}
        for detail in sorted(warning_details, key=lambda d: d['prio']):
            try:
                count_by_symbol[detail['symbol']] += 1
            except KeyError:
                count_by_symbol[detail['symbol']] = 1

        # Make the statistics representable.
        stats = {
            'count': len(warning_details),
            'background': COLOR_WARNING_YELLOW,
            'color': COLOR_WARNING_RED,
            'symbols': [{'symbol': symbol, 'count': count} for symbol, count in count_by_symbol.items()],
        }

        pr_debug('done', with_time=True)
        return stats

    @classmethod
    def _get_warning_details(cls, warning):
        symbol = cls.symbol_by_warning[warning.warning]
        return {
            'symbol': symbol,
            'prio': cls.prio_by_symbol[symbol]
        }
