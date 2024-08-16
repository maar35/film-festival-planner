from django.contrib.auth.mixins import LoginRequiredMixin
from django.views.generic import ListView

from festival_planner.tools import add_base_context, get_log
from festivals.models import current_festival
from screenings.models import Screening
from theaters.models import Theater


class DaySchemaView(LoginRequiredMixin, ListView):
    template_name = 'screenings/day_schema.html'
    http_method_names = ['get']
    context_object_name = 'screen_rows'
    probe_day = None

    def get_queryset(self):
        festival = current_festival(self.request.session)
        festival_screenings = Screening.screenings.filter(film__festival=festival)
        self.probe_day = festival.end_date
        day_screenings = [s for s in festival_screenings if s.start_dt.date() == self.probe_day]
        screenings_by_screen = {}
        sorted_screenings = sorted(day_screenings, key=lambda s: str(s.screen))
        for screening in sorted(sorted_screenings, key=lambda s: s.screen.theater.priority, reverse=True):
            try:
                screenings_by_screen[screening.screen].append(screening)
            except KeyError:
                screenings_by_screen[screening.screen] = [screening]
        screen_rows = [self._get_screen_row(screen, screenings) for screen, screenings in screenings_by_screen.items()]
        return screen_rows

    def get_context_data(self, **kwargs):
        super_context = super().get_context_data(**kwargs)
        new_context = {
            'title': 'Screenings Day Schema',
            'sub_header': 'Watch this day plan grow',
            'day': self.probe_day.isoformat(),
            'log': get_log(self.request.session),
        }
        return add_base_context(self.request, super_context | new_context)

    @staticmethod
    def _get_screen_row(screen, screenings):
        screen_row = {
            'screen': screen,
            'color': Theater.color_by_priority[screen.theater.priority],
            'screenings': sorted(str(s) for s in screenings),
        }
        return screen_row
