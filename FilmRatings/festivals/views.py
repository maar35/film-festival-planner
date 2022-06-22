from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import generic

from FilmRatings import tools
from festivals.forms.set_festival import FestivalEdition
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


# Color picker view.
def detail(request, festival_id):

    # Preset some parameters.
    title = "Festival Picker"
    festival = get_object_or_404(Festival, id=festival_id)

    # Check the request.
    if request.method == 'POST':
        form = FestivalEdition(request.POST, initial={'festival': festival.id})
        if form.is_valid():
            selected_festival_id = form.cleaned_data['festival']
            selected_festival = Festival.festivals.get(pk=selected_festival_id)
            selected_festival.set_current_festival()
            return HttpResponseRedirect(reverse('festivals:detail', args=[selected_festival_id]))
        else:
            print(f'{title}: form not valid.')
    else:
        form = FestivalEdition(initial={'festival': festival.id}, auto_id=False)

    # Construct the context.
    context = tools.add_base_context({
        "title": title,
        "festival_id": festival.id,
        "form": form,
    })

    return render(request, 'festivals/detail.html', context)
