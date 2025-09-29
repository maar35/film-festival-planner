import copy
import datetime

from festival_planner.debug_tools import pr_debug, timed_method
from festival_planner.tools import get_submit_name
from festivals.models import current_festival
from films.models import rating_str

EXPIRY_HOURS = 24 * 7
MAX_CACHES = 10

FILM_SUBMIT_PREFIX = 'list_'


def get_film_list_submit_name(film, rating_value):
    return get_submit_name(FILM_SUBMIT_PREFIX, film.id, rating_value)


class FilmRatingCache:
    caches_count = 0
    cache_by_key = {}
    FILTER_SEPARATOR = ':'
    KEY_VALUE_SEPARATOR = '_'
    FESTIVAL_FILTER_INDEX = 0
    NO_FILTERS = {}

    def __init__(self, session, errors):
        self.initialize_filters(session)
        self.errors = errors

    def invalidate(self, cache_key):
        pr_debug(f'delete cache key with {cache_key.split(":")[0]}')
        del self.cache_by_key[cache_key]

    def is_valid(self, session):
        cache_key = self.get_cache_key(session)
        if cache_key in self.cache_by_key and self.cache_by_key[cache_key]:
            return True
        return False

    def festival_cache_keys(self, festival):
        index = self.FESTIVAL_FILTER_INDEX
        sep = self.FILTER_SEPARATOR
        return [key for key in self.cache_by_key if key.split(sep)[index] == str(festival)]

    @classmethod
    def get_active_filter_keys(cls, session):
        # Get the current cache key from the session.
        cache_key = cls.get_cache_key(session)

        # Split the cache key into the underlying filters.
        filters = cache_key.split(cls.FILTER_SEPARATOR)

        # Remove the festival filter.
        index = cls.FESTIVAL_FILTER_INDEX
        filters.remove(filters[index])

        # Isolate the keys of active filters.
        key_value_list = [f.split(cls.KEY_VALUE_SEPARATOR) for f in filters]
        active_filter_keys = [key for [key, on] in key_value_list if int(on)]

        return active_filter_keys

    def get_film_rows(self, session):
        cache_key = self.get_cache_key(session)
        try:
            cache_data = self.cache_by_key[cache_key]
        except KeyError as e:
            self.errors.append(f'{e} getting film rows')
            return []
        return cache_data.get_film_rows()

    @timed_method
    def set_film_rows(self, session, film_rows):
        cache_key = self.get_cache_key(session)
        cache_data = FilmRatingCacheData(film_rows)
        self.cache_by_key[cache_key] = cache_data
        self.check_invalidate_caches()
        pr_debug(f'{len(self.get_film_rows(session))} records', with_time=True)

    def update_festival_caches(self, session, film, fan, rating_value):
        festival = current_festival(session)
        invalid_cache_keys = self.festival_cache_keys(festival)
        for invalid_cache_key in invalid_cache_keys:
            self.update(invalid_cache_key, film, fan, rating_value)

    @timed_method
    def update(self, cache_key, film, fan, rating_value):
        film_rows = self.cache_by_key[cache_key].get_film_rows()

        # Filter out film data.
        try:
            film_row = [row for row in film_rows if row['film'].id == film.id][0]
        except (TypeError, IndexError) as e:
            pr_debug(f'{e} getting film row for {film=}')
            self.errors.append(f'{e} getting film row for {film=}')
        else:
            # Filter out fan data.
            try:
                fan_data = [r for r in film_row['fan_ratings'] if r['fan'] == fan][0]
            except IndexError as e:
                pr_debug(f'{IndexError.__name__} getting rating for {fan=}')
                self.errors.append(f'{e} getting rating for {fan=}')
            else:
                fan_data['rating_str'] = rating_str(rating_value)
                old_choice = [c for c in fan_data['choices'] if c['disabled']][0]
                old_choice['disabled'] = False
                submit_name = get_film_list_submit_name(film, rating_value)
                new_choice = [c for c in fan_data['choices'] if c['submit_name'] == submit_name][0]
                new_choice['disabled'] = True

    @timed_method
    def check_invalidate_caches(self):
        pr_debug(f'{len(self.cache_by_key)} caches', with_time=True)

        # Delete expired caches
        invalid_cache_keys = [k for k, c in self.cache_by_key.items() if c.expire_date < datetime.datetime.now()]
        for cache_key in invalid_cache_keys:
            self.invalidate(cache_key)

        # Delete the oldest caches until cache count is not above max.
        if len(self.cache_by_key) > MAX_CACHES:
            items = sorted(self.cache_by_key.items(), key=lambda i: i[1].expire_date, reverse=True)
            old_cache_items = items[MAX_CACHES:]
            for cache_key, cache_data in old_cache_items:
                self.invalidate(cache_key)

        pr_debug(f'{len(self.cache_by_key)} caches', with_time=True)

    def invalidate_festival_caches(self, festival):
        invalid_cache_keys = self.festival_cache_keys(festival)
        for invalid_cache_key in invalid_cache_keys:
            self.invalidate(invalid_cache_key)

    @classmethod
    def get_cache_key(cls, session):
        return f'{current_festival(session)}:{cls.get_filters_key(session)}'

    @staticmethod
    def initialize_filters(session):
        session['filters'] = FilmRatingCache.NO_FILTERS

    @staticmethod
    def set_filters(session, filter_dict):
        session['filters'] = {k: 1 if v else 0 for k, v in filter_dict.items()}

    @classmethod
    def get_filters_key(cls, session):
        filter_dict = session.get('filters') or {}
        filter_keys = [f'{k}{cls.KEY_VALUE_SEPARATOR}{v}' for k, v in filter_dict.items()]
        return cls.FILTER_SEPARATOR.join(filter_keys) if filter_keys else ''


class FilmRatingCacheData:
    expiry_timedelta = datetime.timedelta(hours=EXPIRY_HOURS)

    def __init__(self, film_rows):
        self.film_rows = copy.deepcopy(film_rows)
        self.expire_date = self.new_expire_date()

    def __str__(self):
        return f'Film rating cash, {len(self.film_rows)} rows, expires {self.expire_date:%Y-%m-%d %H:%M}'

    def new_expire_date(self):
        return datetime.datetime.now() + self.expiry_timedelta

    def reset_expire_date(self):
        self.expire_date = self.new_expire_date()

    def get_film_rows(self):
        self.reset_expire_date()
        return self.film_rows

