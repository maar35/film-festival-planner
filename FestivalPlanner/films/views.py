import copy
import csv
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, DetailView, ListView

from festival_planner.cache import FilmRatingCache
from festival_planner.debug_tools import pr_debug
from festival_planner.tools import add_base_context, unset_log, wrap_up_form_errors, application_name, get_log, \
    set_cookie, get_cookie
from festivals.config import Config
from festivals.models import current_festival
from films.forms.film_forms import RatingForm, PickRating, UserForm
from films.models import FilmFanFilmRating, Film, current_fan, get_present_fans, fan_rating_str, fan_rating_name
from authentication.models import FilmFan
from sections.models import Subsection

STICKY_HEIGHT = 3


class FilmsView(LoginRequiredMixin, View):
    """
    Film list with updatable ratings.
    """
    template_name = 'films/films.html'
    submit_name_prefix = 'list_'
    unexpected_errors = []

    @staticmethod
    def get(request, *args, **kwargs):
        view = FilmsListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = FilmsFormView.as_view()
        return view(request, *args, **kwargs)


class FilmsListView(LoginRequiredMixin, ListView):
    template_name = FilmsView.template_name
    context_object_name = 'film_rows'
    http_method_names = ['get']
    title = 'Film Rating List'
    highest_rating = FilmFanFilmRating.Rating.values[-1]
    config = Config().config
    max_short_minutes = config['Constants']['MaxShortMinutes']
    short_threshold = timedelta(minutes=max_short_minutes)
    fragment_name_by_row_nr = {}
    include_by_query = {'hide': False, 'include': True}
    query_by_include = {include: query for query, include in include_by_query.items()}
    action_by_display_shorts = {True: 'Hide shorts', False: 'Include shorts'}
    action_by_display_rated = {True: 'Hide rated', False: 'Include rated'}
    description_by_film_id = {}
    fan_list = get_present_fans()
    logged_in_fan = None
    festival = None
    selected_films = None
    festival_feature_films = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.display_shorts = True
        self.display_rated_by_fan = {fan: True for fan in self.fan_list}

    def dispatch(self, request, *args, **kwargs):
        pr_debug('start', with_time=True)
        session = self.request.session

        # Initialize the filter cookies when necessary.
        set_cookie(session, 'shorts', get_cookie(session, 'shorts', self.display_shorts))
        for fan, display_rated in self.display_rated_by_fan.items():
            key = rated_key(fan)
            set_cookie(session, key, get_cookie(session, key, self.display_rated_by_fan[fan]))

        # Ensure the film rating cache is initialized.
        if not PickRating.film_rating_cache:
            PickRating.film_rating_cache = FilmRatingCache(request.session, FilmsView.unexpected_errors)

        # Apply filters from url query part.
        filter_dict = {}
        self.set_cookie_filter('shorts')
        filter_dict['shorts'] = get_cookie(session, 'shorts')
        for fan in self.fan_list:
            key = rated_key(fan)
            self.set_cookie_filter(key)
            filter_dict[key] = get_cookie(session, key)

        # Add the filters to the cache key.
        FilmRatingCache.set_filters(session, filter_dict)

        pr_debug('done', with_time=True)
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        pr_debug('start', with_time=True)
        session = self.request.session
        self.logged_in_fan = current_fan(session)
        self.festival = current_festival(session)
        self.fragment_name_by_row_nr = {}

        # Return the cache when valid.
        if PickRating.film_rating_cache.is_valid(session):
            pr_debug('done, cache is valid', with_time=True)
            return PickRating.film_rating_cache.get_film_rows(session)

        # Filter the films as requested.
        pr_debug('start filtered query', with_time=True)
        filter_kwargs = {'festival': self.festival}
        if not get_cookie(session, 'shorts'):
            filter_kwargs['duration__gt'] = self.short_threshold
        self.selected_films = Film.films.filter(**filter_kwargs).order_by('seq_nr')
        self.festival_feature_films = copy.deepcopy(self.selected_films)
        for fan in self.fan_list:
            if not get_cookie(session, rated_key(fan)):
                self.selected_films = self.selected_films.filter(
                    ~Exists(FilmFanFilmRating.film_ratings.filter(film=OuterRef('pk'), film_fan=fan))
                )

        # Read the descriptions.
        film_info_file = self.festival.filminfo_file
        try:
            with open(film_info_file, 'r', newline='') as csvfile:
                object_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
                self.description_by_film_id = {int(row[0]): row[1] for row in object_reader}
        except FileNotFoundError as e:
            self.description_by_film_id = {}
            FilmsView.unexpected_errors.append(e)

        # Fill the film rows.
        film_rows = [self.get_film_row(row_nr, film) for row_nr, film in enumerate(self.selected_films)]

        # Add a fragment name as to be able to address a specific film.
        pr_debug('start defining fragments', with_time=True)
        for row_nr, film_row in enumerate(film_rows):
            try:
                film_row['fragment_name'] = self.fragment_name_by_row_nr[row_nr]
            except KeyError:
                film_row['fragment_name'] = 0

        # Fill the cache.
        PickRating.film_rating_cache.set_film_rows(session, film_rows)

        pr_debug('done', with_time=True)
        return film_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        session = self.request.session
        pr_debug(f'start, {len(PickRating.film_rating_cache.get_film_rows(session))} records in cache', with_time=True)
        super_context = super().get_context_data(**kwargs)
        film_count, rated_films_count, count_dicts = get_rating_statistics(session)
        display_shorts = get_cookie(session, 'shorts')
        new_context = {
            'title': self.title,
            'fan_headers': self.get_fan_headers(),
            'feature_count': film_count,
            'rated_features_count': rated_films_count,
            'highest_rating': self.highest_rating,
            'eligible_counts': count_dicts,
            'short_threshold': self.short_threshold.total_seconds(),
            'display_shorts_query': self.query_by_include[not display_shorts],
            'display_shorts_action': self.action_by_display_shorts[display_shorts],
            'unexpected_errors': FilmsView.unexpected_errors,
            'log': get_log(session)
        }
        unset_log(session)
        context = add_base_context(self.request, {**super_context, **new_context})
        PickRating.refresh_rating_action(session, context)
        pr_debug('done', with_time=True)
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        FilmsView.unexpected_errors = []
        return response

    def set_cookie_filter(self, request_key, cookie_key=None):
        cookie_key = cookie_key or request_key
        request = self.request
        if request_key in request.GET:
            query_key = request.GET[request_key]
            include = self.include_by_query[query_key]
            set_cookie(request.session, cookie_key, include)

    def get_film_row(self, row_nr, film):
        fragment_row = row_nr - STICKY_HEIGHT if row_nr > STICKY_HEIGHT else 0
        self.fragment_name_by_row_nr[fragment_row] = f'film{film.film_id}'
        film_rating_row = {
            'film': film,
            'fragment_name': None,
            'duration_str': film.duration_str(),
            'duration_seconds': film.duration.total_seconds(),
            'subsection': self.get_subsection(film),
            'section': None,
            'description': self.get_description(film),
            'film_ratings': get_fan_ratings(film, self.fan_list, self.logged_in_fan, FilmsView.submit_name_prefix),
        }
        return film_rating_row

    @staticmethod
    def get_subsection(film):
        if len(film.subsection) == 0:
            return ''
        try:
            subsection = Subsection.subsections.get(festival=film.festival, subsection_id=film.subsection)
        except Subsection.DoesNotExist as e:
            FilmsView.unexpected_errors.append(f'{e}')
            subsection = ''
        return subsection

    def get_description(self, film):
        try:
            description = self.description_by_film_id[film.film_id]
        except KeyError:
            description = None
        return description

    def get_fan_headers(self):
        session = self.request.session
        fan_headers = [{
            'fan': fan,
            'query': self.query_by_include[not get_cookie(session, rated_key(fan))],
            'action': self.action_by_display_rated[get_cookie(session, rated_key(fan))],
        } for fan in self.fan_list]
        return fan_headers


class FilmsFormView(LoginRequiredMixin, FormView):
    template_name = FilmsView.template_name
    form_class = PickRating
    http_method_names = ['post']
    film = None

    def form_valid(self, form):
        submitted_name = list(self.request.POST.keys())[-1]
        if submitted_name is not None:
            pr_debug('start update', with_time=True)
            film_pk, rating_value = submitted_name.strip(FilmsView.submit_name_prefix).split('_')
            self.film = Film.films.get(id=film_pk)
            session = self.request.session
            fan = current_fan(session)
            form.update_rating(session, self.film, fan, rating_value)
            pr_debug('done update', with_time=True)
        else:
            FilmsView.unexpected_errors.append("Can't identify submit widget.")
        return super().form_valid(form)

    def form_invalid(self, form):
        FilmsView.unexpected_errors.append(f'Form {form} invalid:\n{wrap_up_form_errors(form.errors)}')
        return super().form_invalid(form)

    def get_success_url(self):
        fragment = '#top' if FilmsView.unexpected_errors else f'#film{self.film.film_id}'
        pr_debug(f'{fragment=}', with_time=True)
        return reverse('films:films') + fragment


class VotesView(LoginRequiredMixin, View):
    template_name = 'films/votes.html'

    @staticmethod
    def get(request, *args, **kwargs):
        view = VotesListView.as_view()
        return view(request, *args, **kwargs)


class VotesListView(LoginRequiredMixin, ListView):
    template_name = VotesView.template_name
    context_object_name = 'vote_rows'
    http_method_names = ['get']
    title = 'Film Votes List'
    logged_in_fan = None
    festival = None

    def get_queryset(self):
        session = self.request.session
        self.logged_in_fan = current_fan(session)
        self.festival = current_festival(session)

        # Fill the vote rows.
        selected_films = Film.films.filter(festival=self.festival).order_by('seq_nr')[0:20]
        return selected_films

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        new_context = {
            'title': self.title,
        }
        context = add_base_context(self.request, {**super_context, **new_context})
        return context


class ResultsView(DetailView):
    """
    Define generic view classes.
    """
    model = Film
    template_name = 'films/results.html'
    http_method_names = ['get', 'post']
    submit_name_prefix = 'results_'
    submit_names = []
    unexpected_error = ''

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        if request.method == 'POST':
            submitted_name = get_submitted_name(request, self.submit_names)
            session = self.request.session
            if submitted_name is not None:
                [film_pk, rating_value] = submitted_name.strip(self.submit_name_prefix).split('_')
                film = Film.films.get(id=film_pk)
                PickRating.update_rating(session, film, current_fan(session), rating_value)

                return HttpResponseRedirect(reverse('films:results', args=(film_pk,)))
            else:
                self.unexpected_error = "Can't identify submit widget."

        unset_log(request.session)
        return response

    def get_context_data(self, **kwargs):
        film = self.object
        subsection = get_subsection(film)
        fan_rows = []
        fans = FilmFan.film_fans.all()
        logged_in_fan = current_fan(self.request.session)
        for fan in fans:
            choices = get_fan_choices(self.submit_name_prefix, film, fan, logged_in_fan, self.submit_names)
            fan_rows.append({
                'fan': fan,
                'rating_str': fan_rating_str(fan, film),
                'rating_name': fan_rating_name(fan, film),
                'choices': choices,
            })
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Film Rating Results'
        context['subsection'] = subsection
        context['description'] = self.get_description(film)
        context['fan_rows'] = fan_rows
        context['unexpected_error'] = self.unexpected_error
        return context

    @staticmethod
    def get_description(film):
        film_info_file = film.festival.filminfo_file
        # with open(film_info_file, 'r') as stream:
        #     info = yaml.safe_load(stream)
        # description = info['description']
        with open(film_info_file, 'r', newline='') as csvfile:
            object_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
            descriptions = [row[1] for row in object_reader if film.film_id == int(row[0])]
        description = descriptions[0] if descriptions else '-'
        return description


def index(request):
    """
    General index page.
    :param request:
    :return: the rendered index page
    """

    # Set-up parameters.
    title = f'{application_name()} App Index'
    fan = current_fan(request.session)
    user_name = fan if fan is not None else 'Guest'

    # Unset load results cookie.
    unset_log(request.session)

    # Construct the parameters.
    context = add_base_context(request, {
        'title': title,
        'name': user_name,
    })

    return render(request, 'films/index.html', context)


def film_fan(request):
    """
    Film fan switching view.
    """

    # Preset some parameters.
    title = 'Film Fans'

    # Check the request.
    if request.method == 'POST':
        form = UserForm(request.POST)
        if form.is_valid():
            selected_fan = form.cleaned_data['selected_fan']
            fan = FilmFan.film_fans.get(name=selected_fan)
            fan.switch_current(request.session)
            return HttpResponseRedirect(reverse('films:index'))
    else:
        form = UserForm(initial={'current_fan': current_fan(request.session)}, auto_id=False)

    # Construct the context.
    context = add_base_context(request, {
        'title': title,
        'form': form,
    })

    return render(request, 'films/film_fan.html', context)


def rated_key(fan):
    return f'rated_{fan}'


def get_rating_statistics(session):
    def get_stats_for_rating(base_rating):
        counts = [count for r, count in count_by_eligible_rating.items() if r >= base_rating]
        plannable_films_count = sum(counts)
        if rated_films_count > 0:
            projected_plannable_count = int(film_count * plannable_films_count / rated_films_count)
        else:
            projected_plannable_count = None
        return {
            'base_rating': base_rating,
            'plannable_films_count': plannable_films_count,
            'projected_plannable_count': projected_plannable_count,
        }

    # Initialize.
    films = [film_row['film'] for film_row in PickRating.film_rating_cache.get_film_rows(session)]
    config = Config().config
    max_short_minutes = config['Constants']['MaxShortMinutes']
    max_short_duration = timedelta(minutes=max_short_minutes)
    lowest_plannable_rating = config['Constants']['LowestPlannableRating']
    feature_films = [film for film in films if film.duration > max_short_duration]
    eligible_ratings = FilmFanFilmRating.Rating.values[lowest_plannable_rating:]
    film_count = len(feature_films)

    # Filter out the data with eligible ratings.
    rated_films_count = 0
    count_by_eligible_rating = {}
    for feature_film in feature_films:
        rating_set = FilmFanFilmRating.film_ratings.filter(film=feature_film, rating__gt=0)
        if len(rating_set):
            rated_films_count += 1
            best_rating = max([r.rating for r in rating_set])
            if best_rating in eligible_ratings:
                try:
                    count_by_eligible_rating[best_rating] += 1
                except KeyError:
                    count_by_eligible_rating[best_rating] = 1

    # Find the statistics for all eligible ratings.
    count_dicts = []
    for eligible_rating in eligible_ratings:
        count_dicts.append(get_stats_for_rating(eligible_rating))

    return film_count, rated_films_count, count_dicts


def get_fan_ratings(film, fan_list, logged_in_fan, submit_name_prefix):
    film_ratings = []
    for fan in fan_list:
        # Set a rating string to display.
        rating_str = fan_rating_str(fan, film)

        # Get choices for this fan.
        choices = [{
            'value': value,
            'rating_name': name,
            'submit_name': f'{submit_name_prefix}{film.id}_{value}'
        } for value, name in FilmFanFilmRating.Rating.choices] if fan == logged_in_fan else []

        # Append a fan rating dictionary to the list.
        film_ratings.append({
            'fan': fan,
            'rating': rating_str,
            'choices': choices
        })
    return film_ratings


def get_fan_choices(submit_name_prefix, film, fan, logged_in_fan, submit_names):
    # Set the rating choices if this fan is the current fan.
    choices = []
    if fan == logged_in_fan:
        for value, name in FilmFanFilmRating.Rating.choices:
            choice = {
                'value': value,
                'rating_name': name,
                'submit_name': f'{submit_name_prefix}{film.id}_{value}'
            }
            choices.append(choice)
            submit_names.append(choice['submit_name'])

    return choices


def get_subsection(film):
    if len(film.subsection) == 0:
        return ''
    subsection = Subsection.subsections.get(festival=film.festival, subsection_id=film.subsection)
    return subsection


def get_submitted_name(request, submit_names):
    submitted_name = None
    for submit_name in submit_names:
        if submit_name in request.POST:
            submitted_name = submit_name
            break
    return submitted_name


@login_required
def rating(request, film_pk):
    """
    rating picker view.
    """

    # Preset some parameters.
    title = "Rating Picker"
    film = get_object_or_404(Film, id=film_pk)
    fan = current_fan(request.session)

    # Check the request.
    if request.method == 'POST':
        form = RatingForm(request.POST)
        if form.is_valid():
            selected_rating = form.cleaned_data['fan_rating']
            PickRating.update_rating(request.session, film, fan, selected_rating)
            return HttpResponseRedirect(reverse('films:results', args=[film_pk]))
    else:
        try:
            current_rating = FilmFanFilmRating.film_ratings.get(film=film, film_fan=fan)
        except FilmFanFilmRating.DoesNotExist:
            form = RatingForm()
        else:
            form = RatingForm(initial={'fan_rating': current_rating.rating}, auto_id=False)

    # Construct the context.
    context = add_base_context(request, {
        'title': title,
        'film': film,
        'form': form,
    })

    return render(request, 'films/rating.html', context)
