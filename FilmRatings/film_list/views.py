import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import generic

from FilmRatings.tools import unset_load_log, add_base_context, get_load_log, wrap_up_form_errors
from festivals.models import current_festival
from film_list.forms.pick_rating import PickRating
from film_list.forms.set_film_fan import User
from film_list.forms.set_rating import Rating
from film_list.models import Film, FilmFan, FilmFanFilmRating, current_fan


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
        unset_load_log(request.session)
        return response


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
    unset_load_log(request.session)

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
    if 'rating_action' in session:
        action = session['rating_action']
        context['action'] = action
        context['action']['action_time'] = datetime.datetime.fromisoformat(action['action_time'])

    # Check the request.
    if request.method == 'POST':
        unset_load_log(session)
        form = PickRating(request.POST)
        if form.is_valid():
            submitted_name = get_submitted_name(request, submit_names)
            if submitted_name is not None:
                [film_pk, rating_value] = submitted_name.strip(submit_name_prefix).split('_')
                film = Film.films.get(id=film_pk)
                update_rating(session, film, logged_in_fan, rating_value)

                return HttpResponseRedirect(reverse('film_list:film_list'))
            else:
                context['unexpected_error'] = ["Can't identify submit widget."]
        else:
            context['unexpected_error'] = wrap_up_form_errors(form.errors)

    context['load_results'] = get_load_log(session)
    return render(request, "film_list/film_list.html", context)


def get_submitted_name(request, submit_names):
    submitted_name = None
    for submit_name in submit_names:
        if submit_name in request.POST:
            submitted_name = submit_name
            break
    return submitted_name


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
            is_current_fan = fan == logged_in_fan
            choices = []
            if is_current_fan:
                for value, name in FilmFanFilmRating.Rating.choices:
                    choice = {
                        'label': f'{value} - {name}',
                        'submit_name': f'{submit_name_prefix}{film.id}_{value}'
                    }
                    choices.append(choice)
                    submit_names.append(choice['submit_name'])

            # Append a rating cell to the current row.
            rating_cells.append({
                'rating': rating_str,
                'is_current_fan': is_current_fan,
                'choices': choices
            })

        # Append a row to the table rows.
        rating_rows.append(rating_cells)


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
    rating_action = {
        'old_rating': old_rating_str,
        'new_rating': str(new_rating.rating),
        'rated_film': str(new_rating.film),
        'action_time': datetime.datetime.now().isoformat(),
    }
    session['rating_action'] = rating_action


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
