import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import generic
from django.views.generic import FormView

from FilmRatings.tools import unset_log, add_base_context, get_log, wrap_up_form_errors
from festivals.config import Config
from festivals.models import current_festival, Festival
from film_list.forms.model_forms import Rating, User
from film_list.forms.unbound_forms import PickRating, SaveRatingsForm
from film_list.models import Film, FilmFan, FilmFanFilmRating, current_fan, get_rating_name, get_present_fans
from loader.views import file_record_count
from sections.models import Subsection


# Define generic view classes.
class ResultsView(generic.DetailView):
    model = Film
    template_name = 'film_list/results.html'
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
                update_rating(session, film, current_fan(session), rating_value)

                return HttpResponseRedirect(reverse('film_list:results', args=(film_pk,)))
            else:
                self.unexpected_error = "Can't identify submit widget."

        unset_log(request.session)
        return response


class SaveView(LoginRequiredMixin, FormView):
    model = Festival
    template_name = 'film_list/save.html'
    form_class = SaveRatingsForm
    success_url = '/film_list/film_list/'

    def get_context_data(self, **kwargs):
        session = self.request.session
        festival = current_festival(session)
        festival_items = {
            'festival': festival,
            'film_count': len(Film.films.filter(festival=festival)),
            'film_count_on_file': file_record_count(festival.films_file, has_header=True),
            'rating_count': len(FilmFanFilmRating.fan_ratings.filter(film__festival=festival)),
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


# General index page.
def index(request):

    # Set-up parameters.
    title = 'Film List App Index'
    current_time = datetime.datetime.now()
    time_string = current_time.strftime('%H:%M:%S')
    weekday_number = int(current_time.strftime('%w')) + 1
    fan = current_fan(request.session)
    user_name = fan if fan is not None else "Guest"

    # Unset load results cookie.
    unset_log(request.session)

    # Construct the parameters.
    context = add_base_context(request, {
        "title": title,
        "hour": time_string,
        "name": user_name,
        "weekdays": ['zo', 'ma', 'di', 'wo', 'do', 'vr', 'za'],
        "weekday_number": weekday_number,
    })

    return render(request, "film_list/index.html", context)


# Film fan switching view.
def film_fan(request):

    # Preset some parameters.
    title = 'Film Fans'

    # Check the request.
    if request.method == 'POST':
        form = User(request.POST)
        if form.is_valid():
            selected_fan = form.cleaned_data['selected_fan']
            fan = FilmFan.film_fans.get(name=selected_fan)
            fan.switch_current(request.session)
            return HttpResponseRedirect(reverse('film_list:index'))
    else:
        form = User(initial={'current_fan': current_fan(request.session)}, auto_id=False)

    # Construct the context.
    context = add_base_context(request, {
        'title': title,
        'form': form,
    })

    return render(request, 'film_list/film_fan.html', context)


# Film ratings view.
@login_required
def film_list(request):

    # Initialize.
    title = 'Film Rating List'
    submit_name_prefix = 'list_'
    config = Config().config
    max_short_minutes = config['Constants']['MaxShortMinutes']
    session = request.session
    logged_in_fan = current_fan(session)
    festival = current_festival(session)
    films = Film.films.filter(festival=festival).order_by('seq_nr')
    film_count, rated_films_count, count_dicts = get_rating_statistic(festival, films)
    fan_list = get_present_fans()
    highest_rating = FilmFanFilmRating.Rating.values[-1]

    # Get the table rows.
    film_list_rows = [{
        'film': film,
        'duration_str': film.duration_str(),
        'duration_seconds': film.duration.total_seconds(),
        'subsection': get_subsection(film),
        'section': None,
        'fan_ratings': get_fan_ratings(film, fan_list, logged_in_fan, submit_name_prefix),
    } for film in films]

    # Construct the context.
    context = add_base_context(request, {
        'title': title,
        'fans': fan_list,
        'feature_count': film_count,
        'rated_features_count': rated_films_count,
        'highest_rating': highest_rating,
        'eligible_counts': count_dicts,
        'short_threshold': datetime.timedelta(minutes=max_short_minutes).total_seconds(),
        'film_list_rows': film_list_rows,
    })
    refresh_rating_action(session, context)

    # Check the request.
    if request.method == 'POST':
        unset_log(session)
        form = PickRating(request.POST)
        if form.is_valid():
            submitted_name = list(request.POST.keys())[-1]
            if submitted_name is not None:
                [film_pk, rating_value] = submitted_name.strip(submit_name_prefix).split('_')
                film = Film.films.get(id=film_pk)
                update_rating(session, film, logged_in_fan, rating_value)

                return HttpResponseRedirect(reverse('film_list:film_list'))
            else:
                context['unexpected_errors'] = ["Can't identify submit widget."]
        else:
            context['unexpected_errors'] = wrap_up_form_errors(form.errors)

    context['log'] = get_log(session)
    return render(request, "film_list/film_list.html", context)


def get_rating_statistic(festival, films):

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
    max_short_duration = datetime.timedelta(minutes=max_short_minutes)
    lowest_plannable_rating = config['Constants']['LowestPlannableRating']
    feature_films = [film for film in films if film.duration > max_short_duration]
    eligible_ratings = FilmFanFilmRating.Rating.values[lowest_plannable_rating:]
    film_count = len(feature_films)

    # Filter out the data with eligible ratings.
    rated_films_count = 0
    count_by_eligible_rating = {}
    for feature_film in feature_films:
        rating_set = FilmFanFilmRating.fan_ratings.filter(film=feature_film, rating__gt=0)
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
    fan_ratings = []
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
        fan_ratings.append({
            'fan': fan,
            'rating': rating_str,
            'choices': choices
        })
    return fan_ratings


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


def update_rating(session, film, fan, rating_value):
    old_rating_str = fan.fan_rating_str(film)
    new_rating, created = FilmFanFilmRating.fan_ratings.update_or_create(
        film=film,
        film_fan=fan,
        defaults={'rating': rating_value},
    )
    zero_ratings = FilmFanFilmRating.fan_ratings.filter(film=film, film_fan=fan, rating=0)
    if len(zero_ratings) > 0:
        zero_ratings.delete()
    init_rating_action(session, old_rating_str, new_rating)


def init_rating_action(session, old_rating_str, new_rating):
    new_rating_name = get_rating_name(new_rating.rating)
    rating_action = {
        'fan': str(current_fan(session)),
        'old_rating': old_rating_str,
        'new_rating': str(new_rating.rating),
        'new_rating_name': new_rating_name,
        'rated_film': str(new_rating.film),
        'rated_film_id': new_rating.film.id,
        'action_time': datetime.datetime.now().isoformat(),
    }
    session[rating_action_key(session)] = rating_action


def refresh_rating_action(session, context):
    key = rating_action_key(session)
    if key in session:
        action = session[key]
        context['action'] = action
        context['action']['action_time'] = datetime.datetime.fromisoformat(action['action_time'])


def rating_action_key(session):
    return f'rating_action_{current_festival(session).id}'


# rating picker view.
@login_required
def rating(request, film_pk):

    # Preset some parameters.
    title = "Rating Picker"
    film = get_object_or_404(Film, id=film_pk)
    fan = current_fan(request.session)

    # Check the request.
    if request.method == 'POST':
        form = Rating(request.POST)
        if form.is_valid():
            selected_rating = form.cleaned_data['fan_rating']
            update_rating(request.session, film, fan, selected_rating)
            return HttpResponseRedirect(reverse('film_list:results', args=[film_pk]))
    else:
        try:
            current_rating = FilmFanFilmRating.fan_ratings.get(film=film, film_fan=fan)
        except FilmFanFilmRating.DoesNotExist:
            form = Rating()
        else:
            form = Rating(initial={'fan_rating': current_rating.rating}, auto_id=False)

    # Construct the context.
    context = add_base_context(request, {
        'title': title,
        'film': film,
        'form': form,
    })

    return render(request, 'film_list/rating.html', context)
