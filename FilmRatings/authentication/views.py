from django.contrib.auth.views import LoginView
from django.shortcuts import render

from FilmRatings import tools


class FilmsLoginView(LoginView):

    def get_context_data(self, **kwargs):
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Application Login'
        return context


def logout(request):
    tools.unset_current_fan()
    context = tools.add_base_context({
        'title': 'Logged Out',
    })
    return render(request, 'authentication/logged_out.html', context)
