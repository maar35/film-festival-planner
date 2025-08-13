from festival_planner.debug_tools import timed_method

FRAGMENT_INDICATOR = '#'
TOP_CORRECTION_ROWS = 2


class FragmentKeeper:
    object_tag = None
    key_field = None

    def __init__(self):
        self.object_id_by_row_nr = {}

    def __repr__(self):
        return f'{self.__class__} with key "{self.key_field}", tag "{self.object_tag}"'

    @classmethod
    def fragment_code(cls, obj):
        return f'{FRAGMENT_INDICATOR}{cls._fragment_name(cls._object_id(obj))}'

    def add_fragments(self, objects):
        for row_nr, obj in enumerate(objects):
            self.add_fragment(row_nr, obj)

    def add_fragment(self, row_nr, obj, correction_rows=TOP_CORRECTION_ROWS):
        if correction_rows:
            if row_nr >= correction_rows:
                row_nr = row_nr - correction_rows
        self.object_id_by_row_nr[row_nr] = self._object_id(obj)

    def get_fragment_name(self, row_nr):
        try:
            object_id = self.object_id_by_row_nr[row_nr]
        except KeyError:
            fragment_name = ''
        else:
            fragment_name = self._fragment_name(object_id)
        return fragment_name

    @classmethod
    def _fragment_name(cls, object_id):
        return f'{cls.object_tag}{object_id}'

    @classmethod
    def _object_id(cls, obj):
        return getattr(obj, cls.key_field)


class FilmFragmentKeeper(FragmentKeeper):
    object_tag = 'film'
    key_field = 'film_id'


class ScreenFragmentKeeper(FragmentKeeper):
    object_tag = 'screen'
    key_field = 'pk'


class ScreeningFragmentKeeper(FragmentKeeper):
    object_tag = 'screening'
    key_field = 'pk'

    @timed_method
    def add_fragment_data(self, rows):
        for row_nr, row in enumerate(rows):
            screening = row['screening']
            self.add_fragment(row_nr, screening)
        for row_nr, row in enumerate(rows):
            row['fragment_name'] = self.get_fragment_name(row_nr)
