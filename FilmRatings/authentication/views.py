from django.contrib.auth.views import LoginView
from django.shortcuts import render

from FilmRatings import tools
from festivals.models import set_current_festival
from film_list.models import set_current_fan, unset_current_fan


class FilmsLoginView(LoginView):
    template_name = 'authentication/login.html'

    def dispatch(self, request, *args, **kwargs):
        response = super().dispatch(request, *args, **kwargs)

        if request.method == 'POST':
            set_current_fan(request)
            set_current_festival(request.session)

        return response

    def get_context_data(self, **kwargs):
        context = tools.add_base_context(self.request, super().get_context_data(**kwargs))
        context['title'] = 'Application Login'
        return context


def logout(request):
    unset_current_fan(request.session)
    context = tools.add_base_context(request, {
        'title': 'Logged Out',
    })
    return render(request, 'authentication/logged_out.html', context)


def set_test_cookie(request):
    request.session.set_test_cookie()
    context = tools.add_base_context(request, {
        'title': 'Set Test Cookie'
    })
    return render(request, 'authentication/set_test_cookie.html', context)


def check_test_cookie(request):
    worked = request.session.test_cookie_worked()
    context = tools.add_base_context(request, {
        'title': 'Check Test Cookie',
        'test_cookie_worked':  worked,
    })
    if worked:
        request.session.delete_test_cookie()
    return render(request, 'authentication/check_test_cookie.html', context)
