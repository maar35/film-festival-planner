from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import generic

from FilmRatings import tools
from film_list.models import Film, FilmFan
from exercises.models import Question


# Views only used in the tutorial.
# https://docs.djangoproject.com/en/3.2/intro/tutorial04/.

# Generic view classes.


class IndexView(generic.ListView):
    template_name = 'exercises/index.html'
    context_object_name = 'latest_question_list'

    def get_queryset(self):
        """
        Return the last five published questions (not including those set to be
        published in the future).
        """
        now = timezone.now()
        return Question.objects.filter(pub_date__lte=now).order_by('-pub_date')[:5]

    def get_context_data(self, **kwargs):
        film = Film.films.get(film_id=23)
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Questions Index Exercise'
        context['film'] = film
        return context


class DetailView(generic.DetailView):
    model = Question
    template_name = 'exercises/detail.html'
    context_object_name = 'chosen_question'

    def get_queryset(self):
        """
        Excludes any questions that aren't published yet.
        """
        return Question.objects.filter(pub_date__lte=timezone.now())

    def get_context_data(self, **kwargs):
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Details Exercise'
        return context


class ResultsView(generic.DetailView):
    model = Question
    template_name = 'exercises/results.html'

    def get_context_data(self, **kwargs):
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Results Exercise'
        return context


# Old school view classes

def vote(request, question_id):
    title = f'Details Exercise - Empty Vote'
    question = get_object_or_404(Question, id=question_id)
    print(f'@@ {title}: question_id={question_id} {question}')
    try:
        choice_id = request.POST['choice']
        print(f'@@ {title}: POSTed choice_id={choice_id}')
        selected_choice = question.choice_set.get(id=choice_id)
    except KeyError:
        # Redisplay the film rating voting form.
        context = tools.add_base_context({
            'title': title,
            'chosen_question': question,
            'error_message': "First select a choice, you fool.",
        })
        return render(request, 'exercises/detail.html', context)
    else:
        print(f'@@ {title}: POST went fine, selected choice={selected_choice}')
        selected_choice.votes += 1
        selected_choice.save()

        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('exercises:results', args=(question.id,)))


# Working views that are replaced by generic views.

# def film_index(request):
#     title = 'Film Index'
#     partial_film_list = Film.films.order_by('-title')[:15]
#     context = tools.add_base_context({
#         'title': title,
#         'partial_film_list': partial_film_list
#     })
#     return render(request, 'exercises/index.html', context)


# def detail(request, film_id):
#     title = 'Film Details'
#     film = get_object_or_404(Film, pk=film_id)
#     context = tools.add_base_context({
#         'title': title,
#         'film': film
#     })
#     return render(request, 'exercises/detail.html', context)


# def results(request, film_id):
#     title = 'Film Rating Results'
#     film = get_object_or_404(Film, pk=film_id)
#     context = tools.add_base_context({
#         'title': title,
#         'film': film
#     })
#     return render(request, 'exercises/results.html', context)
