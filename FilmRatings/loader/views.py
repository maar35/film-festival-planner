from django.contrib.auth.decorators import login_required
from django.http import HttpResponseRedirect
from django.shortcuts import render
from django.urls import reverse
from django.views import generic

from FilmRatings.tools import add_base_context, initialize_log
from festivals.models import Festival, current_festival
from film_list.models import Film, FilmFanFilmRating
from loader.forms.loader_forms import RatingLoaderForm, SectionLoader, SubsectionLoader
from sections.models import Section, Subsection


def file_row_count(festival, file, has_header=False):
    try:
        with open(file, newline='') as f:
            row_count = len(f.readlines())
        if has_header:
            row_count -= 1
    except FileNotFoundError:
        row_count = 0
    return row_count


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
        'film_count_on_file': file_row_count(festival, festival.films_file, has_header=True),
        'film_count': Film.films.filter(festival=festival).count,
        'rating_count_on_file': file_row_count(festival, festival.ratings_file),
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
        form = RatingLoaderForm(request.POST)
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
        form = RatingLoaderForm(initial={'festival': current_festival(request.session).id})

    context['form'] = form
    return render(request, 'loader/ratings.html', context)


# Class-based view to load program sections of a specific festival.
def get_festival_row(festival):
    festival_row = {
        'festival': festival,
        'id': festival.id,
        'section_count_on_file': file_row_count(festival, festival.sections_file),
        'section_count': Section.sections.filter(festival=festival).count,
        'subsection_count_on_file': file_row_count(festival, festival.subsections_file),
        'subsection_count': Subsection.subsections.filter(festival=festival).count,
    }
    return festival_row


class SectionsLoaderView(generic.ListView):
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
