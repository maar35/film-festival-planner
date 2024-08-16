from operator import attrgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views import View
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from festival_planner.cookie import Cookie
from festival_planner.tools import add_base_context, get_log, unset_log
from festivals.models import current_festival
from theaters.forms.theater_forms import TheaterDetailsForm, TheaterScreenDetailsForm
from theaters.models import Theater, Screen

errors_cookie = Cookie('form_errors', [])


class IndexView(ListView):
    """
    Theaters list view.
    """
    template_name = 'theaters/theaters.html'
    http_method_names = ['get']
    context_object_name = 'theater_rows'

    # Define custom attributes.
    label_by_priority = {p: p.label for p in Theater.Priority}

    def get_queryset(self):
        theater_list = sorted(Theater.theaters.all(), key=attrgetter('city.name', 'abbreviation'))
        theater_rows = [self.get_theater_row(theater) for theater in theater_list]
        return sorted(theater_rows, key=lambda row: row['is_festival_city'], reverse=True)

    def get_context_data(self, *, object_list=None, **kwargs):
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        session = self.request.session
        errors_cookie.remove(session)
        context['title'] = 'Theaters Index'
        context['log'] = get_log(session)
        return context

    def get_theater_row(self, theater):
        session = self.request.session
        is_festival_city = current_festival(session).base.home_city == theater.city
        theater_row = {
            'is_festival_city': is_festival_city,
            'theater': theater,
            'priority_color': Theater.color_by_priority[theater.priority],
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

    def get_context_data(self, **kwargs):
        session = self.request.session
        unset_log(session)
        context = add_base_context(self.request, super().get_context_data(**kwargs))
        theater = self.object
        screens = Screen.screens.filter(theater=theater)
        form_errors = errors_cookie.get(session)
        priority_label = IndexView.label_by_priority[theater.priority]
        theater_form = TheaterDetailsForm(initial={
            'abbreviation': theater.abbreviation,
            'priority': priority_label,
        })
        form = TheaterScreenDetailsForm()
        formset = self.get_screen_formset(screens)
        screen_items = self.get_screen_items(screens, formset)
        context['title'] = 'Theater Details'
        context['form'] = form
        context['theater'] = theater
        context['theater_form'] = theater_form
        context['priority_label'] = priority_label
        context['priority_choices'] = Theater.Priority.labels
        context['screens'] = Screen.screens.filter(theater=theater)
        context['screen_items'] = screen_items
        context['form_errors'] = form_errors
        return context

    @staticmethod
    def get_screen_formset(screens):
        screen_form_set_class = formset_factory(TheaterScreenDetailsForm, max_num=len(screens))
        screen_formset = screen_form_set_class(
            initial=[{'screen_abbreviation': screen.abbreviation} for screen in screens]
        )
        return screen_formset

    @staticmethod
    def get_screen_items(screens, formset):
        screen_items = []
        for i, screen in enumerate(screens):
            form = formset[i]
            screen_items.append({'screen': screen, 'form_field': form})

        return screen_items


class TheaterScreenListFormView(SingleObjectMixin, FormView):
    template_name = 'theaters/details.html'
    form_class = TheaterDetailsForm
    model = Theater
    http_method_names = ['post']
    object = None
    priority_by_label = {p.label: p for p in Theater.Priority}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.theater = None
        self.abbreviation = None
        self.session = None

    def post(self, request, *args, **kwargs):
        self.object = self.get_object()
        self.theater = self.object
        self.session = request.session
        errors_cookie.remove(self.session)
        unset_log(self.session)

        # Save new theater abbreviation.
        if 'abbreviation' in request.POST:
            self.abbreviation = request.POST['abbreviation']
            return super().post(request, *args, **kwargs)

        # Save new theater priority.
        if 'priority' in request.POST:
            priority_label = request.POST['priority']
            self.theater.priority = self.priority_by_label[priority_label]
            self.theater.save()
            return self.clean_response()

        # Validate screen abbreviations.
        self.process_screen_abbreviations(request)
        return self.clean_response()

    def form_valid(self, form):
        errors_cookie.remove(self.session)
        theater = self.object
        if theater.abbreviation != self.abbreviation:
            theater.abbreviation = self.abbreviation
            theater.save()
        return super().form_valid(form)

    def form_invalid(self, form):
        field = form['abbreviation']
        message = f'{field.label} "{self.abbreviation}" is invalid.'
        self.add_form_errors([message], field.errors)
        super().form_invalid(form)
        return self.clean_response()

    def get_success_url(self):
        return reverse('theaters:details', kwargs={'pk': self.object.pk})

    def clean_response(self):
        return HttpResponseRedirect(reverse('theaters:details', args=(self.object.pk,)))

    def process_screen_abbreviations(self, request):
        screens = Screen.screens.filter(theater=self.theater)

        # Create a formset based on the POST dictionary.
        data = {
            'form-TOTAL_FORMS': str(len(screens)),
            'form-INITIAL_FORMS': '0',
        }
        for index, screen in enumerate(screens):
            field_id = f'form-{index}-screen_abbreviation'
            if field_id in request.POST:
                data[field_id] = request.POST[field_id]
        screen_formset_class = formset_factory(TheaterScreenDetailsForm)
        result_formset = screen_formset_class(data)

        # Validate the screen forms.
        field = 'screen_abbreviation'
        form_errors = []
        validator_outputs = set()
        for index, form in enumerate(result_formset):
            if form.is_valid():
                screen = screens[index]
                abbreviation = form.cleaned_data[field]
                if screen.abbreviation != abbreviation:
                    screen.abbreviation = abbreviation
                    screen.save()
            else:
                new_abbreviation = form[field].value()
                form_errors.append(f'{form[field].label} #{index+1} "{new_abbreviation}" is invalid.')
                validator_outputs |= set(form.errors[field])
        self.add_form_errors(form_errors, validator_outputs)

    def add_form_errors(self, form_errors, validator_set):
        if not form_errors:
            return
        form_errors.extend(list(validator_set))
        old_errors = errors_cookie.get(self.session)
        if old_errors:
            form_errors = old_errors + [''] + form_errors
        errors_cookie.set(self.session, form_errors)
        return self.clean_response()


class TheaterView(LoginRequiredMixin, View):

    @staticmethod
    def get(request, *args, **kwargs):
        view = TheaterDetailView.as_view()
        return view(request, *args, **kwargs)

    @staticmethod
    def post(request, *args, **kwargs):
        view = TheaterScreenListFormView.as_view()
        return view(request, *args, **kwargs)
