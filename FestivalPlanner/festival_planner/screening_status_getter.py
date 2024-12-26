from festival_planner.cookie import Filter, Cookie
from festival_planner.debug_tools import pr_debug
from festival_planner.fragment_keeper import ScreeningFragmentKeeper
from festivals.models import current_festival
from films.models import current_fan, fan_rating_str, get_present_fans
from screenings.models import Screening, Attendance, COLOR_PAIR_SELECTED


class ScreeningStatusGetter:
    screening_cookie = Cookie('screening')

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
        if current_fan(self.session) in attendants:
            status = Screening.ScreeningStatus.ATTENDS
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
        selected_screening = Screening.screenings.get(pk=screening_pk) if screening_pk else None
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
        attendants = [attendance.fan for attendance in attendances]
        return attendants

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
        available_fans = []
        for fan, available_by_screening in self.available_by_screening_by_fan.items():
            if available_by_screening[screening]:
                available_fans.append(fan)
        return available_fans

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
        available_fans = self._available_fans(film_screening)
        day = film_screening.start_dt.date().isoformat()
        day_props = {
            'film_screening': film_screening,
            'status': status,
            'day': day,
            'pair_selected': COLOR_PAIR_SELECTED,
            'pair': Screening.color_pair_by_screening_status[status],
            'attendants': ', '.join([attendant.name for attendant in attendants]),
            'available_fans': ', '.join([fan.name for fan in available_fans]),
            'ratings': ', '.join(ratings),
            'q_and_a': film_screening.str_q_and_a(),
            'query_string': Filter.get_querystring(**{'day': day, 'screening': film_screening.pk}),
            'fragment': ScreeningFragmentKeeper.fragment_code(film_screening.screen.pk),
        }
        return day_props
