from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from FilmRatings.tools import add_base_context
from festivals.models import Festival, current_festival
from film_list.models import Film, FilmFanFilmRating
from loader.forms.loader_forms import Loader


# View to start loading ratings of a specific festival.
@login_required
def load_festival_ratings(request):

    # Construct the context.
    title = 'Load Ratings'
    festivals = Festival.festivals.order_by('-start_date')
    submit_name_prefix = 'festival_'
    festival_items = [{
        'str': festival,
        'submit_name': f'{submit_name_prefix}{festival.id}',
        'color': festival.festival_color,
        'film_count_on_file': film_count_on_file(festival),
        'film_count': Film.films.filter(festival=festival).count,
        'rating_count_on_file': rating_count_on_file(festival),
        'rating_count': FilmFanFilmRating.fan_ratings.filter(film__festival=festival).count,
    } for festival in festivals]
    context = add_base_context(request, {
        'title': title,
        'festival_items': festival_items,
    })

    # Check the request.
    if request.method == 'POST':
        festival_indicator = None
        names = [f'{submit_name_prefix}{festival.id}' for festival in festivals]
        for name in names:
            if name in request.POST:
                festival_indicator = name
                break
        form = Loader(request.POST)
        if form.is_valid():
            if festival_indicator is not None:
                keep_ratings = form.cleaned_data['keep_ratings']
                festival_id = int(festival_indicator.strip(submit_name_prefix))
                festival = Festival.festivals.get(pk=festival_id)
                festival.set_current(request.session)
                form.load_rating_data(request.session, festival, keep_ratings)
                return HttpResponseRedirect(reverse('film_list:film_list'))
            else:
                context['unexpected_error'] = "Can't identify submit widget."
    else:
        form = Loader(initial={'festival': current_festival(request.session).id})

    context['form'] = form
    return render(request, 'loader/ratings.html', context)


def film_count_on_file(festival):
    try:
        with open(festival.films_file, newline='') as films_file:
            film_count = len(films_file.readlines()) - 1    # Exclude header.
    except FileNotFoundError:
        film_count = 0
    return film_count


def rating_count_on_file(festival):
    try:
        with open(festival.ratings_file, newline='') as ratings_file:
            rating_count = len(ratings_file.readlines()) - 1    # Exclude header.
    except FileNotFoundError:
        rating_count = 0
    return rating_count
