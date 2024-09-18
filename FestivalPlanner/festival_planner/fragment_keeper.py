FRAGMENT_INDICATOR = '#'
FILM_CORRECTION_ROWS = 2
SCREENING_CORRECTION_ROWS = 2


class FragmentKeeper:
    object_tag = None

    def __init__(self, key_field):
        self.key_field = key_field
        self.object_id_by_row_nr = {}

    @classmethod
    def _fragment_name(cls, object_id):
        return f'{cls.object_tag}{object_id}'

    @classmethod
    def fragment_code(cls, object_id):
        return f'{FRAGMENT_INDICATOR}{cls._fragment_name(object_id)}'

    def add_fragments(self, objects):
        for row_nr, obj in enumerate(objects):
            self.add_fragment(row_nr, obj)

    def add_fragment(self, row_nr, obj, correction_rows=None):
        if correction_rows:
            row_nr = row_nr - correction_rows if row_nr > correction_rows else 0
        self.object_id_by_row_nr[row_nr] = getattr(obj, self.key_field)

    def get_fragment_name(self, row_nr):
        try:
            object_id = self.object_id_by_row_nr[row_nr]
        except KeyError:
            fragment_name = ''
        else:
            fragment_name = self._fragment_name(object_id)
        return fragment_name


class FilmFragmentKeeper(FragmentKeeper):
    object_tag = 'film'

    def add_fragment(self, row_nr, obj, correction_rows=None):
        super().add_fragment(row_nr, obj, correction_rows=correction_rows or FILM_CORRECTION_ROWS)


class ScreeningFragmentKeeper(FragmentKeeper):
    object_tag = 'screen'

    def add_fragment(self, row_nr, obj, correction_rows=None):
        super().add_fragment(row_nr, obj, correction_rows=correction_rows or SCREENING_CORRECTION_ROWS)
