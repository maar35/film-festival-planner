from operator import attrgetter

from django.views import generic

from FilmRatings.tools import add_base_context, get_log
from theaters.models import Theater


class IndexView(generic.ListView):
    """
    Theaters list view.
    """
    template_name = 'theaters/theaters.html'
    http_method_names = ['get']
    context_object_name = 'theater_rows'

    # Define custom attributes.
    label_by_priority = {p: p.label for p in Theater.Priority}
    color_by_priority = {}

    def __init__(self, **kwargs):
        super().__init__(**kwargs)
        self.color_by_priority[Theater.Priority.NO_GO] = 'SlateGray'
        self.color_by_priority[Theater.Priority.LOW] = 'PowderBlue'
        self.color_by_priority[Theater.Priority.HIGH] = 'Coral'

    def get_queryset(self):
        theater_list = sorted(Theater.theaters.all(), key=attrgetter('city.name', 'parse_name'))
        return [self.get_theater_row(theater) for theater in theater_list]

    def get_context_data(self, *, object_list=None, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        session = self.request.session
        context['title'] = 'Theaters Index'
        context['log'] = get_log(session)
        return context

    def get_theater_row(self, theater):
        theater_row = {
            'theater': theater,
            'priority_color': self.color_by_priority[theater.priority],
            'priority_label': self.label_by_priority[theater.priority]
        }
        return theater_row
