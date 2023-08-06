from operator import attrgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from festival_planner.tools import add_base_context, get_log
from festivals.models import current_festival
from theaters.forms.theater_forms import TheaterDetailsForm
from theaters.models import Theater, Screen


class IndexView(ListView):
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
        TheaterDetailView.form_error = None

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


class TheaterDetailView(DetailView):
    """
    Maintain theater details.
    """
    model = Theater
    template_name = 'theaters/details.html'
    http_method_names = ['get']
    priority_submit_name = 'priority'
    form_error = None

    def get_context_data(self, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        theater = self.object
        context['title'] = 'Theater Details'
        context['form'] = TheaterDetailsForm
        context['theater'] = theater
        context['priority_label'] = IndexView.label_by_priority[theater.priority]
        context['priority_choices'] = Theater.Priority.labels
        context['priority_submit_name'] = self.priority_submit_name
        context['screens'] = Screen.screens.filter(theater=theater)
        context['form_error'] = self.form_error
        return context


class TheaterDetailFormView(SingleObjectMixin, FormView):
    template_name = 'theaters/details.html'
    form_class = TheaterDetailsForm
    model = Theater
    http_method_names = ['post']
    object = None
    priority_by_label = {p.label: p for p in Theater.Priority}

    def __init__(self):
        super().__init__()
        self.abbreviation = None
        self.priority = None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        # response = super().post(request, *args, **kwargs)
        if 'abbreviation' in request.POST:
            self.abbreviation = request.POST['abbreviation']
        priority_submit_name = TheaterDetailView.priority_submit_name
        if priority_submit_name in request.POST:
            theater = self.object
            priority_label = request.POST[priority_submit_name]
            theater.priority = self.priority_by_label[priority_label]
            theater.save()
            return self.clean_response()

        return super().post(request, *args, **kwargs)

    def form_valid(self, form):
        TheaterDetailView.form_error = None
        theater = self.object
        theater.abbreviation = self.abbreviation
        theater.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        message = form.fields["abbreviation"].validators[0].message
        TheaterDetailView.form_error = f'{message} So "{self.abbreviation}" is invalid.'
        super().form_invalid(form)
        return self.clean_response()

    def get_success_url(self):
        return reverse('theaters:details', kwargs={'pk': self.object.pk})

    def clean_response(self):
        return HttpResponseRedirect(reverse('theaters:details', args=(self.object.pk,)))


class TheaterView(LoginRequiredMixin, View):

    def __init__(self):
        super().__init__()

    @staticmethod
    def get(request, *args, **kwargs):
        view = TheaterDetailView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = TheaterDetailFormView.as_view()
        return view(request, *args, **kwargs)
