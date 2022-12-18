from django.views import generic

from FilmRatings.tools import add_base_context, get_log
from festivals.models import current_festival
from sections.models import Subsection


class IndexView(generic.ListView):
    template_name = 'sections/index.html'
    http_method_names = ['get']
    context_object_name = 'subsection_list'

    def get_queryset(self):
        festival = current_festival(self.request.session)
        return Subsection.subsections.order_by('section', 'name').filter(festival=festival)

    def get_context_data(self, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Sections Index'
        context['log'] = get_log(self.request.session)
        return context
