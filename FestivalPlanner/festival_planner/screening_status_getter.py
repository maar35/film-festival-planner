from copy import deepcopy
from enum import Enum, auto

from authentication.models import FilmFan, get_sorted_fan_list
from availabilities.models import Availabilities
from festival_planner.cookie import Filter, Cookie
from festival_planner.debug_tools import profiled_method, OVERLAP_PROFILER, GET_WARNINGS_PROFILER, \
    GET_AV_KEEPER_PROFILER, WARNING_KEYS_PROFILER, FAN_WARNINGS_PROFILER, timed_method
from festival_planner.fragment_keeper import ScreenFragmentKeeper
from festivals.models import current_festival
from films.models import current_fan
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


@timed_method
@profiled_method(WARNING_KEYS_PROFILER)
def get_warnings_keys(festival):
    """
    Return a set of screening-fan tuples that could have one or more
    warnings.
    """
    attendances = Attendance.attendances.filter(screening__film__festival=festival)
    a_keys_set = {(attendance.screening, attendance.fan) for attendance in attendances}
    tickets = Ticket.tickets.filter(screening__film__festival=festival)
    t_keys_set = {(ticket.screening, ticket.fan) for ticket in tickets}
    keys_set = a_keys_set | t_keys_set
    return keys_set


@profiled_method(GET_AV_KEEPER_PROFILER)
def get_availability_keeper(keys_set):
    """
    Convert a set of screening-fan tuples into a list of screenings and
    a list of fans as input for a new Availability Keeper.
    Returns the availability keeper.
    """
    keeper = AvailabilityKeeper()
    screenings = set()
    fans = set()
    for screening, fan in keys_set:
        screenings.add(screening)
        fans.add(fan)
    keeper.set_availability(screenings, fans)
    keeper.set_ticket_status(screenings, fans)
    return keeper


@timed_method
@profiled_method(GET_WARNINGS_PROFILER)
def get_warnings(festival, details_getter, keys_set=None):
    """
    Get all warnings concerning the given festival.
    The details getter should deliver objects that will be the
    elements of the returned list.
    """
    @profiled_method(FAN_WARNINGS_PROFILER)
    def get_fan_warnings(_keys_set):
        """For profiling reasons only"""
        details = []
        for keys in _keys_set:
            for warning in ScreeningWarning.get_fan_warnings(*keys, availability_keeper=keeper):
                details.append(details_getter(warning))
        return details

    keys_set = keys_set or get_warnings_keys(festival)
    keeper = get_availability_keeper(keys_set)
    warning_details = get_fan_warnings(keys_set)
    return warning_details


@timed_method
def get_warning_details(warnings, details_getter):
    warning_details = []
    for warning in warnings:
        warning_details.append(details_getter(warning))
    return warning_details


def get_screening_warnings(screening, fans, availability_keeper, status_getter=None):
    warnings = []
    for fan in fans:
        warnings.extend(ScreeningWarning.get_fan_warnings(screening, fan, availability_keeper, status_getter))
    return warnings


def get_filmscreenings(film):
    filmscreenings = Screening.screenings.filter(film=film).order_by('start_dt')
    return filmscreenings


def get_same_film_attendances(screening, fan):
    filmscreenings = get_filmscreenings(screening.film)
    same_film_attendances = Attendance.attendances.filter(screening__in=filmscreenings, fan=fan)
    return same_film_attendances


@profiled_method(OVERLAP_PROFILER)
def get_overlapping_attended_screenings(screening, fan, first_only=True):
    festival = screening.film.festival
    manager = Attendance.attendances
    filter_kwargs = {
        'fan': fan,
        'screening__film__festival': festival,
        'screening__start_dt__date': screening.start_dt.date(),
    }
    attended_screenings = [a.screening for a in manager.filter(**filter_kwargs) if a.screening != screening]
    overlapping_screenings = []
    for day_screening in attended_screenings:
        if day_screening.overlaps(screening):
            overlapping_screenings.append(day_screening)
            if first_only:
                break
    return overlapping_screenings


class ScreeningStatusGetter:
    screening_cookie = Cookie('screening')

    def __init__(self, session, day_screenings):
        self.session = session
        self.day_screenings = day_screenings
        self.fan = current_fan(self.session)
        self.sorted_fans = get_sorted_fan_list(self.fan)
        self.attendances_by_screening = self._get_attendances_by_screening()
        self.attendance_by_screening_by_fan = self._get_attendance_by_screening_by_fan(self.attendances_by_screening)
        self.attends_by_screening = {s: self.attendance_by_screening_by_fan[s][self.fan] for s in day_screenings}
        self.has_attended_film_by_screening = self._get_has_attended_film_by_screening()
        self.keeper = self._get_availability_keeper()

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
        """Set the selected screening if requested"""
        cls.screening_cookie.handle_get_request(request)

    @classmethod
    @timed_method
    def get_filmscreening_props(cls, session, film):
        festival = current_festival(session)
        festival_screenings = Screening.screenings.filter(film__festival=festival)
        filmscreenings = get_filmscreenings(film)
        dates = filmscreenings.dates('start_dt', 'day')
        film_screenings_props = []
        for date in dates:
            day_filmscreenings = filmscreenings.filter(start_dt__date=date)
            day_screenings = festival_screenings.filter(start_dt__date=date)
            getter = cls(session, set(day_screenings) | set(day_filmscreenings))
            film_screenings_props.extend([getter._get_day_props(s) for s in day_filmscreenings])
        return film_screenings_props

    def fits_availability(self, screening):
        fits = self.keeper.get_availability(screening, self.fan)
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

    def _get_attendance_by_screening_by_fan(self, attendances_by_screening):
        attendance_by_screening_by_fan = {}
        for screening, attendances in attendances_by_screening.items():
            for fan in self.sorted_fans:
                fan_attends = fan in [attendance.fan for attendance in attendances]
                try:
                    attendance_by_screening_by_fan[screening][fan] = fan_attends
                except KeyError:
                    attendance_by_screening_by_fan[screening] = {fan: fan_attends}
        return attendance_by_screening_by_fan

    def _get_has_attended_film_by_screening(self):
        manager = Attendance.attendances
        return {s: manager.filter(screening__film=s.film, fan=self.fan).exists() for s in self.day_screenings}

    def _has_attended_film(self, screening):
        """ Returns whether the current fan attends another screening of the same film. """
        current_fan_attends_other_filmscreening = self.has_attended_film_by_screening[screening]
        return current_fan_attends_other_filmscreening

    def _get_availability_keeper(self):
        keeper = AvailabilityKeeper()
        keeper.set_availability(self.day_screenings, self.sorted_fans)
        keeper.set_ticket_status(self.day_screenings, self.sorted_fans)
        return keeper

    def _available_fans(self, screening):
        available_fan_ids = []
        for fan, available_by_screening in self.keeper.available_by_screening_by_fan.items():
            if screening in available_by_screening and available_by_screening[screening]:
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
        warnings = get_screening_warnings(film_screening, self.sorted_fans, self.keeper)
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


class AvailabilityKeeper:
    """
    Keeps availability of fans for screenings.
    """
    def __init__(self):
        self.available_by_screening_by_fan = {}
        self.ticket_by_screening_by_fan = {}

    def set_availability(self, screenings, fans):
        manager = Availabilities.availabilities
        for screening in screenings:
            self.available_by_screening_by_fan[screening] = {}
            kwargs = {
                'start_dt__lte': screening.start_dt,
                'end_dt__gte': screening.end_dt,
                'fan__in': fans,
            }
            availabilities = manager.filter(**kwargs)
            available_fans = [availability.fan for availability in availabilities]
            for fan in available_fans:
                self.available_by_screening_by_fan[screening][fan] = True

    def set_ticket_status(self, screenings, fans):
        manager = Ticket.tickets

        tickets = manager.filter(screening__in=screenings, fan__in=fans)
        for ticket in tickets:
            screening = ticket.screening
            fan = ticket.fan
            try:
                self.ticket_by_screening_by_fan[screening][fan] = ticket
            except KeyError as e:
                self.ticket_by_screening_by_fan[screening] = {fan: ticket}

    def get_availability(self, screening, fan):
        try:
            available = self.available_by_screening_by_fan[screening][fan]
        except KeyError as e:
            available = False
        return available

    def get_ticket(self, screening, fan):
        try:
            ticket = self.ticket_by_screening_by_fan[screening][fan]
        except KeyError:
            ticket = None
        return ticket


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

    fix_by_warning = {
        WarningType.NEEDS_TICKET: 'Buy ticket',
        WarningType.AWAITS_CONFIRMATION: 'Confirm',
        WarningType.SHOULD_SELL_TICKET: 'Sell ticket',
        WarningType.ATTENDS_SAME_FILM: 'Unattend',
        WarningType.ATTENDS_OVERLAPPING: 'Unattend',
        WarningType.ATTENDS_WHILE_UNAVAILABLE: 'Unattend',
    }

    all_of_screening_wording_by_ticket_warning = {
        WarningType.NEEDS_TICKET: 'for all attendants',
        WarningType.AWAITS_CONFIRMATION: 'for all attendants',
        WarningType.SHOULD_SELL_TICKET: 'for unattending fans',
    }

    all_of_fan_wording_by_ticket_warning = {
        WarningType.NEEDS_TICKET: 'for all screenings of',
        WarningType.AWAITS_CONFIRMATION: 'all tickets for',
        WarningType.SHOULD_SELL_TICKET: 'for all unattended screenings of',
    }
    link_wording_by_ticket_warning = {
        WarningType.ATTENDS_SAME_FILM: 'filmscreenings',
        WarningType.ATTENDS_OVERLAPPING: 'overlapping screenings',
    }

    fix_verb_by_warning = {
        WarningType.NEEDS_TICKET: 'created',
        WarningType.AWAITS_CONFIRMATION: 'confirmed',
        WarningType.SHOULD_SELL_TICKET: 'deleted',
        WarningType.ATTENDS_SAME_FILM: 'deleted',
        WarningType.ATTENDS_OVERLAPPING: 'deleted',
        WarningType.ATTENDS_WHILE_UNAVAILABLE: 'deleted',
    }

    fix_noun_by_warning = {
        WarningType.NEEDS_TICKET: 'ticket',
        WarningType.AWAITS_CONFIRMATION: 'ticket',
        WarningType.SHOULD_SELL_TICKET: 'ticket',
        WarningType.ATTENDS_SAME_FILM: 'attendance',
        WarningType.ATTENDS_OVERLAPPING: 'attendance',
        WarningType.ATTENDS_WHILE_UNAVAILABLE: 'attendance',
    }

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

    def __init__(self, screening, fan, warning):
        self.screening = screening
        self.fan = fan
        self.warning = warning
        self.festival = self.screening.film.festival

    def __str__(self):
        return f'Warning {self.warning.name} for {self.fan} in {self.screening}'

    @classmethod
    def get_fan_warnings(cls, screening, fan, availability_keeper, status_getter=None):
        # Get tickets status.
        ticket = availability_keeper.get_ticket(screening, fan)
        has_ticket = ticket is not None
        confirmed = ticket.confirmed if ticket else False

        # Get attendance status.
        attends = status_getter.attendance_by_screening_by_fan[screening][fan] \
            if status_getter else screening.fan_attends(fan).count()

        # Get warnings concerning tickets.
        warnings = []
        warning_type = cls.WarningType
        if attends and not has_ticket:
            warnings.append(cls(screening, fan, warning_type.NEEDS_TICKET))
        if has_ticket and not attends:
            warnings.append(cls(screening, fan, warning_type.SHOULD_SELL_TICKET))
        if attends and has_ticket and not confirmed:
            warnings.append(cls(screening, fan, warning_type.AWAITS_CONFIRMATION))

        if attends:
            # Check if screenings of the same film are attended.
            attends_same_film = cls._get_attends_same_film(screening, fan)
            if attends_same_film:
                warnings.append(cls(screening, fan, warning_type.ATTENDS_SAME_FILM))

            # Check if overlapping screenings are attended.
            overlaps = get_overlapping_attended_screenings(screening, fan)
            if overlaps:
                warnings.append(cls(screening, fan, warning_type.ATTENDS_OVERLAPPING))

            # Check if fan is available for screening.
            available = availability_keeper.get_availability(screening, fan)
            if not available:
                warnings.append(cls(screening, fan, warning_type.ATTENDS_WHILE_UNAVAILABLE))

        for warning in warnings:
            yield warning

    @classmethod
    @timed_method
    def get_warning_stats(cls, festival, warnings=None):
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

        return stats

    @classmethod
    def _get_attends_same_film(cls, screening, fan):
        same_film_attendances = get_same_film_attendances(screening, fan)
        return same_film_attendances.count() > 1

    @classmethod
    def _get_warning_details(cls, warning):
        symbol = cls.symbol_by_warning[warning.warning]
        return {
            'symbol': symbol,
            'prio': cls.prio_by_symbol[symbol]
        }
