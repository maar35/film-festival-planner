from django.contrib.auth.decorators import login_required
from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views.generic import FormView, ListView

from festival_planner.tools import add_base_context, get_log, unset_log, initialize_log
from festivals.models import Festival, current_festival
from films.models import Film, FilmFanFilmRating
from loader.forms.loader_forms import TheaterLoaderForm, SectionLoader, SubsectionLoader, RatingLoaderForm
from sections.models import Section, Subsection
from theaters.models import City, Theater, Screen, cities_path, theaters_path, screens_path


def file_record_count(path, has_header=False):
    try:
        with open(path, newline='') as f:
            record_count = len(f.readlines())
        if has_header:
            record_count -= 1
    except FileNotFoundError:
        record_count = 0
    return record_count


class TheatersLoaderView(LoginRequiredMixin, FormView):
    model = Theater
    template_name = 'loader/theaters.html'
    form_class = TheaterLoaderForm
    success_url = '/theaters/theaters'
    http_method_names = ['get', 'post']

    def get_context_data(self, **kwargs):
        session = self.request.session
        theater_items = {
            'city_count': City.cities.count,
            'city_count_on_file': file_record_count(cities_path()),
            'theater_count': Theater.theaters.count,
            'theater_count_on_file': file_record_count(theaters_path()),
            'screen_count': Screen.screens.count,
            'screen_count_on_file': file_record_count(screens_path()),
        }
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Load Theater Data'
        context['theater_items'] = theater_items
        context['log'] = get_log(session)
        unset_log(session)
        return context

    def form_valid(self, form):
        session = self.request.session
        form.load_theater_data(session)
        return super().form_valid(form)


def get_festival_row(festival):
    festival_row = {
        'festival': festival,
        'id': festival.id,
        'section_count_on_file': file_record_count(festival.sections_file),
        'section_count': Section.sections.filter(festival=festival).count,
        'subsection_count_on_file': file_record_count(festival.subsections_file),
        'subsection_count': Subsection.subsections.filter(festival=festival).count,
    }
    return festival_row


class SectionsLoaderView(ListView):
    """
    Class-based view to load program sections of a specific festival.
    """
    template_name = 'loader/sections.html'
    http_method_names = ['get', 'post']
    object_list = [get_festival_row(festival) for festival in Festival.festivals.order_by('-start_date')]
    context_object_name = 'festival_rows'
    unexpected_error = ''

    def get_context_data(self, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Program Sections Loader'
        context['unexpected_error'] = self.unexpected_error
        return context

    def dispatch(self, request, *args, **kwargs):
        if request.method == 'POST':
            picked_festival = None
            names = [(f'{row["id"]}', row['festival']) for row in self.object_list]
            for name, festival in names:
                if name in request.POST:
                    picked_festival = festival
                    break
            if picked_festival is not None:
                session = request.session
                picked_festival.set_current(session)
                initialize_log(session)
                if SectionLoader(session, picked_festival).load_objects():
                    SubsectionLoader(session, picked_festival).load_objects()
                return HttpResponseRedirect(reverse('sections:index'))
            else:
                self.unexpected_error = f'Submit name not found in POST ({request.POST}'

        return render(request, 'loader/sections.html', self.get_context_data())


@login_required
def load_festival_ratings(request):
    """
    View to start loading ratings of a specific festival.
    :param request:
    :return:
    """

    # Construct the context.
    title = 'Load Ratings'
    festivals = Festival.festivals.order_by('-start_date')
    submit_name_prefix = 'festival_'
    festival_items = [{
        'str': festival,
        'submit_name': f'{submit_name_prefix}{festival.id}',
        'color': festival.festival_color,
        'film_count_on_file': file_record_count(festival.films_file, has_header=True),
        'film_count': Film.films.filter(festival=festival).count,
        'rating_count_on_file': file_record_count(festival.ratings_file, has_header=True),
        'rating_count': FilmFanFilmRating.film_ratings.filter(film__festival=festival).count,
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
        form = RatingLoaderForm(request.POST)
        if form.is_valid():
            if festival_indicator is not None:
                keep_ratings = form.cleaned_data['keep_ratings']
                festival_id = int(festival_indicator.strip(submit_name_prefix))
                festival = Festival.festivals.get(pk=festival_id)
                festival.set_current(request.session)
                form.load_rating_data(request.session, festival, keep_ratings)
                return HttpResponseRedirect(reverse('films:films'))
            else:
                context['unexpected_error'] = "Can't identify submit widget."
    else:
        form = RatingLoaderForm(initial={'festival': current_festival(request.session).id})

    context['form'] = form
    return render(request, 'loader/ratings.html', context)
