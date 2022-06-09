from django.core.exceptions import ObjectDoesNotExist
from django.shortcuts import get_object_or_404, render
from django.http import HttpResponse, HttpResponseRedirect
from django.urls import reverse

from color.models import TableColor
from color.forms.set_color import Color
from FilmRatings import tools


# Color picker view.
def color(request):

    # Preset some parameters.
    title = "Advanced Color Picker"
    print(f'@@ in {title} debug. Action hardcoded URL, no param.')

    # Check the request.
    if "POST" == request.method:
        form = Color(request.POST)
        print(f'@@ in {title} POST.')
        if form.is_valid():
            selected_color = form.cleaned_data['border_color']
            print(selected_color)
            c = TableColor.table_colors.get(id=1)
            c.border_color = selected_color
            c.save()
            return HttpResponseRedirect('/film_list/film_list/')
        else:
            print(f'@@ in {title}: form not valid!!')
    else:
        form = Color()

    # Construct the context.
    context = tools.add_base_context({
        "title": title,
        "color": TableColor.table_colors.get(id=1),
        "form": form,
    })

    return render(request, 'color/color.html', context)


def html_color_index(request):

    # Preset parameters.
    title = "Pure HTML colors index"
    print(f'@@ in {title} debug. No action, no param.')

    # Construct the context.
    context = tools.add_base_context({
        'title': title,
    })
    return render(request, 'color/html_color_index.html', context)


def details(request, color_id):

    # Initialize variables.
    title = f'Color details {color_id}'
    print(f'@@ in {title} debug. Action vote URL, param={color_id}.')
    picked_color = get_object_or_404(TableColor, id=color_id)
    title = f'Color {color_id} - {picked_color}'

    # Process the form result.
    try:
        choice = request.POST['choice']
        selected_color = TableColor.table_colors.get(id=choice)
    except (KeyError, ObjectDoesNotExist):
        # Redisplay the color voting form.
        context = tools.add_base_context({
            'title': title,
            'picked_color': picked_color,
        })
        return render(request, 'color/details.html', context)
    else:
        selected_color.vote_count += 1
        selected_color.save()
        c = TableColor.table_colors.get(id=1)
        c.border_color = selected_color.border_color
        c.save()

        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('color:results', args=(selected_color.id,)))


def vote(request, color_id):
    title = f'Vote {color_id}'
    print(f'@@ in {title} debug. Action vote URL, param={color_id}.')
    picked_color = get_object_or_404(TableColor, id=color_id)
    try:
        choice = request.POST['choice']
        selected_color = TableColor.table_colors.get(id=choice)
    except (KeyError, ObjectDoesNotExist):
        # Redisplay the color voting form.
        context = tools.add_base_context({
            'title': title,
            'picked_color': picked_color,
            'error_message': "You didn't select a choice, you fool.",
            # 'colors': TableColor.table_colors.order_by('id'),
        })
        return render(request, 'color/vote.html', context)
    else:
        selected_color.vote_count += 1
        selected_color.save()
        c = TableColor.table_colors.get(id=1)
        c.border_color = selected_color.border_color
        c.save()
        # Always return an HttpResponseRedirect after successfully dealing
        # with POST data. This prevents data from being posted twice if a
        # user hits the Back button.
        return HttpResponseRedirect(reverse('color:results', args=(selected_color.id,)))

    #
    # # Process the request.
    # try:
    #     selected_color = border_color.choice_set.get(pk=request.POST['choice'])
    # except (KeyError, ObjectDoesNotExist):
    #     # Redisplay the color voting form.
    #     return render(request, 'film_list.html', {
    #         'color': border_color,
    #     })
    # else:
    #     # selected_color.votes += 1
    #     TableColor.table_colors.get(id=1).update_or_create(border_color=selected_color)
    #     hello(request)
    #     # Always return an HttpResponseRedirect after successfully dealing
    #     # with POST data. This prevents data from being posted twice if a
    #     # user hits the Back button.
    #     return HttpResponseRedirect(reverse('hello', args=(border_color.id,)))


def results(request, color_id):
    title = 'Vote Result'
    print(f'@@ in {title} debug. No action, param={color_id}.')
    picked_color = get_object_or_404(TableColor, id=color_id)
    context = tools.add_base_context({
        'title': title,
        'picked_color': picked_color,
    })
    return render(request, 'color/results.html', context)


def thanks(request):
    return HttpResponse("Thanks for picking a color. Much appreciated.")
