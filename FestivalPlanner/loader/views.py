import os
from operator import attrgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, ListView

from authentication.models import FilmFan
from festival_planner.cookie import Cookie
from festival_planner.shared_template_referrer_view import SharedTemplateReferrerView
from festival_planner.tools import add_base_context, get_log, unset_log, initialize_log, wrap_up_form_errors
from festivals.models import Festival, switch_festival, current_festival, FestivalBase
from films.models import Film, FilmFanFilmRating
from loader.forms.loader_forms import SectionLoader, SubsectionLoader, RatingLoaderForm, TheaterDataLoaderForm, \
    TheaterDataDumperForm, CityLoader, TheaterLoader, ScreenLoader, TheaterDataUpdateForm, RatingDataBackupForm, \
    FILM_FANS_BACKUP_PATH, RATINGS_BACKUP_PATH, FILMS_BACKUP_PATH, \
    FESTIVALS_BACKUP_PATH, FESTIVAL_BASES_BACKUP_PATH, BACKUP_DATA_DIR, CITIES_BACKUP_PATH, \
    ScreeningLoader, AttendanceLoader, AttendanceDumper, RatingDumper, SingleTableDumperForm, TicketLoader, TicketDumper
from screenings.forms.screening_forms import DummyForm
from screenings.models import Screening, Attendance, Ticket
from sections.models import Section, Subsection
from theaters.models import Theater, City, cities_path, theaters_path, screens_path, Screen, new_screens_path, \
    new_cities_path, new_theaters_path


def file_record_count(path, has_header=False):
    try:
        with open(path, newline='') as f:
            record_count = len(f.readlines())
        if has_header:
            record_count -= 1
    except FileNotFoundError:
        record_count = 0
    return record_count


def get_festival_row(festival):
    festival_row = {
        'festival': festival,
        'id': festival.id,
        'section_count_on_file': file_record_count(festival.sections_file()),
        'section_count': Section.sections.filter(festival=festival).count,
        'subsection_count_on_file': file_record_count(festival.subsections_file()),
        'subsection_count': Subsection.subsections.filter(section__festival=festival).count,
    }
    return festival_row


class TheaterDataInterfaceView(LoginRequiredMixin, FormView):
    model = Theater
    template_name = 'loader/theaters.html'
    form_class = None
    http_method_names = ['get', 'post']
    form_class_by_action = {'load': TheaterDataLoaderForm, 'dump': TheaterDataDumperForm}
    action_cookie = Cookie('action')

    def dispatch(self, request, *args, **kwargs):
        self.action_cookie.handle_get_request(request)
        action = self.action_cookie.get(request.session)
        self.form_class = self.form_class_by_action[action]
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        session = self.request.session
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        action = self.action_cookie.get(session)
        context['title'] = f'{action} Theater Data'
        context['action'] = action
        context['theater_items'] = self._get_theater_items()
        context['log'] = get_log(session)
        unset_log(session)
        return context

    def form_valid(self, form):
        session = self.request.session
        action = self.action_cookie.get(session)
        self.action_cookie.remove(session)
        if action == 'dump':
            form.dump_theater_data(session)
        elif action == 'load':
            form.load_theater_data(session)
        return HttpResponseRedirect('/theaters/theaters')

    @staticmethod
    def _get_theater_items():
        theater_items = {
            'city_count': City.cities.count,
            'city_count_on_file': file_record_count(cities_path()),
            'theater_count': Theater.theaters.count,
            'theater_count_on_file': file_record_count(theaters_path()),
            'screen_count': Screen.screens.count,
            'screen_count_on_file': file_record_count(screens_path()),
        }
        return theater_items


class NewTheaterDataListView(ListView):
    """
    Class-based view to merge new theater data into the corresponding tables.
    """
    template_name = 'loader/new_screens.html'
    http_method_names = ['get']
    object_list = None
    queryset = None
    context_object_name = 'new_screen_items'
    color_by_exists = {True: 'silver', False: 'MediumSpringGreen'}

    def get_queryset(self):
        session = self.request.session
        if NewTheaterDataView.state_nr == 0:
            initialize_log(session)
        NewTheaterDataView.reset_new_theater_data()
        new_cities = NewTheaterDataView.new_cities
        new_theaters = NewTheaterDataView.new_theaters
        new_screens = NewTheaterDataView.new_screens

        # Load new theater data.
        _ = CityLoader(session, file=new_cities_path()).load_new_objects(new_cities)
        _ = TheaterLoader(session, file=new_theaters_path()).load_new_objects(new_theaters, foreign_objects=new_cities)
        _ = ScreenLoader(session, file=new_screens_path()).load_new_objects(new_screens, foreign_objects=new_theaters)

        # Create the new screen items list.
        new_screen_items = [self.get_new_screen_item(screen) for screen in new_screens]

        return sorted(
            new_screen_items,
            key=lambda new_screen_item: (new_screen_item['theater'], new_screen_item['screen_abbr'])
        )

    def get_context_data(self, *args, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Merge New Screens'
        context['log'] = get_log(self.request.session)
        context['objects_label'] = NewTheaterDataView.current_objects_label()
        return context

    def get_new_screen_item(self, screen):
        theater_kwargs = {'city_id': screen.theater.city.id, 'abbreviation': screen.theater.abbreviation}

        new_screen_item = {
            'city': screen.theater.city.name,
            'city_color': self.color(City, City.cities, **{'country': 'nl', 'name': screen.theater.city.name}),
            'theater': screen.theater.parse_name,
            'theater_abbr': screen.theater.abbreviation,
            'theater_color': self.color(Theater, Theater.theaters, **theater_kwargs),
            'screen': screen.parse_name,
            'screen_abbr': screen.abbreviation,
            'address_type': screen.address_type.label,
            'screen_color': self.color(Screen, Screen.screens, **{'parse_name': screen.parse_name}),
        }
        return new_screen_item

    def color(self, cls, manager, **kwargs):
        exists = True
        try:
            _ = manager.get(**kwargs)
        except cls.DoesNotExist:
            exists = False
        color = self.color_by_exists[exists]
        return color


class NewTheaterDataFormView(FormView):
    template_name = 'loader/new_screens.html'
    form_class = TheaterDataUpdateForm
    http_method_names = ['post']

    def post(self, request, *args, **kwargs):
        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        session = self.request.session

        # Handle all entities separate, to avoid "save() prohibited to
        # prevent data loss due to unsaved related object" error.
        objects_label = NewTheaterDataView.current_objects_label()
        if objects_label == 'cities':
            form.add_new_cities(session, NewTheaterDataView.new_cities)
            NewTheaterDataView.next_objects_label()
        elif objects_label == 'theaters':
            form.add_new_theaters(session, NewTheaterDataView.new_theaters)
            NewTheaterDataView.next_objects_label()
        elif objects_label == 'screens':
            form.add_new_screens(session, NewTheaterDataView.new_screens)
            NewTheaterDataView.state_nr = 0
        else:
            raise ValueError(f'Unexpected state value: {objects_label}')
        return super().form_valid(form)

    def get_success_url(self):
        if NewTheaterDataView.state_nr:
            url = reverse('loader:new_screens')
        else:
            url = reverse('theaters:theaters')
        return url


class NewTheaterDataView(LoginRequiredMixin, View):
    new_cities = []
    new_theaters = []
    new_screens = []
    new_objects_by_label = {
        'cities': new_cities,
        'theaters': new_theaters,
        'screens': new_screens,
    }
    states = [k for k in new_objects_by_label.keys()]
    state_nr = 0

    @classmethod
    def current_objects_label(cls):
        return cls.states[cls.state_nr]

    @classmethod
    def next_objects_label(cls):
        cls.state_nr += 1

    @classmethod
    def reset_new_theater_data(cls):
        cls.new_cities = []
        cls.new_theaters = []
        cls.new_screens = []

    @staticmethod
    def get(request, *args, **kwargs):
        view = NewTheaterDataListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = NewTheaterDataFormView.as_view()
        return view(request, *args, **kwargs)


class SectionsLoaderView(LoginRequiredMixin, ListView):
    """
    Class-based view to load program sections of a specific festival.
    """
    template_name = 'loader/sections.html'
    http_method_names = ['get', 'post']
    object_list = None
    queryset = None
    context_object_name = 'festival_rows'
    unexpected_error = ''

    def get_queryset(self):
        festivals = Festival.festivals.order_by('-start_date')
        object_rows = [get_festival_row(festival) for festival in festivals]
        return object_rows

    def get_context_data(self, **kwargs):
        self.object_list = self.get_queryset()
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Program Sections Loader'
        context['unexpected_error'] = self.unexpected_error
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            picked_festival = None
            self.object_list = self.get_queryset()
            names = [(f'{row["id"]}', row['festival']) for row in self.object_list]
            for name, festival in names:
                if name in request.POST:
                    picked_festival = festival
                    break
            if picked_festival is not None:
                session = request.session
                switch_festival(session, picked_festival)
                initialize_log(session)
                if SectionLoader(session, picked_festival).load_objects():
                    SubsectionLoader(session, picked_festival).load_objects()
                return HttpResponseRedirect(reverse('sections:index'))
            else:
                self.unexpected_error = f'Submit name not found in POST ({request.POST}'

        return render(request, 'loader/sections.html', self.get_context_data())


class FilmDataBackupView(LoginRequiredMixin, FormView):
    """
    Class-based view to back up the data associated with the film models.
    """
    template_name = 'loader/film_backup.html'
    form_class = RatingDataBackupForm
    http_method_names = ['get', 'post']
    success_url = '/films/films'
    unexpected_error = ''

    def get_context_data(self, *args, **kwargs):
        super_context = super().get_context_data(**kwargs)
        new_context = {
            'title': 'Back Up Rating Data',
            'log': get_log(self.request.session),
            'fan_count': FilmFan.film_fans.count(),
            'fans_file': FILM_FANS_BACKUP_PATH,
            'rating_count': FilmFanFilmRating.film_ratings.count(),
            'ratings_file': RATINGS_BACKUP_PATH,
            'film_count': Film.films.count(),
            'films_file': FILMS_BACKUP_PATH,
            'festival_count': Festival.festivals.count(),
            'festivals_file': FESTIVALS_BACKUP_PATH,
            'festival_base_count': FestivalBase.festival_bases.count(),
            'festival_bases_file': FESTIVAL_BASES_BACKUP_PATH,
            'city_count': City.cities.count(),
            'cities_file': CITIES_BACKUP_PATH,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    def form_valid(self, form):
        session = self.request.session

        # Make sure that the backup directory exists.
        backup_dir = BACKUP_DATA_DIR
        if not os.path.isdir(backup_dir):
            os.mkdir(backup_dir)

        # Make backups of all relevant tables.
        form.backup_film_data(session)

        return super().form_valid(form)


class RatingsLoaderView(LoginRequiredMixin, ListView):
    """
    Class-based view to load film ratings of a specific festival.
    """
    template_name = 'loader/ratings.html'
    http_method_names = ['get', 'post']
    context_object_name = 'festival_items'
    object_list = None
    unexpected_error = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submit_name_prefix = 'ratings_'

    def get_queryset(self):
        festival_list = sorted(Festival.festivals.all(), key=attrgetter('start_date'), reverse=True)
        festival_rows = [self._get_festival_row(festival) for festival in festival_list]
        return festival_rows

    def get_context_data(self, **kwargs):
        self.object_list = self.get_queryset()
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Load Films and Ratings'
        context['unexpected_error'] = self.unexpected_error
        context['form'] = RatingLoaderForm()
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            festival_indicator = None
            object_list = self.get_queryset()
            names = [f'{self.submit_name_prefix}{row["str"].id}' for row in object_list]
            for name in names:
                if name in request.POST:
                    festival_indicator = name
                    break
            form = RatingLoaderForm(request.POST)
            if form.is_valid():
                if festival_indicator is not None:
                    import_mode = form.cleaned_data['import_mode']
                    festival_id = int(festival_indicator.strip(self.submit_name_prefix))
                    festival = Festival.festivals.get(pk=festival_id)
                    session = request.session
                    switch_festival(session, festival)
                    rating_cachefile = festival.ratings_cache()
                    rating_queryset = self._ratings_queryset(festival)
                    form.load_rating_data(session, festival, rating_queryset, rating_cachefile, import_mode=import_mode)
                    return HttpResponseRedirect(reverse('films:films'))
                else:
                    self.unexpected_error = "Can't identify submit widget."

        return render(request, 'loader/ratings.html', self.get_context_data())

    def _get_festival_row(self, festival):
        festival_row = {
            'str': festival,
            'submit_name': f'{self.submit_name_prefix}{festival.id}',
            'color': festival.festival_color,
            'film_count_on_file': file_record_count(festival.films_file(), has_header=True),
            'film_count': Film.films.filter(festival=festival).count,
            'rating_count_on_file': file_record_count(festival.ratings_file(), has_header=True),
            'rating_count': self._ratings_queryset(festival).count,
        }
        return festival_row

    @staticmethod
    def _ratings_queryset(festival):
        ratings_queryset = FilmFanFilmRating.film_ratings.filter(film__festival=festival)
        return ratings_queryset


class BaseListActionListView(LoginRequiredMixin, ListView):
    http_method_names = ['get']
    context_object_name = 'festival_rows'
    template_name = None
    object_list = None
    loader_class = None
    load_file = None
    manager = None
    title = None
    list_name = None
    festival_filter = None
    alternative_headers = None

    def get_queryset(self):
        festivals = Festival.festivals.order_by('-start_date')
        festival_rows = [self._get_festival_row(festival) for festival in festivals]
        return festival_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        session = self.request.session
        super_context = super().get_context_data(object_list=object_list, **kwargs)
        new_context = {
            'title': self.title,
            'list_name': self.list_name,
            'unexpected_error': ScreeningsLoaderView.unexpected_error,
            'log': get_log(session),
        }
        context = add_base_context(self.request, super_context | new_context)
        unset_log(session)
        return context

    def _get_festival_row(self, festival):
        path = getattr(festival, self.load_file)()
        festival_kwargs = {self.festival_filter: festival}
        festival_row = {
            'festival': festival,
            'field_props': self._get_field_props(path),
            'data_count_on_file': file_record_count(path, has_header=True),
            'data_count': self.manager.filter(**festival_kwargs).count,
        }
        return festival_row

    def _get_field_props(self, path):
        loadable = False
        comments = []
        expected_header = self.loader_class.expected_header
        header = ScreeningLoader.get_header(path)

        if not header:
            comments.append('File not found')
        elif header == expected_header:
            loadable = True
            comments.append('OK')
        elif self.alternative_headers and header in self.alternative_headers:
            loadable = True
            comments.append('OK, using alternative header')
        else:
            comments.append('Incompatible')

        field_props = {
            'loadable': loadable,
            'comment': f'{", ".join(comments)}',
        }
        return field_props


class BaseListActionFormView(LoginRequiredMixin, FormView):
    http_method_names = ['post']
    form_class = DummyForm
    template_name = None
    loader_class = None
    success_template_name = None
    invalid_template_name = None
    invalid_template_query = None

    def form_valid(self, form):
        session = self.request.session
        festival_id = list(self.request.POST.keys())[-1]
        festival = Festival.festivals.get(id=festival_id)
        switch_festival(session, festival)
        initialize_log(session)
        _ = self.loader_class(session, festival, festival_pk='film__festival__pk').load_objects()
        return super().form_valid(form)

    def form_invalid(self, form):
        super().form_invalid(form)
        ScreeningsLoaderView.unexpected_error = '\n'.join(wrap_up_form_errors(form.errors))
        return HttpResponseRedirect(reverse(self.invalid_template_name) + self.invalid_template_query or '')

    def get_success_url(self):
        return reverse(self.success_template_name)


class ScreeningsLoaderView(SharedTemplateReferrerView):
    """
    Class-based view to load the screenings of a specific festival.
    """
    template_name = 'loader/list_action.html'
    unexpected_error = ''

    def __init__(self):
        super().__init__()
        self.list_view = ScreeningLoaderListView
        self.form_view = ScreeningLoaderFormView


class ScreeningLoaderListView(BaseListActionListView):
    template_name = ScreeningsLoaderView.template_name
    loader_class = ScreeningLoader
    load_file = 'screenings_file'
    manager = Screening.screenings
    title = 'Festival Screenings Loader'
    list_name = 'screenings'
    festival_filter = 'film__festival'
    alternative_headers = [ScreeningLoader.alternative_header]


class ScreeningLoaderFormView(BaseListActionFormView):
    template_name = ScreeningsLoaderView.template_name
    loader_class = ScreeningLoader
    success_template_name = 'screenings:day_schema'
    invalid_template_name = 'loader:list_action'
    invalid_template_query = 'screenings'


class AttendanceLoaderView(SharedTemplateReferrerView):
    """
    Class-based view to load the attendances of a specific festival.
    """
    template_name = 'loader/list_action.html'
    unexpected_error = ''

    def __init__(self):
        super().__init__()
        self.list_view = AttendanceLoaderListView
        self.form_view = AttendanceLoaderFormView


class AttendanceLoaderListView(BaseListActionListView):
    template_name = AttendanceLoaderView.template_name
    loader_class = AttendanceLoader
    load_file = 'screening_info_file'
    manager = Attendance.attendances
    title = 'Festival Attendances Loader'
    list_name = 'attendances'
    festival_filter = 'screening__film__festival'


class AttendanceLoaderFormView(BaseListActionFormView):
    template_name = AttendanceLoaderView.template_name
    loader_class = AttendanceLoader
    success_template_name = 'screenings:day_schema'
    invalid_template_name = 'loader:list_action'
    invalid_template_query = 'attendances'


class TicketLoaderView(SharedTemplateReferrerView):
    """
    Class-based view to load the tickets of a specific festival.
    """
    template_name = 'loader/list_action.html'
    unexpected_error = ''

    def __init__(self):
        super().__init__()
        self.list_view = TicketLoaderListView
        self.form_view = TicketLoaderFormView


class TicketLoaderListView(AttendanceLoaderListView):
    template_name = TicketLoaderView.template_name
    loader_class = TicketLoader
    manager = Ticket.tickets
    title = 'Festival Tickets Loader'
    list_name = 'tickets'


class TicketLoaderFormView(AttendanceLoaderFormView):
    template_name = TicketLoaderView.template_name
    loader_class = TicketLoader
    invalid_template_query = 'tickets'


class BaseDumperView(LoginRequiredMixin, FormView):
    """
    Base view to derive single model date dumpers from.

    These globals should be filled:
    - dump_class, must be derived from BaseDumper
    - success_url
    - data_name, for use in log texts
    - has_header, whether the dumpfile should have a header

    Thes globals should be assigned in setup():
    - dumpfile
    - queryset
    """
    model = Festival
    http_method_names = ['get', 'post']
    template_name = 'loader/dump_data.html'
    form_class = SingleTableDumperForm
    dump_class = None
    success_url = None
    data_name = None
    dumpfile = None
    has_header = None
    manager = None
    queryset = None
    session = None
    display_props = None
    festival = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.session = request.session
        self.festival = current_festival(self.session)
        self.display_props = []

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        self.add_display_props(self.data_name, self.queryset, self.dumpfile, self.has_header)
        new_context = {
            'title': f'Dump {self.data_name}',
            'subtitle': f'Dump {self.data_name} of {self.festival}',
            'data_name': self.data_name,
            'display_props': self.display_props,
            'dumpfile': self.dumpfile,
            'log': get_log(self.session),
        }
        unset_log(self.session)
        context = add_base_context(self.request, super_context | new_context)
        return context

    def form_valid(self, form):
        form.dump_data(self.session, self.festival, self.data_name, self.dump_class, self.dumpfile, self.queryset)
        return super().form_valid(form)

    def add_display_props(self, name, queryset, dumpfile, has_header=False):
        self.display_props.append({
            'name': name,
            'data_count': len(queryset),
            'data_count_on_file': file_record_count(dumpfile, has_header=has_header),
        })


class RatingDumperView(BaseDumperView):
    dump_class = RatingDumper
    success_url = '/films/films/'
    data_name = 'ratings'
    has_header = True

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.dumpfile = self.festival.ratings_file()
        self.queryset = FilmFanFilmRating.film_ratings.filter(film__festival=self.festival)

        extra_queryset = Film.films.filter(festival=self.festival)
        extra_dump_file = self.festival.films_file()
        self.add_display_props('films', extra_queryset, extra_dump_file, has_header=True)


class AttendanceDumperView(BaseDumperView):
    dump_class = AttendanceDumper
    success_url = '/screenings/day_schema/'
    data_name = 'attendances'
    has_header = True

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.dumpfile = self.festival.attendances_file()
        self.queryset = Attendance.attendances.filter(screening__film__festival=self.festival)


class TicketDumperView(BaseDumperView):
    dump_class = TicketDumper
    success_url = '/screenings/day_schema/'
    data_name = 'tickets'
    has_header = True

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.dumpfile = self.festival.tickets_file()
        self.queryset = Ticket.tickets.filter(screening__film__festival=self.festival)


class SingleTemplateBaseView(SharedTemplateReferrerView):
    http_method_names = ['get', 'post']
    label_cookie = Cookie('label')
    view_class_by_label = None
    view_class = None

    def dispatch(self, request, *args, **kwargs):
        self.label_cookie.handle_get_request(request)
        data_name = self.label_cookie.get(request.session)
        self.view_class = self.view_class_by_label[data_name]
        self.list_view = self.view_class
        self.form_view = self.view_class
        return super().dispatch(request, *args, **kwargs)


class SingleTemplateListView(SingleTemplateBaseView):
    view_class_by_label = {
        'screenings': ScreeningsLoaderView,
        'attendances': AttendanceLoaderView,
        'tickets': TicketLoaderView,
    }


class SingleTemplateDumperView(SingleTemplateBaseView):
    view_class_by_label = {
        'ratings': RatingDumperView,
        'attendances': AttendanceDumperView,
        'tickets': TicketDumperView,
    }
