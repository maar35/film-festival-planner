from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.views import generic

from FilmRatings import tools
from festivals.forms.set_color import FestivalDetail
from festivals.models import Festival


# Define generic view classes.
class IndexView(generic.ListView):
    template_name = 'festivals/index.html'
    context_object_name = 'festival_list'

    def get_queryset(self):
        """Return the festivals, most recent first."""
        return Festival.festivals.order_by('-start_date')

    def get_context_data(self, **kwargs):
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Festival Index'
        return context


class DetailView(generic.DetailView):
    model = Festival
    template_name = 'festivals/detail.html'

    def get_context_data(self, **kwargs):
        tools.set_current_festival(self.object)
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Festival Details'
        context['border_color'] = self.object.border_color
        return context


# Color picker view.
def detail(request, festival_id):

    # Preset some parameters.
    title = "Festival Color Picker"

    # Check the request.
    print(f'In {title}, passed festival id is: {festival_id}.')
    if "POST" == request.method:
        form = FestivalDetail(request.POST)
        if form.is_valid():
            selected_color = form.cleaned_data['border_color']
            print(f'In {title}, selected color is: {selected_color}.')
            festival = Festival.festivals.get(pk=festival_id)
            festival.border_color = selected_color
            festival.save()
            return HttpResponseRedirect('/film_list/film_list/')
        else:
            print(f'In {title}: form not valid.')
    else:
        print('Nothing POSTed.')
        form = FestivalDetail()

    # Construct the context.
    context = tools.add_base_context({
        "title": title,
        "festival": Festival.festivals.get(pk=festival_id),
        "form": form,
    })

    return render(request, 'festivals/detail.html', context)
