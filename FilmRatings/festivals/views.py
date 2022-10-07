import datetime

from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.views import generic

from FilmRatings import tools
from FilmRatings.tools import add_base_context
from festivals.forms.set_festival import FestivalEdition, TestNearestFestival
from festivals.models import Festival, default_festival


# Define generic view classes.
class IndexView(generic.ListView):
    template_name = 'festivals/index.html'
    http_method_names = ['get', 'post']
    object_list = Festival.festivals.order_by('-start_date')
    context_object_name = 'festival_list'
    unexpected_error = ''

    def get_context_data(self, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Festival Index'
        context['unexpected_error'] = self.unexpected_error
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':

            picked_festival = None
            names = [(f'{festival.id}', festival) for festival in self.object_list]
            for name, festival in names:
                if name in request.POST:
                    picked_festival = festival
                    break
            if picked_festival is not None:
                picked_festival.set_current(request.session)
                return HttpResponseRedirect(reverse('film_list:film_list'))
            else:
                self.unexpected_error = f'Submit name not found in POS ({request.POST}'

        return render(request, 'festivals/index.html', self.get_context_data())


# Festival details view.
@login_required
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
            selected_festival.set_current(request.session)
            return HttpResponseRedirect(reverse('festivals:detail', args=[selected_festival_id]))
    else:
        form = FestivalEdition(initial={'festival': festival.id}, auto_id=False)

    # Construct the context.
    context = tools.add_base_context(request, {
        "title": title,
        "festival_id": festival.id,
        "form": form,
    })

    return render(request, 'festivals/detail.html', context)


@login_required
def test_default_festival(request):
    # Preset some parameters.
    title = "Nearest Festival Date Picker"

    # Construct the context.
    session = request.session
    context = tools.add_base_context(request, {
        'title': title,
        'festivals': Festival.festivals.order_by('-start_date'),
        'sample_date': session.get('sample_date'),
        'default_festival': session.get('festival'),
    })

    # Check the request.
    if request.method == 'POST':
        form = TestNearestFestival(request.POST)
        if form.is_valid():
            sample_date = form.cleaned_data['sample_date']
            festival = default_festival(sample_date)
            festival.set_current(session)
            session['sample_date'] = str(sample_date)
            session['default_festival'] = str(festival)
            return HttpResponseRedirect(reverse('festivals:test_default_festival'))
    else:
        initial_date = session.get('sample_date', datetime.date.today())
        form = TestNearestFestival(initial={'sample_date': initial_date})

    context['form'] = form
    return render(request, 'festivals/test_default_festival.html', context)
