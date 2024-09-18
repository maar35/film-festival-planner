class Cookie:
    """
    Support basic operations on same-keyed cookies.
    """
    def __init__(self, cookie_key, initial_value=None):
        self._cookie_key = cookie_key
        self._initial_value = initial_value

    def _set_value_from_session(self, session):
        """
        Link the cookie to a session.
        """
        self.set(session, session.get(self._cookie_key, self._initial_value))

    def get_cookie_key(self):
        return self._cookie_key

    def handle_get_request(self, request):
        """
        Find cookie in a GET request and update its value accordingly.
        """
        if self._cookie_key in request.GET:
            query_value = request.GET[self._cookie_key]
            self.set(request.session, query_value)

    def get(self, session, default=None):
        """
        Return the cookie value from the session or default if it doesn't exist.
        """
        self._set_value_from_session(session)
        value = session.get(self._cookie_key, default)
        return value

    def set(self, session, value):
        session[self._cookie_key] = value

    def remove(self, session):
        if self._cookie_key in session:
            del session[self._cookie_key]


class Filter(Cookie):
    """
    Provide filtering data on a "on/off" basis.
    """
    filtered_by_query = {'display': False, 'hide': True}
    query_by_filtered = {filtered: query for query, filtered in filtered_by_query.items()}

    def __init__(self, action_subject, cookie_key=None, filtered=False, action_true=None, action_false=None):
        super().__init__(cookie_key or action_subject.strip().replace(' ', '-'), initial_value=filtered)
        action_true = action_true or f'Display {action_subject}'
        action_false = action_false or f'Hide {action_subject}'
        self._action_by_filtered = {True: action_true, False: action_false}

    def handle_get_request(self, request):
        """
        Find cookie in a GET request and update its filter on/off value accordingly.
        """
        if self._cookie_key in request.GET:
            query_key = request.GET[self._cookie_key]
            filtered = self.filtered_by_query[query_key]
            self.set(request.session, filtered)

    @staticmethod
    def get_querystring(**kwargs):
        query_list = [f'{key}={value}' for key, value in kwargs.items()]
        return '?' + '&'.join(query_list) if query_list else ''

    def get_href_filter(self, session, first=True):
        """
        Shortcut filter query as to use in template variable.
        """
        return f'{"?" if first else "&"}{self.get_cookie_key()}={self.next_query(session)}'

    @classmethod
    def get_display_query_from_keys(cls, filter_keys):
        kwargs = {key: cls.query_by_filtered[False] for key in filter_keys}
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

