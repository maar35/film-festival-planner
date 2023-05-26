from django.views import generic

from FilmRatings.tools import add_base_context, get_log
from theaters.models import Theater


class IndexView(generic.ListView):
    template_name = 'theaters/theaters.html'
    http_method_names = ['get']
    context_object_name = 'theater_list'

    def get_queryset(self):
        return Theater.theaters.order_by('city', 'parse_name')

    def get_context_data(self, *, object_list=None, **kwargs):
        session = self.request.session
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Theaters Index'
        context['log'] = get_log(session)
        return context
