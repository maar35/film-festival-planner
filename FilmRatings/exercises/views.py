from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import generic

from FilmRatings import tools
from filmList.models import Film, FilmFan


# Views only used in the tutorial.
# (https://docs.djangoproject.com/en/3.2/intro/tutorial04/).

# Generic view classes.


class IndexView(generic.ListView):
    template_name = 'exercises/film_index.html'
    context_object_name = 'partial_film_list'

    def get_queryset(self):
        """Return a part of the films."""
        return Film.films.order_by('seq_nr')[:20]

    def get_context_data(self, **kwargs):
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Films Index Exercise'
        return context


class DetailView(generic.DetailView):
    model = Film
    template_name = 'exercises/detail.html'

    def get_context_data(self, **kwargs):
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Film Rating Details Exercise'
        return context


class ResultsView(generic.DetailView):
    model = Film
    template_name = 'exercises/results.html'

    def get_context_data(self, **kwargs):
        film = self.object
        fan_rows = []
        fans = FilmFan.film_fans.all()
        for fan in fans:
            fan_row = [fan, fan.fan_rating_str(film)]
            fan_rows.append(fan_row)
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Film Rating Results Exercise'
        context['fan_rows'] = fan_rows
        return context


# Old school view classes

def vote(request, film_id):
    title = f'Film Details Exercise - Empty Vote'
    film = get_object_or_404(Film, film_id=film_id)
    try:
        choice = request.POST['choice']
        # selected_rating = film.filmfanfilmrating_set.get(pk=choice)
    except KeyError:
        # Redisplay the film rating voting form.
        context = tools.add_base_context({
            'title': title,
            'film': film,
            'error_message': "First select a rating, you fool.",
        })
        return render(request, 'exercises/detail.html', context)
    else:
        # selected_rating.vote_count += 1
        # selected_rating.save()

        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('exercises:results', args=(film.film_id,)))


# Working views that are replaced by generic views.

# def film_index(request):
#     title = 'Film Index'
#     partial_film_list = Film.films.order_by('-title')[:15]
#     context = tools.add_base_context({
#         'title': title,
#         'partial_film_list': partial_film_list
#     })
#     return render(request, 'exercises/film_index.html', context)


# def detail(request, film_id):
#     title = 'Film Details'
#     film = get_object_or_404(Film, pk=film_id)
#     context = tools.add_base_context({
#         'title': title,
#         'film': film
#     })
#     return render(request, 'exercises/detail.html', context)


# def results(request, film_id):
#     title = 'Film Rating Results'
#     film = get_object_or_404(Film, pk=film_id)
#     context = tools.add_base_context({
#         'title': title,
#         'film': film
#     })
#     return render(request, 'exercises/results.html', context)
