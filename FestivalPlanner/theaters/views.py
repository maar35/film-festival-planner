from operator import attrgetter

from django.contrib.auth.mixins import LoginRequiredMixin
from django.db import transaction, IntegrityError
from django.forms import formset_factory
from django.http import HttpResponseRedirect
from django.urls import reverse
from django.views.generic import ListView, DetailView, FormView
from django.views.generic.detail import SingleObjectMixin

from festival_planner.cookie import Cookie, Filter
from festival_planner.shared_template_referrer_view import SharedTemplateReferrerView
from festival_planner.tools import add_base_context, get_log, unset_log, wrap_up_form_errors, add_log, initialize_log
from festivals.models import current_festival
from screenings.forms.screening_forms import DummyForm
from screenings.models import Screening
from theaters.forms.theater_forms import TheaterDetailsForm, TheaterScreenDetailsForm, TheaterScreenFormSet
from theaters.models import Theater, Screen

ERRORS_COOKIE = Cookie('form_errors', [])


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
        ERRORS_COOKIE.remove(session)
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
            'display_value': name,
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
    theater_changed = None
    screens_initial_data = None
    screens_changed = None
    screen_to_delete = None

    def __init__(self):
        super().__init__()
        self.list_view = TheaterDetailView
        self.form_view = TheaterDetailFormView


def must_confirm_delete():
    return TheaterView.screen_to_delete and not theater_details_changed()


def must_cancel_delete():
    return TheaterView.screen_to_delete and theater_details_changed()


def theater_details_changed():
    return TheaterView.screens_changed or TheaterView.theater_changed


class TheaterDetailView(DetailView):
    """
    Maintain theater details.
    """
    model = Theater
    template_name = TheaterView.template_name
    http_method_names = ['get']

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.screens = None
        self.theater = None
        self.can_delete_filter = None

    def setup(self, request, *args, **kwargs):
        super().setup(request, *args, **kwargs)
        self.can_delete_filter = Filter('can_delete',
                                        action_false='Allow deleting',
                                        action_true='Stop deleting')

    def dispatch(self, request, *args, **kwargs):
        self.can_delete_filter.handle_get_request(request)
        return super().dispatch(request, *args, **kwargs)

    def get_context_data(self, **kwargs):
        super_context = add_base_context(self.request, super().get_context_data(**kwargs))
        session = self.request.session
        if must_confirm_delete():
            log_text = f'Asking confirmation to delete {TheaterView.screen_to_delete.parse_name}.'
            add_log(session, log_text)

        self.theater = self.object
        self.screens = Screen.screens.filter(theater=self.theater)
        TheaterView.screens_initial_data = [{'abbreviation': screen.abbreviation} for screen in self.screens]

        theater = self.object
        screens = self.screens
        priority_label = TheatersView.label_by_priority[theater.priority]
        can_delete = self.can_delete_filter.on(session)
        theater_form = self._get_theater_form(theater)
        screens_formset = self._get_screen_formset(screens)
        screen_items = self._get_screen_items(screens, screens_formset)
        new_context = {
            'title': 'Theater Details',
            'theater': theater,
            'theater_form': theater_form,
            'priority_label': priority_label,
            'priority_color': Theater.color_by_priority[theater.priority],
            'can_delete_href_filter': self.can_delete_filter.get_href_filter(session),
            'can_delete_action': self.can_delete_filter.action(session),
            'deleting': can_delete,
            'screens': screens,
            'screen_items': screen_items,
            'can_delete': len([1 for item in screen_items if not item['screening_count']]),
            'confirm_delete': must_confirm_delete(),
            'screen_to_delete': TheaterView.screen_to_delete,
            'log': get_log(session),
            'form_errors': ERRORS_COOKIE.get(session),
        }
        TheaterView.theater_changed = False
        TheaterView.screens_changed = False
        unset_log(session)
        initialize_log(session, 'Manage theater details')
        ERRORS_COOKIE.remove(session)
        context = add_base_context(self.request, super_context | new_context)
        return context

    @staticmethod
    def _get_theater_form(theater):
        theater_data = {
            'abbreviation': theater.abbreviation,
        }
        theater_form = TheaterDetailsForm(theater_data, initial=theater_data)
        TheaterDetailsForm.theater_initial_data = theater_data
        return theater_form

    @staticmethod
    def _get_screen_formset(screens):
        screen_formset_class = formset_factory(TheaterScreenDetailsForm, max_num=len(screens))
        screen_formset = screen_formset_class(initial=TheaterView.screens_initial_data)
        return screen_formset

    @staticmethod
    def _get_screen_items(screens, formset):
        screen_items = []
        for i, screen in enumerate(screens):
            form = formset[i]
            screen_items.append({
                'screen': screen,
                'form_field': form,
                'address_type': [c[1] for c in Screen.ScreenAddressType.choices if c[0] == screen.address_type][0],
                'screening_count': Screening.screenings.filter(screen=screen).count(),
                'sort_by': screen.parse_name,
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
        self.new_abbreviation = None
        self.session = None
        self.theater_error = None

    def post(self, request, *args, **kwargs):
        self.session = request.session
        self.object = self.get_object()
        self.theater = self.object
        ERRORS_COOKIE.remove(self.session)

        form_errors = []
        validator_outputs = set()
        initialize_log(self.request.session, 'Manage abbreviations')

        # Redirect to form_valid() if confirmation to delete is decided.
        if 'delete_canceled' in request.POST or 'delete_confirmed' in request.POST:
            add_log(self.session, f'Delete {'confirmed' if 'delete_confirmed' in request.POST else 'canceled'}')
            _ = super().post(request, *args, **kwargs)
            return self.clean_response()

        # Process the theater abbreviation.
        self._process_theater_abbreviation(request, form_errors, validator_outputs)

        # Process the screen abbreviations.
        self._process_screen_abbreviations(request, form_errors, validator_outputs)

        # Store error messages if any.
        self._add_form_errors(form_errors, validator_outputs)

        # Redirect to form_valid() or form_invalid() if a delete button is hit.
        if self._set_screen_to_delete():
            _ = super().post(request, *args, **kwargs)

        return self.clean_response()

    def form_valid(self, form):
        session = self.request.session

        if must_cancel_delete():
            add_log(session, f'Theater details changed, no screen will be deleted.')
            TheaterView.screen_to_delete = None
        else:
            _ = self._set_screen_to_delete()
            # pr_debug(f'{TheaterView.screen_to_delete=}')

        match self.request.POST:
            case {'delete_confirmed': _} if TheaterView.screen_to_delete:
                self._handle_delete(session, form)
            case {'delete_canceled': _}:
                add_log(session, 'Delete screen cancelled.')
                TheaterView.screen_to_delete = None

        return super().form_valid(form)

    def form_invalid(self, form):
        # pr_debug(f'{form.errors=}')
        if TheaterView.screen_to_delete:
            # raise ValueError(f'Screen to delete "{TheaterView.screen_to_delete}" not none while form invalid')
            add_log(self.request.session, f'Invalid theater details, no screen will be deleted.')
            TheaterView.screen_to_delete = None
        else:
            field = form['abbreviation']
            message = f'{field.label} "{self.new_abbreviation}" is invalid.'
            self._add_form_errors([message], field.errors)

            ERRORS_COOKIE.set(self.request.session, wrap_up_form_errors(form.errors))
            super().form_invalid(form)
        return self.clean_response()

    def get_success_url(self):
        return reverse('theaters:details', kwargs={'pk': self.object.pk})

    def clean_response(self):
        fragment = '#ask_confirmation' if must_confirm_delete() else ''
        return HttpResponseRedirect(reverse('theaters:details', args=(self.object.pk,)) + fragment)

    def _set_screen_to_delete(self):
        screens = Screen.screens.filter(theater_id=self.theater.id)
        items = [(f'delete_{screen.id}', screen) for screen in screens]
        for name, screen in items:
            if name in self.request.POST:
                TheaterView.screen_to_delete = screen
                return True
        return False

    @staticmethod
    def _handle_delete(session, form):
        screen = TheaterView.screen_to_delete
        add_log(session, f'Deleting screen {screen.parse_name} confirmed.')
        if form.delete_screen(session, screen):
            add_log(session, f'Deleted {TheaterView.screen_to_delete.parse_name}.')
            TheaterView.screen_to_delete = None

    def _process_theater_abbreviation(self, request, form_errors, validator_outputs):
        session = request.session
        field = 'abbreviation'
        TheaterDetailsForm.theater = self.theater
        details_form = self._get_theater_details_form(request, field)

        # Validate the theater form.
        if details_form.has_changed():
            if details_form.is_valid():
                self.new_abbreviation = details_form.cleaned_data[field]
                add_log(session, f'Theater abbreviation "{self.new_abbreviation}" is valid.')
            elif details_form.non_field_errors():
                add_log(session, f'Non-field error in {self.theater.parse_name}.')
                error, validator_output = details_form.non_field_errors()
                form_errors += [error]
                validator_outputs.add(validator_output)
            else:
                validator_output_list = details_form.errors[field]
                validator_output = ', '.join(validator_output_list)
                add_log(session, f'Error in {self.theater.parse_name}: {validator_output}')
                error = details_form[field].data
                form_errors.append(f'Invalid theater {field}: {error}.')
                validator_outputs |= {validator_output}

        # Save the new abbreviation if no errors exist.
        if details_form.has_changed() and not form_errors and not validator_outputs:
            text = (f'Changing abbreviation of {self.theater.parse_name} from "{self.theater.abbreviation}"'
                    f' into "{self.new_abbreviation}".')
            add_log(request.session, text)
            theater = Theater.theaters.get(id=self.theater.id)
            theater.abbreviation = self.new_abbreviation
            theater.save()

    def _process_screen_abbreviations(self, request, form_errors, validator_outputs):
        session = request.session
        screens = Screen.screens.filter(theater=self.theater)
        updated_by_screen = {}

        # Create a formset based on the POST dictionary.
        screens_formset = self._get_screens_formset(request, screens)

        # Validate the screen forms.
        TheaterView.screens_changed = screens_formset.has_changed()
        if screens_formset.has_changed():
            field = 'abbreviation'
            for index, form in enumerate(screens_formset):
                screen = screens[index]
                if form.is_valid():
                    new_abbreviation = form.cleaned_data[field]
                    if screen.abbreviation != new_abbreviation:
                        add_log(session, f'Screen abbreviation "{form.cleaned_data[field]}" is valid.')
                        updated_by_screen[screen] = new_abbreviation
                else:
                    new_abbreviation = form[field].value()
                    form_errors.append(f'{form[field].label} "{new_abbreviation}" of {screen.parse_name} is invalid.')
                    validator_outputs |= set(form.errors[field])

            # Check for non-form errors.
            if screens_formset.is_valid():
                error, validator_output = screens_formset.non_form_errors() or (None, None)
                if (error, validator_output) != (None, None):
                    add_log(session, f'Non-form error.')
                    form_errors += [error]
                    validator_outputs.add(validator_output)

        # Save the new abbreviations if no errors exist.
        formset_error_count = screens_formset.total_error_count()
        if formset_error_count:
            updated_by_screen = {}
            for error in screens_formset.non_form_errors():
                add_log(session, f'{error}')
        if updated_by_screen:
            current_screen = None
            try:
                with transaction.atomic():
                    for screen, updated_abbreviation in updated_by_screen.items():
                        text = (f'Changing abbreviation of {screen.parse_name} from "{screen.abbreviation}"'
                                f' into "{updated_abbreviation}".')
                        add_log(session, text)
                        screen.abbreviation = updated_abbreviation
                        current_screen = screen
                        screen.save()
            except IntegrityError as e:
                text = f'Duplicate abbreviation "{current_screen.abbreviation}" in {current_screen.parse_name}.'
                add_log(session, text)
                add_log(session, f'Exception: {e}.')
                add_log(session, 'Database rolled back.')
                form_errors += [text, str(e)]
                validator_outputs.add("A screen abbreviation can't be changed into a value that already exist. Please "
                                      "update one by one.")

        return

    @staticmethod
    def _get_theater_details_form(request, field):
        """Return a form based on the POST dictionary"""
        theater_data = {field: request.POST[field]}
        theater_initial = TheaterDetailsForm.theater_initial_data
        details_form = TheaterDetailsForm(theater_data, initial=theater_initial)
        TheaterView.theater_changed = details_form.has_changed()
        return details_form

    @staticmethod
    def _get_screens_formset(request, screens):
        data = {
            'form-TOTAL_FORMS': str(len(screens)),
            'form-INITIAL_FORMS': str(len(TheaterView.screens_initial_data)),
        }
        for index, screen in enumerate(screens):
            field_id = f'form-{index}-abbreviation'
            if field_id in request.POST:
                data[field_id] = request.POST[field_id]
        screen_formset_class = formset_factory(TheaterScreenDetailsForm, formset=TheaterScreenFormSet)
        result_formset = screen_formset_class(data, initial=TheaterView.screens_initial_data)
        return result_formset

    def _add_form_errors(self, form_errors, validator_set):
        if not form_errors:
            return
        old_errors = ERRORS_COOKIE.get(self.session)
        if old_errors:
            form_errors = old_errors + form_errors
        form_errors.extend(list(validator_set))
        ERRORS_COOKIE.set(self.session, form_errors)
