from operator import attrgetter

from django.views import generic

from festival_planner.tools import add_base_context, get_log
from festivals.models import current_festival
from theaters.models import Theater, Screen


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
        theater_list = sorted(Theater.theaters.all(), key=attrgetter('city.name', 'abbreviation'))
        theater_rows = [self.get_theater_row(theater) for theater in theater_list]
        return sorted(theater_rows, key=lambda row: row['is_festival_city'], reverse=True)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        session = self.request.session
        context['title'] = 'Theaters Index'
        context['log'] = get_log(session)
        return context

    def get_theater_row(self, theater):
        session = self.request.session
        is_festival_city = current_festival(session).base.home_city == theater.city
        theater_row = {
            'is_festival_city': is_festival_city,
            'theater': theater,
            'priority_color': self.color_by_priority[theater.priority],
            'priority_label': self.label_by_priority[theater.priority],
            'screen_count': Screen.screens.filter(theater=theater).count()
        }
        return theater_row
