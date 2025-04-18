from authentication.models import FilmFan, get_sorted_fan_list
from festival_planner.cookie import Filter, Cookie
from festival_planner.debug_tools import pr_debug
from festival_planner.fragment_keeper import ScreeningFragmentKeeper
from festivals.models import current_festival
from films.models import current_fan, fan_rating_str, get_present_fans
from screenings.models import Screening, Attendance, COLOR_PAIR_SELECTED, Ticket, COLOR_WARNING_ORANGE, \
    COLOR_WARNING_YELLOW

INDEX_BY_ALERT = {}


def get_ticket_holders(screening, current_filmfan, confirmed=None):
    kwargs = {'screening': screening}
    if confirmed is not None:
        kwargs['confirmed'] = confirmed
    fan_ids = Ticket.tickets.filter(**kwargs).values_list('fan', flat=True)
    ticket_holders = FilmFan.film_fans.filter(id__in=fan_ids)
    sorted_holders = get_sorted_fan_list(current_filmfan, fan_query_set=ticket_holders)
    return sorted_holders


def get_buy_sell_confirm_alert_tuple(fan, screening):
    has_ticket = screening.fan_has_ticket(fan).count()
    confirmed = False
    if has_ticket:
        confirmed = screening.fan_ticket_confirmed(fan).count()
    attends = screening.fan_attends(fan).count()
    buy_sell_confirm_tuple = (
        attends and not has_ticket,
        has_ticket and not attends,
        attends and has_ticket and not confirmed
    )
    return buy_sell_confirm_tuple


class ScreeningStatusGetter:
    screening_cookie = Cookie('screening')
    buy_sell_confirm_tuple_index_by_alert = {
        'buy': 0,
        'sell': 1,
        'expect': 2,
    }
    template_key_by_alert = {
        'buy': 'should_buy',
        'sell': 'should_sell',
        'expect': 'awaits_confirmation',
    }
    action_by_alert = {
        'buy': 'needs a ticket',
        'sell': 'should sell',
        'expect': 'awaits confirmation'
    }
    color_by_alert = {
        'buy': COLOR_WARNING_ORANGE,
        'sell': COLOR_WARNING_ORANGE,
        'expect': COLOR_WARNING_YELLOW,
    }

    def __init__(self, session, day_screenings):
        self.session = session
        self.day_screenings = day_screenings
        self.fan = current_fan(self.session)
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
            availability_by_screening_by_fan[fan] =\
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
        ratings = [f'{fan.initial()}{fan_rating_str(fan, film_screening.film)}' for fan in attendants]
        status = self.get_screening_status(film_screening, attendants)
        attendants_props = self._get_attendants_props(film_screening, attendants)
        ticket_holders_props = self._get_ticket_holders_props(film_screening)
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
            'ratings': ', '.join(ratings),
            'q_and_a': film_screening.str_q_and_a(),
            'query_string': Filter.get_querystring(**{'day': day, 'screening': film_screening.pk}),
            'fragment': ScreeningFragmentKeeper.fragment_code(film_screening.screen.pk),
        }
        return day_props

    @classmethod
    def _get_attendants_props(cls, screening, attendants):
        return cls._get_buy_sell_fan_props(screening, attendants, ['buy'])

    def _get_ticket_holders_props(self, screening):
        ticket_holders = get_ticket_holders(screening, self.fan)
        return self._get_buy_sell_fan_props(screening, ticket_holders, ['sell', 'expect'])

    def _get_confirmed_ticket_holders_props(self, screening):
        confirmed_ticket_holders = get_ticket_holders(screening, self.fan, confirmed=True)
        return confirmed_ticket_holders

    @classmethod
    def _get_buy_sell_fan_props(cls, screening, fans, alerts):
        fan_props = []
        for fan in fans:
            tup = get_buy_sell_confirm_alert_tuple(fan, screening)
            alert_bool = False
            used_alert = None
            for alert in alerts:
                alert_bool = tup[cls.buy_sell_confirm_tuple_index_by_alert[alert]]
                if alert_bool:
                    used_alert = alert
                    break
            used_alert = used_alert or alerts[0]
            alert_key = cls.template_key_by_alert[used_alert]
            props = {
                'name': fan.name,
                alert_key: alert_bool,
                'action': alert_bool and cls.action_by_alert[used_alert],
                'color': alert_bool and cls.color_by_alert[used_alert],
                'delimiter': ', ',
            }
            fan_props.append(props)
        if fan_props:
            fan_props[-1]['delimiter'] = ''
        return fan_props
