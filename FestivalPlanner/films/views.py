import copy
import csv
import re
from datetime import timedelta
from operator import attrgetter, itemgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import View
from django.views.generic import FormView, DetailView, ListView, TemplateView

from authentication.models import FilmFan
from festival_planner.cache import FilmRatingCache
from festival_planner.debug_tools import pr_debug
from festival_planner.tools import add_base_context, unset_log, wrap_up_form_errors, application_name, get_log, \
    set_cookie, get_cookie, initialize_log, add_log
from festivals.config import Config
from festivals.models import current_festival
from films.forms.film_forms import PickRating, UserForm, refreshed_rating_action
from films.models import FilmFanFilmRating, Film, current_fan, get_present_fans, fan_rating_str, \
    FilmFanFilmVote, fan_rating
from sections.models import Subsection

STICKY_HEIGHT = 3
CONSTANTS_CONFIG = Config().config['Constants']
MAX_SHORT_MINUTES = CONSTANTS_CONFIG['MaxShortMinutes']
LOWEST_PLANNABLE_RATING = CONSTANTS_CONFIG['LowestPlannableRating']


class FragmentKeeper:

    def __init__(self):
        self.film_id_by_row_nr = {}

    @staticmethod
    def fragment_name(film_id):
        return f'film{film_id}'

    @classmethod
    def fragment_code(cls, film_id):
        return f'#{cls.fragment_name(film_id)}'

    def add_fragments(self, films):
        for row_nr, film in enumerate(films):
            self.add_fragment(row_nr, film)

    def add_fragment(self, row_nr, film):
        fragment_row = row_nr - STICKY_HEIGHT if row_nr > STICKY_HEIGHT else 0
        self.film_id_by_row_nr[fragment_row] = film.film_id

    def get_fragment_name(self, row_nr):
        try:
            film_id = self.film_id_by_row_nr[row_nr]
        except KeyError:
            fragment_name = ''
        else:
            fragment_name = FragmentKeeper.fragment_name(film_id)
        return fragment_name


class Filter:
    filtered_by_query = {'display': False, 'hide': True}
    query_by_filtered = {filtered: query for query, filtered in filtered_by_query.items()}

    def __init__(self, action_subject, cookie_key=None, filtered=False, action_true=None, action_false=None):
        self._cookie_key = cookie_key or action_subject.strip().replace(' ', '-')
        self._filtered = filtered
        action_true = action_true or f'Display {action_subject}'
        action_false = action_false or f'Hide {action_subject}'
        self._action_by_filtered = {True: action_true, False: action_false}

    def init_cookie(self, session):
        set_cookie(session, self._cookie_key, get_cookie(session, self._cookie_key, self._filtered))

    def get_cookie_key(self):
        return self._cookie_key

    def handle_request(self, request):
        if self._cookie_key in request.GET:
            query_key = request.GET[self._cookie_key]
            filtered = self.filtered_by_query[query_key]
            set_cookie(request.session, self._cookie_key, filtered)

    def get_href_filter(self, session):
        return f'?{self.get_cookie_key()}={self.next_query(session)}'

    def on(self, session, default=None):
        return get_cookie(session, self._cookie_key, default)

    def off(self, session, default=None):
        return not self.on(session, default)

    def next_query(self, session):
        return self.query_by_filtered[self.off(session)]

    def action(self, session):
        return self._action_by_filtered[self.on(session)]


class IndexView(TemplateView):
    """
    General index page.
    """
    template_name = 'films/index.html'
    http_method_names = ['get']

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)

        # Unset log cookie.
        unset_log(request.session)

    def get_context_data(self, **kwargs):
        super().get_context_data(**kwargs)
        request = self.request

        title = f'{application_name()} App Index'
        fan = current_fan(request.session)
        user_name = fan if fan is not None else 'Guest'
        context = add_base_context(request, {
            'title': title,
            'name': user_name,
        })

        return context


class BaseFilmsFormView(LoginRequiredMixin, FormView):
    SEARCH_KEY = 'search_text'
    template_name = None
    form_class = PickRating
    http_method_names = ['post']
    submit_name_prefix = None
    view = None
    success_view_name = None
    post_attendance = None
    film = None
    found_films = None

    def form_valid(self, form):
        search_text = form.cleaned_data[self.SEARCH_KEY]
        if search_text:
            self.search_title(search_text)
        else:
            self.update_rating(form)
        return super().form_valid(form)

    def form_invalid(self, form):
        self.view.unexpected_errors.extend(wrap_up_form_errors(form.errors))
        super().form_invalid(form)
        return self.clean_response()

    def get_success_url(self):
        errors = self.view.unexpected_errors
        fragment = '#top' if not self.film or errors else FragmentKeeper.fragment_code(self.film.film_id)
        return reverse(self.success_view_name) + fragment

    @staticmethod
    def clean_response():
        return HttpResponseRedirect(reverse('films:films'))

    def search_title(self, text):
        session = self.request.session
        initialize_log(session, action=f'Search "{text}"')
        festival = current_festival(session)
        found_films = []
        start_by_film = {}
        for film in Film.films.filter(festival=festival):
            start_pos = self.start_position_of_text(film, text)
            if start_pos is not None:
                found_films.append(film)
                start_by_film[film] = start_pos
                add_log(session, film.sort_title)
        if found_films:
            sorted_tuples = sorted([(f, s, f.sort_title) for f, s in start_by_film.items()], key=itemgetter(1, 2))
            BaseFilmsFormView.found_films = [f for f, s, t in sorted_tuples]
        else:
            add_log(session, f'No title found containing "{text}"')

    @staticmethod
    def start_position_of_text(film, text):
        re_search_text = re.compile(f'{text}')
        m = re_search_text.search(film.sort_title)
        return m.start() if m else None

    def update_rating(self, form):
        submitted_name = list(self.request.POST.keys())[-1]
        if submitted_name == self.SEARCH_KEY:
            return  # Search field committed while empty.
        if submitted_name is not None:
            pr_debug('start update', with_time=True)
            film_pk, rating_value = submitted_name.strip(self.submit_name_prefix).split('_')
            self.film = Film.films.get(id=film_pk)
            session = self.request.session
            fan = current_fan(session)
            form.update_rating(session, self.film, fan, rating_value, post_attendance=self.post_attendance)
            pr_debug('done update', with_time=True)
        else:
            self.view.unexpected_errors.append("Can't identify submit widget.")


class FilmsView(LoginRequiredMixin, View):
    """
    Film list with updatable ratings.
    """
    template_name = 'films/films.html'
    submit_name_prefix = 'list_'
    post_attendance = False
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
    class_tag = 'rating'
    highest_rating = FilmFanFilmRating.Rating.values[-1]
    short_threshold = timedelta(minutes=MAX_SHORT_MINUTES)
    description_by_film_id = {}
    fan_list = get_present_fans()
    fragment_keeper = None
    logged_in_fan = None
    festival = None
    selected_films = None
    festival_feature_films = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.filters = []
        self.shorts_filter = Filter('shorts')
        self.filters.append(self.shorts_filter)
        self.rated_filters = {}
        for fan in self.fan_list:
            self.rated_filters[fan] = Filter('rated', cookie_key=f'{fan}-rated')
            self.filters.append(self.rated_filters[fan])

    def dispatch(self, request, *args, **kwargs):
        session = self.request.session
        self.fragment_keeper = FragmentKeeper()

        # Initialize the filter cookies when necessary.
        for f in self.filters:
            f.init_cookie(session)

        # Ensure the film rating cache is initialized.
        if not PickRating.film_rating_cache:
            PickRating.film_rating_cache = FilmRatingCache(request.session, FilmsView.unexpected_errors)

        # Apply filters from url query part.
        for f in self.filters:
            f.handle_request(request)

        # Add the filters to the cache key.
        filter_dict = {}
        for f in self.filters:
            filter_dict[f.get_cookie_key()] = f.on(session)
        FilmRatingCache.set_filters(session, filter_dict)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        pr_debug('start', with_time=True)
        session = self.request.session
        self.logged_in_fan = current_fan(session)
        self.festival = current_festival(session)

        # Return the cache when valid.
        if PickRating.film_rating_cache.is_valid(session):
            pr_debug('done, cache is valid', with_time=True)
            return PickRating.film_rating_cache.get_film_rows(session)

        # Filter the films as requested.
        pr_debug('start filtered query', with_time=True)
        filter_kwargs = {'festival': self.festival}
        if self.shorts_filter.on(session):
            filter_kwargs['duration__gt'] = self.short_threshold
        self.selected_films = Film.films.filter(**filter_kwargs).order_by('seq_nr')
        self.festival_feature_films = copy.deepcopy(self.selected_films)
        for fan in self.fan_list:
            if self.rated_filters[fan].on(session):
                self.selected_films = self.selected_films.filter(
                    ~Exists(FilmFanFilmRating.film_ratings.filter(film=OuterRef('pk'), film_fan=fan))
                )

        # Read the descriptions.
        if not get_log(session):
            initialize_log(session, action='Read descriptions')
        film_info_file = self.festival.filminfo_file()
        try:
            with open(film_info_file, 'r', newline='') as csvfile:
                object_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
                self.description_by_film_id = {int(row[0]): row[1] for row in object_reader}
                add_log(session, f'{len(self.description_by_film_id)} descriptions found.')
        except FileNotFoundError as e:
            self.description_by_film_id = {}
            add_log(session, 'No descriptions file found.')

        # Set the fragment names.
        self.fragment_keeper.add_fragments(self.selected_films)

        # Fill the film rows.
        film_rows = [self.get_film_row(row_nr, film) for row_nr, film in enumerate(self.selected_films)]

        # Fill the cache.
        PickRating.film_rating_cache.set_film_rows(session, film_rows)

        pr_debug('done', with_time=True)
        return film_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        session = self.request.session
        super_context = super().get_context_data(**kwargs)
        film_count, rated_films_count, count_dicts = get_rating_statistics(session)
        new_context = {
            'title': self.title,
            'search_form': PickRating(),
            'fan_headers': self.get_fan_headers(),
            'feature_count': film_count,
            'rated_features_count': rated_films_count,
            'highest_rating': self.highest_rating,
            'eligible_counts': count_dicts,
            'short_threshold': self.short_threshold.total_seconds(),
            'display_shorts_href_filter': self.shorts_filter.get_href_filter(session),
            'display_shorts_action': self.shorts_filter.action(session),
            'found_films': BaseFilmsFormView.found_films,
            'action': refreshed_rating_action(session, self.class_tag),
            'unexpected_errors': FilmsView.unexpected_errors,
            'log': get_log(session)
        }
        unset_log(session)
        context = add_base_context(self.request, super_context | new_context)
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        FilmsView.unexpected_errors = []
        BaseFilmsFormView.found_films = None
        return response

    def get_film_row(self, row_nr, film):
        prefix = FilmsView.submit_name_prefix
        choices = FilmFanFilmRating.Rating.choices
        fan_ratings = get_fan_ratings(film, self.fan_list, self.logged_in_fan, prefix, choices,
                                      FilmsView.post_attendance)
        film_rating_row = {
            'film': film,
            'fragment_name': self.fragment_keeper.get_fragment_name(row_nr),
            'duration_str': film.duration_str(),
            'duration_seconds': film.duration.total_seconds(),
            'subsection': self.get_subsection(film),
            'section': None,
            'description': self.get_description(film),
            'fan_ratings': fan_ratings,
        }
        return film_rating_row

    @staticmethod
    def get_subsection(film):
        if not film.subsection:
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
        fan_headers = []
        for fan in self.fan_list:
            rated_filter = self.rated_filters[fan]
            fan_header = {
                'fan': fan,
                'href_filter': rated_filter.get_href_filter(session),
                'action': rated_filter.action(session),
            }
            fan_headers.append(fan_header)
        return fan_headers


class FilmsFormView(BaseFilmsFormView):
    view = FilmsView
    template_name = view.template_name
    submit_name_prefix = view.submit_name_prefix
    post_attendance = view.post_attendance
    success_view_name = 'films:films'


class VotesView(LoginRequiredMixin, View):
    template_name = 'films/votes.html'
    submit_name_prefix = 'votes_'
    post_attendance = True
    unexpected_errors = []

    @staticmethod
    def get(request, *args, **kwargs):
        view = VotesListView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = VotesFormView.as_view()
        return view(request, *args, **kwargs)


class VotesListView(LoginRequiredMixin, ListView):
    template_name = VotesView.template_name
    context_object_name = 'vote_rows'
    http_method_names = ['get']
    title = 'Film Votes List'
    class_tag = 'vote'
    fan_list = get_present_fans()
    fragment_keeper = None
    attended_films = []
    logged_in_fan = None
    festival = None

    def dispatch(self, request, *args, **kwargs):
        session = self.request.session
        self.festival = current_festival(session)
        self.logged_in_fan = current_fan(session)
        self.fragment_keeper = FragmentKeeper()
        VotesView.unexpected_errors = []

        # Read the films that were attended.
        self.set_attended_films()

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        selected_films = sorted(self.attended_films, key=attrgetter('seq_nr'))

        # Set the fragment names.
        self.fragment_keeper.add_fragments(selected_films)

        # Fill the vote rows.
        vote_rows = [self.get_vote_row(row_nr, film) for row_nr, film in enumerate(selected_films)]

        return vote_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        new_context = {
            'title': self.title,
            'fans': self.fan_list,
            'action': refreshed_rating_action(self.request.session, self.class_tag),
            'unexpected_errors': VotesView.unexpected_errors,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    def set_attended_films(self):
        screening_info_file = self.festival.screening_info_file()
        self.attended_films = []
        try:
            with open(screening_info_file, 'r', newline='') as csvfile:
                _ = csvfile.__next__()  # skip header
                screening_info_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
                film_id_index = 5
                attended_index = 8
                tickets_bought_index = 9
                for row in screening_info_reader:
                    if row[attended_index].split(',')[0] == 'WAAR' and row[tickets_bought_index] == 'WAAR':
                        film = self.get_film(row[film_id_index])
                        if film:
                            self.attended_films.append(film)
        except (FileNotFoundError, IndexError) as e:
            VotesView.unexpected_errors.append(e)

    def get_film(self, film_id):
        try:
            film = Film.films.get(festival=self.festival, film_id=film_id)
        except Film.DoesNotExist as e:
            film = None
        return film

    def get_vote_row(self, row_nr, film):
        prefix = VotesView.submit_name_prefix
        choices = FilmFanFilmVote.choices
        post_attendance = VotesView.post_attendance
        fan_votes = get_fan_ratings(film, self.fan_list, self.logged_in_fan, prefix, choices, post_attendance)
        vote_row = {
            'film': film,
            'duration_str': film.duration_str(),
            'reviewer': film.reviewer or '',
            'fan_votes': fan_votes,
            'fragment_name': self.fragment_keeper.get_fragment_name(row_nr),
        }
        return vote_row


class VotesFormView(BaseFilmsFormView):
    view = VotesView
    template_name = view.template_name
    submit_name_prefix = view.submit_name_prefix
    post_attendance = view.post_attendance
    success_view_name = 'films:votes'


class ResultsView(LoginRequiredMixin, DetailView):
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
        film_info_file = film.festival.filminfo_file()
        # with open(film_info_file, 'r') as stream:
        #     info = yaml.safe_load(stream)
        # description = info['description']
        try:
            with open(film_info_file, 'r', newline='') as csvfile:
                object_reader = csv.reader(csvfile, delimiter=';', quotechar='"')
                descriptions = [row[1] for row in object_reader if film.film_id == int(row[0])]
        except FileNotFoundError:
            descriptions = []
        description = descriptions[0] if descriptions else '-'
        return description


class ReviewersView(ListView):
    """
    Displays statistics of reviewers.
    Pre-attendance judgements ("ratings") are compared with post_attendance judgements ("votes").
    """
    template_name = 'films/reviewers.html'
    context_object_name = 'reviewer_rows'
    http_method_names = ['get']
    title = 'Reviewers Statistics'
    fan_list = get_present_fans()
    reviewed_films = None
    total_film_count = None
    unexpected_errors = []

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.judged_filter = Filter('not judged', filtered=True, action_true='Display all')

    def dispatch(self, request, *args, **kwargs):
        self.total_film_count = 0
        session = request.session

        # Initialize the filter cookie when necessary.
        self.judged_filter.init_cookie(session)

        # Apply the filter from url query part.
        self.judged_filter.handle_request(request)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        self.reviewed_films = Film.films.exclude(reviewer=None)
        session = self.request.session
        reviewers = set([film.reviewer for film in self.reviewed_films])
        reviewer_rows = self.get_reviewer_rows(reviewers)
        sort_key = 'reviewer' if self.judged_filter.off(session) else 'avg_discrepancy'
        return sorted(reviewer_rows, key=lambda r: r[sort_key])

    def get_context_data(self, *, object_list=None, **kwargs):
        super_context = super().get_context_data(**kwargs)
        session = self.request.session
        new_context = {
            'title': self.title,
            'fans': self.fan_list,
            'total_film_count': self.total_film_count,
            'judged_href_filter': self.judged_filter.get_href_filter(session),
            'judged_filter_action': self.judged_filter.action(session),
            'unexpected_errors': self.unexpected_errors,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    def get_reviewer_rows(self, reviewers):
        reviewer_rows = []
        for reviewer in reviewers:
            row = self.get_reviewer_row(reviewer)
            if row['display_reviewer']:
                reviewer_rows.append(row)
        return reviewer_rows

    def get_reviewer_row(self, reviewer):
        reviewed_films = [film for film in self.reviewed_films if film.reviewer == reviewer]
        film_count = len(reviewed_films)
        self.total_film_count += film_count
        fan_judgements, dropdown_rows = self.get_fan_judgements(reviewer)
        judged_count, avg_discrepancy = self.get_discrepancy_stats(fan_judgements)
        display_reviewer = judged_count or self.judged_filter.off(self.request.session)

        # Create a reviewer row dictionary.
        reviewer_row = {
            'reviewer': reviewer,
            'display_reviewer': display_reviewer,
            'film_count': film_count,
            'judged_count': judged_count,
            'avg_discrepancy': avg_discrepancy,
            'fan_judgements': fan_judgements,
            'dropdown_rows': dropdown_rows,
        }
        return reviewer_row

    def get_fan_judgements(self, reviewer):
        fan_judgements = []
        dropdown_rows = []
        for fan in self.fan_list:
            ratings = (FilmFanFilmRating.film_ratings
                       .filter(film__reviewer=reviewer, film_fan=fan)
                       .select_related('film'))
            rating_set = set([rating.film for rating in ratings])
            votes = (FilmFanFilmVote.film_votes
                     .filter(film__reviewer=reviewer, film_fan=fan)
                     .select_related('film'))
            vote_set = set([vote.film for vote in votes])
            judge_set = rating_set & vote_set

            discrepancies = []
            for film in sorted(judge_set, key=attrgetter('sort_title')):
                rating = fan_rating(fan, film)
                vote = fan_rating(fan, film, manager=FilmFanFilmVote.film_votes)
                discrepancy = rating.rating - vote.vote
                discrepancies.append(discrepancy)
                dropdown_row = {
                    'film': film.title,
                    'fan': fan,
                    'rating': rating.rating,
                    'vote': vote.vote,
                    'discrepancy': discrepancy,
                }
                dropdown_rows.append(dropdown_row)

            fan_judgement = {
                'fan': fan,
                'judged_count': len(judge_set),
                'judged_films': judge_set,
                'discrepancies': discrepancies,
                'min_discrepancy': min(discrepancies) if discrepancies else None,
                'max_discrepancy': max(discrepancies) if discrepancies else None,
                'avg_discrepancy': sum(discrepancies) / len(discrepancies) if discrepancies else None,
            }
            fan_judgements.append(fan_judgement)

        return fan_judgements, dropdown_rows

    @staticmethod
    def get_discrepancy_stats(fan_judgements):
        discrepancies = [j['discrepancies'] for j in fan_judgements]
        discr_list = []
        for discrepancy in discrepancies:
            discr_list += discrepancy
        discrepancy_count = len(discr_list)
        avg_discrepancy = sum(discr_list) / len(discr_list) if discr_list else 0
        return discrepancy_count, avg_discrepancy


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
    max_short_duration = timedelta(minutes=MAX_SHORT_MINUTES)
    feature_films = [film for film in films if film.duration > max_short_duration]
    eligible_ratings = FilmFanFilmRating.Rating.values[LOWEST_PLANNABLE_RATING:]
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


def get_fan_ratings(film, fan_list, logged_in_fan, submit_name_prefix, choices, post_attendance):
    film_ratings = []
    for fan in fan_list:
        # Set a rating string to display.
        rating_str = fan_rating_str(fan, film, post_attendance)

        # Get choices for this fan.
        choice_dict = [{
            'value': value,
            'rating_name': name,
            'submit_name': f'{submit_name_prefix}{film.id}_{value}'
        } for value, name in choices] if fan == logged_in_fan else []

        # Append a fan rating dictionary to the list.
        film_ratings.append({
            'fan': fan,
            'rating': rating_str,
            'choices': choice_dict
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
    if not film.subsection:
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
