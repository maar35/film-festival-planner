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
from festival_planner.tools import add_base_context, get_log, unset_log, initialize_log, wrap_up_form_errors
from festivals.models import Festival, switch_festival, current_festival, FestivalBase
from films.models import Film, FilmFanFilmRating
from loader.forms.loader_forms import SectionLoader, SubsectionLoader, RatingLoaderForm, TheaterDataLoaderForm, \
    TheaterDataDumperForm, CityLoader, TheaterLoader, ScreenLoader, TheaterDataUpdateForm, SaveRatingsForm, \
    RatingDataBackupForm, FILM_FANS_BACKUP_PATH, RATINGS_BACKUP_PATH, FILMS_BACKUP_PATH, \
    FESTIVALS_BACKUP_PATH, FESTIVAL_BASES_BACKUP_PATH, BACKUP_DATA_DIR, CITIES_BACKUP_PATH, ScreeningsLoaderForm, \
    ScreeningLoader
from screenings.models import Screening
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


def get_theater_items():
    theater_items = {
        'city_count': City.cities.count,
        'city_count_on_file': file_record_count(cities_path()),
        'theater_count': Theater.theaters.count,
        'theater_count_on_file': file_record_count(theaters_path()),
        'screen_count': Screen.screens.count,
        'screen_count_on_file': file_record_count(screens_path()),
    }
    return theater_items


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
        context['theater_items'] = get_theater_items()
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
    object_list = None
    context_object_name = 'festival_items'
    unexpected_error = ''

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.submit_name_prefix = 'ratings_'

    def get_queryset(self):
        festival_list = sorted(Festival.festivals.all(), key=attrgetter('start_date'), reverse=True)
        festival_rows = [self.get_festival_row(festival) for festival in festival_list]
        return festival_rows

    def get_context_data(self, **kwargs):
        self.object_list = self.get_queryset()
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Load Ratings'
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
                    switch_festival(request.session, festival)
                    form.load_rating_data(request.session, festival, import_mode)
                    return HttpResponseRedirect(reverse('films:films'))
                else:
                    self.unexpected_error = "Can't identify submit widget."

        return render(request, 'loader/ratings.html', self.get_context_data())

    def get_festival_row(self, festival):
        festival_row = {
            'str': festival,
            'submit_name': f'{self.submit_name_prefix}{festival.id}',
            'color': festival.festival_color,
            'film_count_on_file': file_record_count(festival.films_file(), has_header=True),
            'film_count': Film.films.filter(festival=festival).count,
            'rating_count_on_file': file_record_count(festival.ratings_file(), has_header=True),
            'rating_count': FilmFanFilmRating.film_ratings.filter(film__festival=festival).count,
        }
        return festival_row


class SaveRatingsView(LoginRequiredMixin, FormView):
    model = Festival
    template_name = 'loader/save_ratings.html'
    form_class = SaveRatingsForm
    success_url = '/films/films/'
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        session = self.request.session
        festival = current_festival(session)
        festival_items = {
            'festival': festival,
            'film_count': len(Film.films.filter(festival=festival)),
            'film_count_on_file': file_record_count(festival.films_file(), has_header=True),
            'rating_count': len(FilmFanFilmRating.film_ratings.filter(film__festival=festival)),
            'rating_count_on_file': file_record_count(festival.ratings_file(), has_header=True),
            'ratings_file': festival.ratings_file(),
        }
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Save Ratings'
        context['festival_items'] = festival_items
        context['log'] = get_log(session)
        unset_log(session)
        return context

    def form_valid(self, form):
        session = self.request.session
        festival = current_festival(session)
        form.save_ratings(session, festival)
        return super().form_valid(form)


class ScreeningsLoaderView(LoginRequiredMixin, View):
    """
    Class-based view to load the screenings of a specific festival.
    """
    template_name = 'loader/screenings.html'
    unexpected_error = ''

    @staticmethod
    def get(request, *args, **kwargs):
        view = ScreeningLoaderListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = ScreeningLoaderFormView.as_view()
        return view(request, *args, **kwargs)


class ScreeningLoaderListView(LoginRequiredMixin, ListView):
    template_name = ScreeningsLoaderView.template_name
    http_method_names = ['get']
    context_object_name = 'festival_rows'
    object_list = None

    def get_queryset(self):
        festivals = Festival.festivals.order_by('-start_date')
        festival_rows = [self._get_festival_row(festival) for festival in festivals]
        return festival_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        session = self.request.session
        context = add_base_context(self.request, super().get_context_data(object_list=object_list, **kwargs))
        context['title'] = 'Festival Screenings Loader'
        context['unexpected_error'] = ScreeningsLoaderView.unexpected_error
        context['log'] = get_log(session)
        unset_log(session)
        return context

    @staticmethod
    def _get_festival_row(festival):
        festival_row = {
            'festival': festival,
            'screening_file_field_count': 0,                            # TODO: add flesh here!
            'screening_count_on_file': file_record_count(festival.screenings_file(), has_header=True),
            'screening_count': Screening.screenings.filter(film__festival=festival).count,
        }
        return festival_row


class ScreeningLoaderFormView(LoginRequiredMixin, FormView):
    template_name = ScreeningsLoaderView.template_name
    form_class = ScreeningsLoaderForm
    http_method_names = ['post']

    def form_valid(self, form):
        session = self.request.session
        festival_id = list(self.request.POST.keys())[-1]
        festival = Festival.festivals.get(id=festival_id)
        switch_festival(session, festival)
        initialize_log(session)
        _ = ScreeningLoader(session, festival, festival_pk='film__festival__pk').load_objects()
        return super().form_valid(form)

    def form_invalid(self, form):
        super().form_invalid(form)
        ScreeningsLoaderView.unexpected_error = '\n'.join(wrap_up_form_errors(form.errors))
        return HttpResponseRedirect(reverse('loader:screenings'))

    def get_success_url(self):
        return reverse('screenings:day_schema')
