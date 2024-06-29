
class Cookie:
    def __init__(self, cookie_key, initial_value=None):
        self._cookie_key = cookie_key
        self._initial_value = initial_value

    def init_cookie(self, session):
        self.set(session, self.get(session, self._initial_value))

    def get_cookie_key(self):
        return self._cookie_key

    def handle_request(self, request, default=None):
        if self._cookie_key in request.GET:
            query_value = request.GET[self._cookie_key]
            self.set(request.session, query_value)
        elif default:
            self.set(request.session, default)

    def set(self, session, value):
        """
        Initialize cookie.
        """
        session[self._cookie_key] = value

    def get(self, session, default=None):
        """
        Get the cookie from the session or default if it doesn't exist.
        """
        value = session.get(self._cookie_key, default)
        return value

    def remove_cookie(self, session):
        """
        Remove cookie.
        """
        if self._cookie_key in session:
            del session[self._cookie_key]


class Filter(Cookie):
    filtered_by_query = {'display': False, 'hide': True}
    query_by_filtered = {filtered: query for query, filtered in filtered_by_query.items()}

    def __init__(self, action_subject, cookie_key=None, filtered=False, action_true=None, action_false=None):
        super().__init__(cookie_key or action_subject.strip().replace(' ', '-'), initial_value=filtered)
        action_true = action_true or f'Display {action_subject}'
        action_false = action_false or f'Hide {action_subject}'
        self._action_by_filtered = {True: action_true, False: action_false}

    def handle_request(self, request):
        if self._cookie_key in request.GET:
            query_key = request.GET[self._cookie_key]
            filtered = self.filtered_by_query[query_key]
            self.set(request.session, filtered)

    def get_href_filter(self, session):
        return f'?{self.get_cookie_key()}={self.next_query(session)}'

    def on(self, session, default=None):
        return self.get(session, default)

    def off(self, session, default=None):
        return not self.on(session, default)

    def next_query(self, session):
        return self.query_by_filtered[self.off(session)]

    def action(self, session):
        return self._action_by_filtered[self.on(session)]

