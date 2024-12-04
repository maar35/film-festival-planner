from django.views import generic

from festival_planner.tools import add_base_context, get_log
from festivals.models import current_festival
from sections.models import Subsection


class IndexView(generic.ListView):
    template_name = 'sections/index.html'
    http_method_names = ['get']
    context_object_name = 'subsection_rows'

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.subsections = None

    def get_queryset(self):
        festival = current_festival(self.request.session)
        self.subsections = Subsection.subsections.order_by('section', 'name').filter(section__festival=festival)
        subsection_rows = [self._get_subsection_rows(subsection) for subsection in self.subsections]
        return subsection_rows

    def get_context_data(self, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Sections Index'
        context['log'] = get_log(self.request.session)
        return context

    def _get_subsection_rows(self, subsection):
        return {
            'name': subsection.name,
            'url': subsection.url,
            'description': subsection.description,
            'section': subsection.section,
            'films_count': self.subsections.filter(film__subsection=subsection).count()
        }
