import csv
import re
from datetime import timedelta
from operator import attrgetter, itemgetter

import yaml
from django.contrib.auth.mixins import LoginRequiredMixin
from django.db.models import Exists, OuterRef
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import FormView, DetailView, ListView, TemplateView

from authentication.models import FilmFan
from festival_planner.cache import FilmRatingCache, FILM_SUBMIT_PREFIX
from festival_planner.cookie import Filter, Cookie
from festival_planner.debug_tools import pr_debug, timed_method
from festival_planner.fragment_keeper import FilmFragmentKeeper
from festival_planner.screening_status_getter import ScreeningStatusGetter
from festival_planner.shared_template_referrer_view import SharedTemplateReferrerView
from festival_planner.tools import add_base_context, unset_log, wrap_up_form_errors, application_name, get_log, \
    initialize_log, add_log, CSV_DIALECT, get_submit_name, get_data_from_submit
from festivals.config import Config
from festivals.models import current_festival
from films.forms.film_forms import PickRating, UserForm, TitlesForm
from films.models import FilmFanFilmRating, Film, current_fan, get_judging_fans, fan_rating_str, \
    FilmFanFilmVote, fan_rating, UNRATED_STR, get_judgement_choices
from screenings.models import Attendance
from sections.models import Subsection, Section

CONSTANTS_CONFIG = Config().config['Constants']
MAX_SHORT_MINUTES = CONSTANTS_CONFIG['MaxShortMinutes']


class FilmsFinder:

    def __init__(self):
        self.found_films = None

    def search_title(self, session, text):
        initialize_log(session, action=f'Search "{text}"')
        festival = current_festival(session)
        self.found_films = []
        start_by_film = {}
        for film in Film.films.filter(festival=festival):
            start_pos = self.start_position_of_text(film, text)
            if start_pos is not None:
                self.found_films.append(film)
                start_by_film[film] = start_pos
                add_log(session, film.sort_title)
        if self.found_films:
            sorted_tuples = sorted([(f, s, f.sort_title) for f, s in start_by_film.items()], key=itemgetter(1, 2))
            self.found_films = [f for f, s, t in sorted_tuples]
        else:
            add_log(session, f'No title found containing "{text}"')

    @staticmethod
    def start_position_of_text(film, text):
        re_search_text = re.compile(f'{text.lower()}')
        m = re_search_text.search(film.sort_title)
        return m.start() if m else None


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
    films_finder = FilmsFinder()

    def form_valid(self, form):
        search_text = form.cleaned_data[self.SEARCH_KEY]
        if search_text:
            self.films_finder.search_title(self.request.session, search_text)
        else:
            self.update_rating(form)
        return super().form_valid(form)

    def form_invalid(self, form):
        self.view.unexpected_errors.extend(wrap_up_form_errors(form.errors))
        super().form_invalid(form)
        return self.clean_response()

    def get_success_url(self):
        errors = self.view.unexpected_errors
        fragment = '#top' if not self.film or errors else FilmFragmentKeeper.fragment_code(self.film)
        return reverse(self.success_view_name) + fragment

    @staticmethod
    def clean_response():
        return HttpResponseRedirect(reverse('films:films'))

    def update_rating(self, form):
        submitted_name = list(self.request.POST.keys())[-1]
        if submitted_name == self.SEARCH_KEY:
            return  # Search field committed while empty.
        if submitted_name is not None:
            pr_debug('start update', with_time=True)
            film_pk, rating_value = get_data_from_submit(self.submit_name_prefix, submitted_name)
            self.film = Film.films.get(id=film_pk)
            session = self.request.session
            fan = current_fan(session)
            form.update_rating(session, self.film, fan, rating_value, post_attendance=self.post_attendance)
            pr_debug('done update', with_time=True)
        else:
            self.view.unexpected_errors.append("Can't identify submit widget.")


class FilmsView(SharedTemplateReferrerView):
    """
    Film list with updatable ratings.
    """
    template_name = 'films/films.html'
    submit_name_prefix = FILM_SUBMIT_PREFIX
    post_attendance = False
    unexpected_errors = []

    def __init__(self):
        super().__init__()
        self.list_view = FilmsListView
        self.form_view = FilmsFormView


class FilmsListView(LoginRequiredMixin, ListView):
    template_name = FilmsView.template_name
    context_object_name = 'film_rows'
    http_method_names = ['get']
    object_list = None
    title = 'Film Rating List'
    class_tag = 'rating'
    highest_rating = FilmFanFilmRating.Rating.values[-1]
    eligible_ratings = FilmFanFilmRating.get_eligible_ratings()
    short_threshold = timedelta(minutes=MAX_SHORT_MINUTES)
    fragment_keeper = None
    logged_in_fan = None
    festival = None
    selected_films = None

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.subsection_filters = None
        self.section_filters = None
        self.rated_filters = None
        self.shorts_filter = None
        self.filters = None
        self.description_by_film_id = {}
        self.festival_feature_films = None
        self.section_list = Section.sections.all()
        self.subsection_list = Subsection.subsections.all()
        self.fan_list = get_judging_fans()

    @timed_method
    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.festival = current_festival(request.session)

        # Save the list of festival feature films.
        filter_kwargs = {'festival': self.festival, 'duration__gt': self.short_threshold}
        self.festival_feature_films = Film.films.filter(**filter_kwargs)

        # Define the filters.
        self._setup_filters()

    def dispatch(self, request, *args, **kwargs):
        session = self.request.session
        self.fragment_keeper = FilmFragmentKeeper()

        # Ensure the film rating cache is initialized.
        if not PickRating.film_rating_cache:
            PickRating.film_rating_cache = FilmRatingCache(request.session, FilmsView.unexpected_errors)

        # Apply filters from url query part.
        for f in self.filters:
            f.handle_get_request(request)

        # Add the filters to the cache key.
        filter_dict = {}
        for f in self.filters:
            filter_dict[f.get_cookie_key()] = f.on(session)
        FilmRatingCache.set_filters(session, filter_dict)

        return super().dispatch(request, *args, **kwargs)

    @timed_method
    def get_queryset(self):
        session = self.request.session
        self.logged_in_fan = current_fan(session)

        # Return the cache when valid.
        if PickRating.film_rating_cache.is_valid(session):
            pr_debug('done, cache is valid', with_time=True)
            return PickRating.film_rating_cache.get_film_rows(session)

        # Filter the films as requested.
        self._filter_films(session)

        # Read the descriptions.
        self._read_film_descriptions(session)

        # Set the fragment names.
        self.fragment_keeper.add_fragments(self.selected_films)

        # Fill the film rows.
        film_rows = [self._get_film_row(row_nr, film) for row_nr, film in enumerate(self.selected_films)]

        # Fill the cache.
        PickRating.film_rating_cache.set_film_rows(session, film_rows)

        return film_rows

    def get_context_data(self, *, object_list=None, **kwargs):
        session = self.request.session
        super_context = super().get_context_data(**kwargs)
        film_count, rated_films_count, eligible_rating_counts = self._get_stats_for_ratings()
        new_context = {
            'title': self.title,
            'search_form': PickRating(),
            'fan_headers': self._get_fan_headers(),
            'feature_count': film_count,
            'rated_features_count': rated_films_count,
            'highest_rating': self.highest_rating,
            'eligible_counts': eligible_rating_counts,
            'short_threshold': self.short_threshold.total_seconds(),
            'display_shorts_href_filter': self.shorts_filter.get_href_filter(session),
            'display_shorts_action': self.shorts_filter.action(session),
            'display_all_subsections_query': self._get_query_string_to_select_all_subsections(session),
            'found_films': BaseFilmsFormView.films_finder.found_films,
            'action': PickRating.rating_action_by_field[self.class_tag].get_refreshed_action(session),
            'unexpected_errors': FilmsView.unexpected_errors,
            'log': get_log(session)
        }
        unset_log(session)
        context = add_base_context(self.request, super_context | new_context)
        return context

    def render_to_response(self, context, **response_kwargs):
        response = super().render_to_response(context, **response_kwargs)
        FilmsView.unexpected_errors = []
        BaseFilmsFormView.films_finder.found_films = None
        return response

    def _setup_filters(self):
        self.filters = []
        self.shorts_filter = Filter('shorts')
        self.filters.append(self.shorts_filter)
        self.rated_filters = {}
        for fan in self.fan_list:
            self.rated_filters[fan] = Filter('rated', cookie_key=f'{fan}-rated')
            self.filters.append(self.rated_filters[fan])
        self.section_filters = {}
        for section in self.section_list:
            self.section_filters[section] = Filter('section',
                                                   cookie_key=f'section-{section.id}',
                                                   action_false='Select section',
                                                   action_true='Remove filter')
            self.filters.append(self.section_filters[section])
        self.subsection_filters = {}
        for subsection in self.subsection_list:
            self.subsection_filters[subsection] = Filter('subsection',
                                                         cookie_key=f'subsection-{subsection.id}',
                                                         action_false='Select subsection',
                                                         action_true='Remove filter')
            self.filters.append(self.subsection_filters[subsection])

    @timed_method
    def _filter_films(self, session):
        filter_kwargs = {'festival': self.festival}
        if self.shorts_filter.on(session):
            filter_kwargs['duration__gt'] = self.short_threshold
        for section in self.section_list:
            if self.section_filters[section].on(session):
                filter_kwargs['subsection__section'] = section
        for subsection in self.subsection_list:
            if self.subsection_filters[subsection].on(session):
                filter_kwargs['subsection'] = subsection
        self.selected_films = Film.films.filter(**filter_kwargs).order_by('sort_title')
        for fan in self.fan_list:
            if self.rated_filters[fan].on(session):
                self.selected_films = self.selected_films.filter(
                    ~Exists(FilmFanFilmRating.film_ratings.filter(film=OuterRef('pk'), film_fan=fan))
                )

    @staticmethod
    def _get_query_string_to_select_all_subsections(session):
        active_keys = FilmRatingCache.get_active_filter_keys(session)
        section_keys = [k for k in active_keys if k.startswith('subsection-') or k.startswith('section-')]
        query_string = Filter.get_display_query_from_keys(section_keys)
        return query_string

    def _read_film_descriptions(self, session):
        if not get_log(session):
            initialize_log(session, action='Read descriptions')
        film_info_file = self.festival.filminfo_csv_file()
        try:
            with open(film_info_file, 'r', newline='') as csvfile:
                object_reader = csv.reader(csvfile, dialect=CSV_DIALECT)
                self.description_by_film_id = {int(row[0]): row[1] for row in object_reader}
                add_log(session, f'{len(self.description_by_film_id)} descriptions found.')
        except FileNotFoundError as e:
            self.description_by_film_id = {}
            add_log(session, f'{e}: No descriptions file found.')

    def _get_film_row(self, row_nr, film):
        prefix = FilmsView.submit_name_prefix
        fan_ratings = get_fan_ratings(film, self.fan_list, self.logged_in_fan, prefix, FilmsView.post_attendance)
        film_rating_row = {
            'film': film,
            'fragment_name': self.fragment_keeper.get_fragment_name(row_nr),
            'duration_str': film.duration_str(),
            'duration_seconds': film.duration.total_seconds(),
            'subsection': film.subsection,
            'subsection_filter': self._get_subsection_filter(film.subsection),
            'section_filter': self._get_section_filter(film.subsection),
            'description': self._get_description(film),
            'fan_ratings': fan_ratings,
        }

        return film_rating_row

    @staticmethod
    def _get_stats_for_one_rating(base_rating, count_by_rating, film_count, rated_films_count):
        counts = [count for r, count in count_by_rating.items() if r >= base_rating]
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

    def _get_count_by_rating(self, film_rating_queryset_tuples):
        count_by_eligible_rating = {}
        for film, rating_queryset in film_rating_queryset_tuples:
            best_rating = max([r.rating for r in rating_queryset])
            if best_rating in self.eligible_ratings:
                try:
                    count_by_eligible_rating[best_rating] += 1
                except KeyError:
                    count_by_eligible_rating[best_rating] = 1
        return count_by_eligible_rating

    def _get_stats_for_ratings(self):
        # Get the feature films of this festival.
        feature_films = self.festival_feature_films
        film_count = len(feature_films)

        # Filter out the data with eligible ratings.
        manager = FilmFanFilmRating.film_ratings
        dirty_film_rating_sets = [(f, manager.filter(film=f, rating__gt=0)) for f in feature_films]
        film_rating_sets = [(f, ratings) for f, ratings in dirty_film_rating_sets if ratings]
        rated_films_count = len(film_rating_sets)
        count_by_eligible_rating = self._get_count_by_rating(film_rating_sets)

        # Find the statistics for all eligible ratings.
        eligible_rating_counts = []
        for eligible_rating in self.eligible_ratings:
            eligible_rating_counts.append(self._get_stats_for_one_rating(eligible_rating,
                                                                         count_by_eligible_rating,
                                                                         film_count,
                                                                         rated_films_count))

        return film_count, rated_films_count, eligible_rating_counts

    def _get_subsection_filter(self, subsection):
        subsection_row = None
        if subsection:
            session = self.request.session
            subsection_filter = self.subsection_filters[subsection]
            subsection_row = {
                'subsection': subsection,
                'href_filter': subsection_filter.get_href_filter(session),
                'action': subsection_filter.action(session),
            }
        return subsection_row

    def _get_section_filter(self, subsection):
        section_row = None
        if subsection:
            session = self.request.session
            section = subsection.section
            section_filter = self.section_filters[section]
            subsection_filter = self.subsection_filters[subsection]
            extra_filters = [subsection_filter] if subsection_filter.on(session) else []
            href_filter = section_filter.get_href_filter(session, extra_filters=extra_filters)
            section_row = {
                'section': section,
                'href_filter': href_filter,
                'action': section_filter.action(session),
            }
        return section_row

    def _get_description(self, film):
        try:
            description = self.description_by_film_id[film.film_id]
        except KeyError:
            description = None
        return description

    def _get_fan_headers(self):
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


class VotesView(SharedTemplateReferrerView):
    template_name = 'films/votes.html'
    submit_name_prefix = 'votes_'
    post_attendance = True
    unexpected_errors = []

    def __init__(self):
        super().__init__()
        self.list_view = VotesListView
        self.form_view = VotesFormView


class VotesListView(LoginRequiredMixin, ListView):
    template_name = VotesView.template_name
    context_object_name = 'vote_rows'
    http_method_names = ['get']
    title = 'Film Votes List'
    class_tag = 'vote'
    fan_list = get_judging_fans()
    fragment_keeper = None
    attended_films = []
    logged_in_fan = None
    festival = None

    def dispatch(self, request, *args, **kwargs):
        session = self.request.session
        self.festival = current_festival(session)
        self.logged_in_fan = current_fan(session)
        self.fragment_keeper = FilmFragmentKeeper()
        VotesView.unexpected_errors = []

        # Read the films that were attended.
        self._set_attended_films()

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
            'action': PickRating.rating_action_by_field[self.class_tag].get_refreshed_action(self.request.session),
            'unexpected_errors': VotesView.unexpected_errors,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    def _set_attended_films(self):
        festival = self.festival
        fan = self.logged_in_fan
        manager = Attendance.attendances
        attendances = manager.filter(screening__film__festival=festival, fan=fan)
        self.attended_films = list({a.screening.film for a in attendances})

    def get_film(self, film_id):
        try:
            film = Film.films.get(festival=self.festival, film_id=film_id)
        except Film.DoesNotExist:
            film = None
        return film

    def get_vote_row(self, row_nr, film):
        prefix = VotesView.submit_name_prefix
        post_attendance = VotesView.post_attendance
        fan_votes = get_fan_ratings(film, self.fan_list, self.logged_in_fan, prefix, post_attendance)
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


class FilmDetailView(LoginRequiredMixin, DetailView):
    """
    Define generic view classes.
    """
    model = Film
    template_name = 'films/details.html'
    http_method_names = ['get', 'post']
    submit_name_prefix = 'results_'
    unexpected_error = ''

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
        ScreeningStatusGetter.handle_screening_get_request(request)

        if request.method == 'POST':
            submitted_name = list(request.POST.keys())[-1]
            session = self.request.session
            if submitted_name is not None:
                film_pk, rating_value = get_data_from_submit(self.submit_name_prefix, submitted_name)
                film = Film.films.get(id=film_pk)
                PickRating.update_rating(session, film, current_fan(session), rating_value)
                return HttpResponseRedirect(reverse('films:details', args=(film_pk,)))
            else:
                self.unexpected_error = "Can't identify submit widget."

        unset_log(request.session)
        return response

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        film = self.object
        metadata, combi_data, screened_data = self._get_film_info(film)
        session = self.request.session
        festival = current_festival(session)
        combi_films = [Film.films.get(film_id=d['film_id'], festival=festival) for d in combi_data]
        screened_films = [Film.films.get(film_id=d['film_id'], festival=festival) for d in screened_data]
        selected_screening = ScreeningStatusGetter.get_selected_screening(self.request)
        films_for_screenings = combi_films or [film]
        fans = get_judging_fans()
        logged_in_fan = current_fan(session)
        fan_rows = get_fan_props_list(film, fans, logged_in_fan, self.submit_name_prefix)
        in_cache = film_is_in_cache(session, film)
        new_context = {
            'title': 'Film Rating Results',
            'description': self.get_description(film),
            'screened_films': screened_films,
            'combination_films': combi_films,
            'metadata': metadata,
            'fragment': FilmFragmentKeeper.fragment_code(film),
            'film_in_cache': in_cache,
            'no_cache': in_cache is None,
            'display_all_query': in_cache is None or self.get_query_string_to_display_all(session),
            'fan_rows': fan_rows,
            'film_title': film.title,
            'film_screening_props_list': get_filmscreening_props_list(session, films_for_screenings),
            'screening': selected_screening,
            'unexpected_error': self.unexpected_error,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    @staticmethod
    def get_description(film):
        film_info_file = film.festival.filminfo_csv_file()
        try:
            with open(film_info_file, 'r', newline='') as csvfile:
                object_reader = csv.reader(csvfile, dialect=CSV_DIALECT)
                descriptions = [row[1] for row in object_reader if film.film_id == int(row[0])]
        except FileNotFoundError:
            description = None
        else:
            try:
                description = descriptions[0].strip() or None
            except IndexError:
                description = None
        return description

    @staticmethod
    def _get_film_info(film):
        combi_data = []
        screened_data = []
        film_metadata = {}
        filminfo_yaml_file = film.festival.filminfo_yaml_file()
        try:
            with open(filminfo_yaml_file, 'r') as stream:
                yaml_object = yaml.safe_load(stream)
        except FileNotFoundError:
            pass
        else:
            try:
                """
                TODO: Read this information for as much as reasonable festivals.
                """
                combi_dict = yaml_object['combinations']
                combination_films_by_film_id = {i: l for i, l in combi_dict.items()}
                screened_dict = yaml_object['screened_films']
                screened_films_by_film_id = {i: l for i, l in screened_dict.items()}
                metadata_dict = yaml_object['metadata']
                metadata_by_film_id = {i: metadata for i, metadata in metadata_dict.items()}
                combi_data = combination_films_by_film_id[film.film_id]
                screened_data = screened_films_by_film_id[film.film_id]
                film_metadata = metadata_by_film_id[film.film_id]
            except KeyError:
                combi_data = []
                screened_data = []
                film_metadata = {}
        metadata = [{'key': k, 'value': v} for k, v in film_metadata.items()]
        film_info = metadata, combi_data, screened_data
        return film_info

    @staticmethod
    def get_query_string_to_display_all(session):
        """
        Set up an HTML query as to switch off all filters.
        """
        filter_keys = FilmRatingCache.get_active_filter_keys(session)
        display_all_query = Filter.get_display_query_from_keys(filter_keys)
        return display_all_query


class ReviewersView(ListView):
    """
    Displays statistics of reviewers.
    Pre-attendance judgements ("ratings") are compared with post_attendance judgements ("votes").
    """
    template_name = 'films/reviewers.html'
    context_object_name = 'reviewer_rows'
    http_method_names = ['get']
    title = 'Reviewers Statistics'
    fan_list = None
    judged_filter = Filter('not judged', filtered=True, action_true='Display all')
    festival_filter = Filter('other festivals', filtered=True,
                             action_true='All festivals', action_false='Current festival')
    reviewed_films = None
    total_film_count = None
    unexpected_errors = []

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.fan_list = get_judging_fans()

    def dispatch(self, request, *args, **kwargs):
        self.total_film_count = 0

        # Apply the filter from url query part.
        self.judged_filter.handle_get_request(request)
        self.festival_filter.handle_get_request(request)

        return super().dispatch(request, *args, **kwargs)

    def get_queryset(self):
        session = self.request.session
        festival = current_festival(session)
        self.reviewed_films = Film.films.exclude(reviewer=None)
        if self.festival_filter.on(session):
            self.reviewed_films = self.reviewed_films.filter(festival=festival)
        reviewers = set([film.reviewer for film in self.reviewed_films])
        reviewer_rows = self._get_reviewer_rows(reviewers)
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
            'festival_href_filter': self.festival_filter.get_href_filter(session),
            'festival_filter_action': self.festival_filter.action(session),
            'festival_filter_label': self.festival_filter.label(session),
            'unexpected_errors': self.unexpected_errors,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    def _get_reviewer_rows(self, reviewers):
        reviewer_rows = []
        for reviewer in reviewers:
            row = self._get_reviewer_row(reviewer)
            if row['display_reviewer']:
                reviewer_rows.append(row)
        return reviewer_rows

    def _get_reviewer_row(self, reviewer):
        reviewed_films = [film for film in self.reviewed_films if film.reviewer == reviewer]
        film_count = len(reviewed_films)
        self.total_film_count += film_count
        fan_judgements, dropdown_rows = self._get_fan_judgements(reviewer)
        judged_count, avg_discrepancy = self._get_discrepancy_stats(fan_judgements)
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

    def _get_fan_judgements(self, reviewer):
        fan_judgements = []
        dropdown_rows = []
        for fan in self.fan_list:
            judge_set = self._get_fan_judge_set(reviewer, fan)

            discrepancies = []
            for film in sorted(judge_set, key=attrgetter('sort_title')):
                rating = fan_rating(fan, film)
                vote = fan_rating(fan, film, manager=FilmFanFilmVote.film_votes)
                discrepancy = rating.rating - vote.vote
                discrepancies.append(discrepancy)
                dropdown_row = {
                    'film': film.title,
                    'festival': str(film.festival),
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
    def _get_discrepancy_stats(fan_judgements):
        discrepancies = [j['discrepancies'] for j in fan_judgements]
        discr_list = []
        for discrepancy in discrepancies:
            discr_list += discrepancy
        discrepancy_count = len(discr_list)
        avg_discrepancy = sum(discr_list) / len(discr_list) if discr_list else 0
        return discrepancy_count, avg_discrepancy

    def _get_fan_judge_set(self, reviewer, fan):
        filter_kwargs = {'film__in': self.reviewed_films, 'film__reviewer': reviewer, 'film_fan': fan}
        ratings = (FilmFanFilmRating.film_ratings
                   .filter(**filter_kwargs)
                   .select_related('film'))
        rating_set = set([rating.film for rating in ratings])
        votes = (FilmFanFilmVote.film_votes
                 .filter(**filter_kwargs)
                 .select_related('film'))
        vote_set = set([vote.film for vote in votes])
        judge_set = rating_set & vote_set
        return judge_set


class TitlesView(SharedTemplateReferrerView):
    """
    Refer requests concerning alternative titles of a film.
    """
    template_name = 'films/titles.html'
    films_finder = FilmsFinder()
    submit_prefix = 'titles_'
    link_submit_name = 'link'
    unlink_submit_name = 'unlink'
    unexpected_errors = []
    main_title_film = None

    def __init__(self):
        super().__init__()
        self.list_view = TitlesDetailView
        self.form_view = TitlesFormView


class TitlesDetailView(LoginRequiredMixin, DetailView):
    model = Film
    template_name = TitlesView.template_name
    http_method_names = ['get']
    view = TitlesView

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data()
        session = self.request.session
        self.view.main_title_film = self.object
        film = self.object
        in_cache = film_is_in_cache(session, film)
        alt_title_films = self._get_alt_title_films(session, film)
        new_context = {
            'title': 'Manage alternative titles',
            'film': film,
            'fragment': FilmFragmentKeeper.fragment_code(film),
            'film_in_cache': in_cache,
            'no_cache': in_cache is None,
            'search_form': TitlesForm(),
            'found_props': self._get_found_props(),
            'alt_title_films': alt_title_films,
            'alt_props': self._get_alt_props(alt_title_films),
            'form_errors': self.view.unexpected_errors,
            'log': get_log(session),
        }
        self.view.unexpected_errors = []
        unset_log(session)
        context = add_base_context(self.request, super_context | new_context)
        return context

    def _get_found_props(self):
        found_files = self.view.films_finder.found_films or []
        found_props = [{
            'film': film,
            'submit_name': get_submit_name(self.view.submit_prefix, self.view.link_submit_name, film.id)
        } for film in found_files]
        return found_props

    @staticmethod
    def _get_alt_title_films(session, main_title_film):
        festival = current_festival(session)
        alt_title_films = Film.films.filter(festival=festival, main_title=main_title_film)
        return alt_title_films

    def _get_alt_props(self, alt_title_films):
        alt_props = [{
            'alt_film': film,
            'submit_name': get_submit_name(self.view.submit_prefix, self.view.unlink_submit_name, film.id),
        } for film in alt_title_films]
        return alt_props


class TitlesFormView(LoginRequiredMixin, FormView):
    template_name = TitlesView.template_name
    form_class = TitlesForm
    http_method_names = ['post']
    view = TitlesView

    def form_valid(self, form):
        search_text = form.cleaned_data[BaseFilmsFormView.SEARCH_KEY]
        if search_text:
            TitlesView.films_finder.search_title(self.request.session, search_text)
        else:
            film_by_operation = {
                self.view.link_submit_name: self.view.main_title_film,
                self.view.unlink_submit_name: None,
            }
            submit_name = list(self.request.POST.keys())[-1]
            operation, film_id_str = get_data_from_submit(self.view.submit_prefix, submit_name)
            alternative_title_film_id = int(film_id_str)
            film_arg = film_by_operation[operation]
            form.update_main_title(alternative_title_film_id, film_arg)
        return super().form_valid(form)

    def form_invalid(self, form):
        session = self.request.session
        if not get_log(session):
            initialize_log(session, action='Search alternative title')
        self.view.unexpected_errors.extend(wrap_up_form_errors(form.errors))
        self.view.unexpected_errors.append(f'Invalid search terms: {self.request.POST["search_text"]}')

        super().form_invalid(form)
        return HttpResponseRedirect(self.get_success_url())

    def get_success_url(self):
        return reverse('films:titles', args=[TitlesView.main_title_film.pk])


def get_filmscreening_props_list(session, films):
    filmscreening_props_list = []
    for film in films:
        filmscreening_props = ScreeningStatusGetter.get_filmscreening_props(session, film)
        filmscreening_props_item = {
            'props': filmscreening_props,
            'title': film.title,
        }
        filmscreening_props_list.append(filmscreening_props_item)
    return filmscreening_props_list


def film_is_in_cache(session, film):
    """
    Returns whether the current film is in cache or None if no cache exists.
    """
    try:
        film_rows = PickRating.film_rating_cache.get_film_rows(session)
    except AttributeError:
        return None
    if not film_rows:
        return None
    return film in [row['film'] for row in film_rows]


def film_fan(request):
    """
    Film fan switching view.
    """
    # Preset some parameters.
    title = 'Film Fans'
    form = UserForm(initial={'current_fan': current_fan(request.session)}, auto_id=False)
    session = request.session
    next_cookie = Cookie('next')

    # Check the request.
    match request.method:
        case 'GET':
            next_cookie.handle_get_request(request)
        case 'POST':
            form = UserForm(request.POST)
            if form.is_valid():
                # Switch fan as indicated.
                selected_fan = form.cleaned_data['selected_fan']
                fan = FilmFan.film_fans.get(name=selected_fan)
                fan.switch_current(session)

                # Redirect to calling page.
                redirect_path = next_cookie.get(session)
                next_cookie.remove(session)
                return HttpResponseRedirect(redirect_path or reverse('films:index'))

    # Construct the context.
    context = add_base_context(request, {
        'title': title,
        'form': form,
    })

    return render(request, 'films/film_fan.html', context)


def get_fan_ratings(film, fan_list, logged_in_fan, submit_name_prefix, post_attendance=False):
    film_rating_props = []
    choices = get_judgement_choices(post_attendance)
    for fan in fan_list:
        # Set a rating string to display.
        rating_str = fan_rating_str(fan, film, post_attendance)

        # Get choices for this fan.
        choice_props = [{
            'display_value': f'{value:2d}  {name}',
            'submit_name': get_submit_name(submit_name_prefix, film.id, value),
            'disabled': value == (0 if rating_str == UNRATED_STR else int(rating_str)),
        } for value, name in choices] if fan == logged_in_fan else []

        # Append a fan rating dictionary to the list.
        film_rating_props.append({
            'fan': fan,
            'rating_str': rating_str,
            'choices': choice_props
        })
    return film_rating_props


def get_fan_props_list(film, fans, logged_in_fan, submit_name_prefix):
    fan_props_list = get_fan_ratings(film, fans, logged_in_fan, submit_name_prefix)
    for fan_props in fan_props_list:
        rating_str = fan_props['rating_str']
        rating = int(rating_str) if rating_str != UNRATED_STR else 0
        fan_props['rating_label'] = FilmFanFilmRating.Rating(rating).label
    return fan_props_list


def get_fan_choices(submit_name_prefix, film, fan, logged_in_fan, post_attendance=False):
    """Get the rating choices if this fan is the current fan."""

    rating_str = fan_rating_str(fan, film, post_attendance)
    choices = get_judgement_choices(post_attendance)
    choice_props = [{
        'display_value': f'{value:2d}  {name}',
        'submit_name': get_submit_name(submit_name_prefix, film.id, value),
        'disabled': value == (0 if rating_str == UNRATED_STR else int(rating_str)),
    } for value, name in choices] if fan == logged_in_fan else []

    return choice_props
