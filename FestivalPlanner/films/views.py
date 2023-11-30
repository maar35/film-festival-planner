import copy
from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, DetailView, ListView

from festival_planner.tools import add_base_context, unset_log, get_log, wrap_up_form_errors, application_name
from festivals.config import Config
from festivals.models import Festival, current_festival
from films.forms.film_forms import RatingForm, PickRating, UserForm
from films.models import FilmFanFilmRating, Film, FilmFan, current_fan, get_present_fans
from loader.forms.loader_forms import SaveRatingsForm
from loader.views import file_record_count
from sections.models import Subsection


class FilmsView(LoginRequiredMixin, View):
    """
    Film list with updatable ratings.
    """
    template_name = 'films/films.html'
    submit_name_prefix = 'list_'
    unexpected_errors = None
    display_shorts = True
    display_rated_by_fan = {fan.name: True for fan in get_present_fans()}

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
    http_method_names = ['get']
    queryset = None
    context_object_name = 'film_rows'
    title = 'Film Rating List'
    highest_rating = FilmFanFilmRating.Rating.values[-1]
    config = Config().config
    max_short_minutes = config['Constants']['MaxShortMinutes']
    short_threshold = timedelta(minutes=max_short_minutes)
    sticky_height = 2
    fragment_name_by_row_nr = {}
    action_by_display_shorts = {True: 'Hide shorts', False: 'Include shorts'}
    action_by_display_rated = {True: 'Hide rated', False: 'Include rated'}
    fan_list = get_present_fans()
    logged_in_fan = None
    festival = None
    selected_films = None
    festival_feature_films = None

    def dispatch(self, request, *args, **kwargs):
        if 'filter' in request.GET:
            column_filter = request.GET['filter']
            if column_filter == 'shorts':
                FilmsView.display_shorts = not FilmsView.display_shorts
        for fan in self.fan_list:
            if f'filter_{fan}' in request.GET:
                column_filter = request.GET[f'filter_{fan}']
                if column_filter == 'rated':
                    FilmsView.display_rated_by_fan[fan.name] = not FilmsView.display_rated_by_fan[fan.name]
        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        FilmsView.unexpected_errors = []
        session = self.request.session
        self.logged_in_fan = current_fan(session)
        self.festival = current_festival(session)
        self.fragment_name_by_row_nr = {}

        # Filter the films as requested.
        filter_kwargs = {'festival': self.festival}
        if not FilmsView.display_shorts:
            filter_kwargs['duration__gt'] = self.short_threshold
        self.selected_films = Film.films.filter(**filter_kwargs).order_by('seq_nr')
        self.festival_feature_films = copy.deepcopy(self.selected_films)
        for fan in self.fan_list:
            if not FilmsView.display_rated_by_fan[fan.name]:
                self.selected_films = self.selected_films.filter(
                    ~Exists(FilmFanFilmRating.film_ratings.filter(film=OuterRef('pk'), film_fan=fan))
                )
        film_rows = [self.get_film_row(row_nr, film) for row_nr, film in enumerate(self.selected_films)]

        # Add a fragment name as to be able to address a specific film.
        for row_nr, film_row in enumerate(film_rows):
            try:
                film_row['fragment_name'] = self.fragment_name_by_row_nr[row_nr]
            except KeyError:
                film_row['fragment_name'] = 0

        return film_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        film_count, rated_films_count, count_dicts = get_rating_statistic(self.festival_feature_films)
        new_context = {
            'title': self.title,
            'fan_headers': self.get_fan_headers(),
            'feature_count': film_count,
            'rated_features_count': rated_films_count,
            'highest_rating': self.highest_rating,
            'eligible_counts': count_dicts,
            'short_threshold': self.short_threshold.total_seconds(),
            'display_shorts_action': self.action_by_display_shorts[FilmsView.display_shorts],
            'unexpected_errors': FilmsView.unexpected_errors,
        }
        context = add_base_context(self.request, {**super_context, **new_context})
        session = self.request.session
        PickRating.refresh_rating_action(session, context)
        context['log'] = get_log(session)
        return context

    def get_film_row(self, row_nr, film):
        fragment_row = row_nr - self.sticky_height if row_nr > self.sticky_height else 0
        self.fragment_name_by_row_nr[fragment_row] = f'film{film.film_id}'
        film_rating_row = {
            'film': film,
            'fragment_name': None,
            'duration_str': film.duration_str(),
            'duration_seconds': film.duration.total_seconds(),
            'subsection': self.get_subsection(film),
            'section': None,
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

    def get_fan_headers(self):
        fan_headers = [{
            'fan': fan,
            'action': self.action_by_display_rated[FilmsView.display_rated_by_fan[fan.name]]
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
            film_pk, rating_value = submitted_name.strip(FilmsView.submit_name_prefix).split('_')
            self.film = Film.films.get(id=film_pk)
            session = self.request.session
            fan = current_fan(session)
            form.update_rating(session, self.film, fan, rating_value)
        else:
            FilmsView.unexpected_errors.append("Can't identify submit widget.")
        return super().form_valid(form)

    def form_invalid(self, form):
        FilmsView.unexpected_errors.append(f'Form {form} invalid:\n{wrap_up_form_errors(form.errors)}')
        return super().form_invalid(form)

    def get_success_url(self):
        return reverse('films:films') + f'#film{self.film.film_id}'


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
                'rating_str': fan.fan_rating_str(film),
                'rating_name': fan.fan_rating_name(film),
                'choices': choices,
            })
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Film Rating Results'
        context['subsection'] = subsection
        context['fan_rows'] = fan_rows
        context['unexpected_error'] = self.unexpected_error
        return context

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


class SaveView(LoginRequiredMixin, FormView):
    model = Festival
    template_name = 'films/save.html'
    form_class = SaveRatingsForm
    success_url = '/films/films/'
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        session = self.request.session
        festival = current_festival(session)
        festival_items = {
            'festival': festival,
            'film_count': len(Film.films.filter(festival=festival)),
            'film_count_on_file': file_record_count(festival.films_file, has_header=True),
            'rating_count': len(FilmFanFilmRating.film_ratings.filter(film__festival=festival)),
            'rating_count_on_file': file_record_count(festival.ratings_file, has_header=True),
            'ratings_file': festival.ratings_file,
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


def get_rating_statistic(films):
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
        rating_str = fan.fan_rating_str(film)

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
