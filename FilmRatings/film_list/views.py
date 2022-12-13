import datetime

from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import generic
from django.views.generic import FormView

from FilmRatings.tools import unset_log, add_base_context, get_log, wrap_up_form_errors
from festivals.models import current_festival, Festival
from film_list.forms.model_forms import Rating, User
from film_list.forms.unbound_forms import PickRating, SaveRatingsForm
from film_list.models import Film, FilmFan, FilmFanFilmRating, current_fan, get_rating_name
from loader.views import rating_count_on_file


# Define generic view classes.
class ResultsView(generic.DetailView):
    model = Film
    template_name = 'film_list/results.html'

    def get_context_data(self, **kwargs):
        film = self.object
        fan_rows = []
        fans = FilmFan.film_fans.all()
        for fan in fans:
            fan_row = [fan, fan.fan_rating_str(film), fan.fan_rating_name(film)]
            fan_rows.append(fan_row)
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Film Rating Results'
        context['fan_rows'] = fan_rows
        return context

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)
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
            'rating_count': len(FilmFanFilmRating.fan_ratings.filter(film__festival=festival)),
            'rating_count_on_file': rating_count_on_file(festival),
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
    submit_name_prefix = 'rating_'
    session = request.session
    logged_in_fan = current_fan(session)
    fan_list = FilmFan.film_fans.all()

    # Get the table rows.
    rating_rows = []
    submit_names = []
    get_rating_rows(session, submit_name_prefix, fan_list, rating_rows, submit_names)

    # Construct the context.
    context = add_base_context(request, {
        'title': title,
        'fans': fan_list,
        'rating_rows': rating_rows,
    })
    refresh_rating_action(session, context)

    # Check the request.
    if request.method == 'POST':
        unset_log(session)
        form = PickRating(request.POST)
        if form.is_valid():
            submitted_name = get_submitted_name(request, submit_names)
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


def get_rating_rows(session, submit_name_prefix, fan_list, rating_rows, submit_names):

    # Initialize.
    festival = current_festival(session)
    films = Film.films.filter(festival=festival).order_by('seq_nr')
    logged_in_fan = current_fan(session)

    # Create a rating row for each film.
    for film in films:

        # Set the row to contain film, film duration and film fans.
        rating_cells = [film, film.duration_str()]
        for fan in fan_list:

            # Set a rating string to display.
            rating_str = get_rating_str(film, fan)

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

            # Append a rating cell to the current row.
            rating_cells.append({
                'rating': rating_str,
                'fan': fan,
                'choices': choices
            })

        # Append a row to the table rows.
        rating_rows.append(rating_cells)


def get_submitted_name(request, submit_names):
    submitted_name = None
    for submit_name in submit_names:
        if submit_name in request.POST:
            submitted_name = submit_name
            break
    return submitted_name


def get_rating_str(film, fan):
    try:
        fan_rating = FilmFanFilmRating.fan_ratings.get(film=film, film_fan=fan)
    except (KeyError, FilmFanFilmRating.DoesNotExist):
        fan_rating = None
    rating_str = f'{fan_rating.rating}' if fan_rating is not None else '-'
    return rating_str


def update_rating(session, film, fan, rating_value):
    old_rating_str = get_rating_str(film, fan)
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
