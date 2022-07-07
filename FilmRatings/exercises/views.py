from django.http import HttpResponseRedirect
from django.shortcuts import render, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.views import generic

from FilmRatings import tools
from exercises.models import Question


# Views only used in the tutorial.
# https://docs.djangoproject.com/en/3.2/intro/tutorial04/.
# (and the course)


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
        context = tools.add_base_context(super().get_context_data(**kwargs))
        context['title'] = 'Questions Index Exercise'
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
    try:
        choice_id = request.POST['choice']
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
        selected_choice.votes += 1
        selected_choice.save()

        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('exercises:results', args=(question.id,)))
