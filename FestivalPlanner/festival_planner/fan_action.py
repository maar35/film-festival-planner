import copy
import datetime

from festival_planner.cookie import Cookie
from festivals.models import current_festival
from films.models import current_fan, get_rating_name


class BaseAction:
    def __init__(self, action_key, known_keys, initial_value=None):
        self.action_key = action_key
        self.action_cookie = None
        self.known_keys = {'fan', 'action_time'} | known_keys
        self.initial_value = initial_value

    def init_action(self, session, **kwargs):
        """
        Initialize the action cookie now a session can be supplied.
        """
        # Set the cookie.
        cookie_key = self._get_cookie_key_from_session(session)
        self.action_cookie = Cookie(cookie_key, initial_value=self.initial_value)

        # Check keyword arguments.
        unknown_keys = [key for key in kwargs.keys() if key not in self.known_keys]
        if unknown_keys:
            raise ValueError(f'Unknown kwargs key(s) {",".join(unknown_keys)}')

        # Initialize the action dictionary.
        now = datetime.datetime.now()
        action = {
            'fan': str(current_fan(session)),
            'action_time': now.isoformat(),     # Store the current time as a string in the cookie.
        }

        # Merge the keyword arguments with the existing action dictionary.
        action |= kwargs

        # Store the action dictionary as cookie.
        self.action_cookie.set(session, copy.deepcopy(action))

    def update(self, **kwargs):
        action = self.action_cookie.get()
        action |= kwargs
        self.action_cookie.set(action)

    def add_detail(self, session, line):
        action = self.action_cookie.get(session)
        action['updates'].append(line)
        self.action_cookie.set(session, action)

    def get_refreshed_action(self, session):
        # Make sure the cookie is based on the current festival.
        cookie_key = self._get_cookie_key_from_session(session)
        if not self.action_cookie or self.action_cookie.get_cookie_key() != cookie_key:
            self.action_cookie = Cookie(cookie_key, initial_value=self.initial_value)
            if self.action_cookie.get_cookie_key() not in session:
                BaseAction.init_action(self, session)

        # Recover the time variable from the stored string representation if necessary.
        if self.action_cookie.get(session):
            action = copy.deepcopy(self.action_cookie.get(session))
            action['action_time'] = datetime.datetime.fromisoformat(action['action_time'])
        else:
            action = None
        return action

    def _get_cookie_key_from_session(self, session):
        festival = current_festival(session)
        return f'action_{self.action_key}_{festival.id}'


class FanAction(BaseAction):
    known_keys = {'screening_str', 'screening_id', 'updates'}

    def __init__(self, action_key):
        super().__init__(action_key, self.known_keys, initial_value={})

    def init_action(self, session, **kwargs):
        # Initialize the action dictionary.
        screening = kwargs.get('screening')
        action = {
            'screening_str': str(screening),
            'screening_id': screening.id,
            'updates': [],
        }

        # Merge with the standard action items.
        super().init_action(session, **action)


class FixWarningAction(BaseAction):
    known_keys = {'header', 'updates'}

    def __init__(self, action_key):
        super().__init__(action_key, self.known_keys, initial_value={})

    def init_action(self, session, **kwargs):
        # Initialize the action dictionary.
        header = kwargs.get('header')
        action = {
            'header': header,
            'updates': [],
        }

        # Merge with the standard action dictionary.
        super().init_action(session, **action)


class RatingAction(BaseAction):
    known_keys = {'rating_type', 'old_rating', 'new_rating', 'new_rating_name', 'rated_film', 'rated_film_id'}

    def __init__(self, action_key):
        super().__init__(action_key, self.known_keys, initial_value={})

    def init_action(self, session, **kwargs):
        # Initialize the action dictionary.
        field = kwargs.get('field')
        new_rating = kwargs.get('new_rating')
        new_rating_value = getattr(new_rating, field)
        new_rating_name = get_rating_name(new_rating_value)
        rating_action = {
            'rating_type': field,
            'old_rating': kwargs.get('old_rating_str'),
            'new_rating': str(new_rating_value),
            'new_rating_name': new_rating_name,
            'rated_film': str(new_rating.film),
            'rated_film_id': new_rating.film.id,
        }

        # Merge with the standard action items.
        super().init_action(session, **rating_action)

