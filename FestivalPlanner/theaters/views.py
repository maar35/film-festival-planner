from operator import attrgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from festival_planner.cookie import Cookie
from festival_planner.shared_template_referrer_view import SharedTemplateReferrerView
from festival_planner.tools import add_base_context, get_log, unset_log
from festivals.models import current_festival
from screenings.forms.screening_forms import DummyForm
from theaters.forms.theater_forms import TheaterDetailsForm, TheaterScreenDetailsForm, TheaterScreenFormSet
from theaters.models import Theater, Screen

errors_cookie = Cookie('form_errors', [])


class TheatersView(SharedTemplateReferrerView):
    """Theaters list with updatable priorities."""
    template_name = 'theaters/theaters.html'
    label_by_priority = {p: p.label for p in Theater.Priority}

    def __init__(self):
        super().__init__()
        self.list_view = TheatersListView
        self.form_view = TheatersFormView


class TheatersListView(LoginRequiredMixin, ListView):
    """
    Theaters list view.
    """
    template_name = TheatersView.template_name
    http_method_names = ['get']
    context_object_name = 'theater_rows'

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
        priority_choices = self._get_priority_choices(theater)
        theater_row = {
            'is_festival_city': is_festival_city,
            'theater': theater,
            'priority_color': Theater.color_by_priority[theater.priority],
            'priority_label': TheatersView.label_by_priority[theater.priority],
            'priority_choices': priority_choices,
            'screen_count': Screen.screens.filter(theater=theater).count()
        }
        return theater_row

    @staticmethod
    def _get_priority_choices(theater):
        submit_name_prefix = 'theaters_'
        choices = Theater.Priority.choices

        choice_props_list = [{
            'prio_name': name,
            'submit_name': f'{submit_name_prefix}{theater.id}_{value}',
            'disabled': value == theater.priority,
        } for value, name in choices]

        return choice_props_list


class TheatersFormView(LoginRequiredMixin, FormView):
    template_name = TheatersView.template_name
    form_class = DummyForm
    http_method_names = ['post']
    success_url = '/theaters/theaters'

    def form_valid(self, form):
        submitted_name = list(self.request.POST.keys())[-1]
        _, theater_id_str, priority_str = submitted_name.split('_')
        theater = Theater.theaters.get(pk=int(theater_id_str))
        theater.priority = int(priority_str)
        theater.save()
        return super().form_valid(form)


class TheaterView(SharedTemplateReferrerView):
    template_name = 'theaters/details.html'

    def __init__(self):
        super().__init__()
        self.list_view = TheaterDetailView
        self.form_view = TheaterDetailFormView


class TheaterDetailView(DetailView):
    """
    Maintain theater details.
    """
    model = Theater
    template_name = TheaterView.template_name
    http_method_names = ['get']

    def get_context_data(self, **kwargs):
        super_context = add_base_context(self.request, super().get_context_data(**kwargs))
        session = self.request.session
        unset_log(session)
        theater = self.object
        screens = Screen.screens.filter(theater=theater)
        form_errors = errors_cookie.get(session)
        priority_label = TheatersView.label_by_priority[theater.priority]
        theater_form = TheaterDetailsForm(initial={
            'abbreviation': theater.abbreviation,
            'priority': priority_label,
        })
        formset = self.get_screen_formset(screens)
        screen_items = self.get_screen_items(screens, formset)
        new_context = {
            'title': 'Theater Details',
            'theater': theater,
            'theater_form': theater_form,
            'priority_label': priority_label,
            'priority_color': Theater.color_by_priority[theater.priority],
            'screens': screens,
            'screen_items': screen_items,
            'form_errors': form_errors,
        }
        context = add_base_context(self.request, super_context | new_context)
        return context

    @staticmethod
    def get_screen_formset(screens):
        screen_formset_class = formset_factory(TheaterScreenDetailsForm, max_num=len(screens))
        screen_formset = screen_formset_class(
            initial=[{'screen_abbreviation': screen.abbreviation} for screen in screens]
        )
        return screen_formset

    @staticmethod
    def get_screen_items(screens, formset):
        screen_items = []
        for i, screen in enumerate(screens):
            form = formset[i]
            screen_items.append({
                'screen': screen,
                'form_field': form,
                'address_type': [c[1] for c in Screen.ScreenAddressType.choices if c[0] == screen.address_type][0],
            })

        return screen_items


class TheaterDetailFormView(SingleObjectMixin, FormView):
    template_name = TheaterView.template_name
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
        self.theater_error = None

    def post(self, request, *args, **kwargs):
        self.session = request.session
        self.object = self.get_object()
        self.theater = self.object
        errors_cookie.remove(self.session)
        unset_log(self.session)
        form_errors = []
        validator_outputs = set()

        # Validate new theater abbreviation.
        if 'abbreviation' in request.POST:
            self.validate_theater_abbreviation_unique(request, form_errors, validator_outputs)
            _ = super().post(request, *args, **kwargs)

        # Process the screenings.
        self.process_screen_abbreviations(request, form_errors, validator_outputs)

        # Store the error messages.
        self.add_form_errors(form_errors, validator_outputs)

        return self.clean_response()

    def form_valid(self, form):
        errors_cookie.remove(self.session)
        if not self.theater_error:
            self.theater.save()
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

    def validate_theater_abbreviation_unique(self, request, form_errors, validator_outputs):
        """Validate uniqueness of new theater abbreviation."""
        self.theater_error = False
        self.abbreviation = request.POST['abbreviation']
        if self.theater.abbreviation != self.abbreviation:
            try:
                _ = Theater.theaters.get(abbreviation=self.abbreviation, city=self.theater.city)
            except Theater.DoesNotExist:
                self.theater.abbreviation = self.abbreviation
            else:
                form_errors.append(f'Theater abbreviation "{self.abbreviation}" already exists.')
                validator_outputs.add('Theater abbreviations are unique within a city')
                self.theater_error = True

    def process_screen_abbreviations(self, request, form_errors, validator_outputs):
        screens = Screen.screens.filter(theater=self.theater)
        updated_by_screen = {}

        # Create a formset based on the POST dictionary.
        data = {
            'form-TOTAL_FORMS': str(len(screens)),
            'form-INITIAL_FORMS': '0',
        }
        for index, screen in enumerate(screens):
            field_id = f'form-{index}-screen_abbreviation'
            if field_id in request.POST:
                data[field_id] = request.POST[field_id]
        screen_formset_class = formset_factory(TheaterScreenDetailsForm, formset=TheaterScreenFormSet)
        result_formset = screen_formset_class(data)

        # Validate the screen forms.
        field = 'screen_abbreviation'
        for index, form in enumerate(result_formset):
            if form.is_valid():
                screen = screens[index]
                abbreviation = form.cleaned_data[field]
                if screen.abbreviation != abbreviation:
                    updated_by_screen[screen] = abbreviation
            else:
                new_abbreviation = form[field].value()
                form_errors.append(f'{form[field].label} #{index+1} "{new_abbreviation}" is invalid.')
                validator_outputs |= set(form.errors[field])

        # Save the new abbreviations if no non-form errors exist.
        if result_formset.non_form_errors():
            form_errors += result_formset.non_form_errors()
        else:
            for screen, updated_abbreviation in updated_by_screen.items():
                screen.abbreviation = updated_abbreviation
                screen.save()

        return

    def add_form_errors(self, form_errors, validator_set):
        if not form_errors:
            return
        form_errors.extend(list(validator_set))
        old_errors = errors_cookie.get(self.session)
        if old_errors:
            form_errors = old_errors + [''] + form_errors
        errors_cookie.set(self.session, form_errors)
