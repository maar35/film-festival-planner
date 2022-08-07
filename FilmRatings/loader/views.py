from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse

from FilmRatings import tools
from festivals.models import Festival, current_festival
from loader.forms.loader_forms import Loader


def load_ratings(request):

    # Preset title.
    title = 'Load Ratings'

    # Check the request.
    if request.method == 'POST':
        form = Loader(request.POST)
        if form.is_valid():
            festival_id = form.cleaned_data['festival']
            festival = Festival.festivals.get(pk=festival_id)
            festival.set_current(request.session)
            return HttpResponseRedirect(reverse('film_list:film_list'))
        else:
            print(f'{title}: form not valid.')
    else:
        form = Loader(initial={'festival': current_festival(request.session).id})

    # Set the context.
    context = tools.add_base_context(request, {
        'title': title,
        'form': form
    })

    return render(request, 'loader/ratings.html', context)
