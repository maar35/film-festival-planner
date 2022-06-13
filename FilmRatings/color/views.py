from django.shortcuts import render
from django.http import HttpResponseRedirect

from color.models import TableColor
from color.forms.set_color import Color
from FilmRatings import tools


# Color picker view.
def color(request):

    # Preset some parameters.
    title = "Advanced Color Picker"

    # Check the request.
    if "POST" == request.method:
        form = Color(request.POST)
        if form.is_valid():
            selected_color = form.cleaned_data['border_color']
            print(selected_color)
            c = TableColor.table_colors.get(id=1)
            c.border_color = selected_color
            c.save()
            return HttpResponseRedirect('/film_list/film_list/')
        else:
            print(f'In {title}: form not valid.')
    else:
        form = Color()

    # Construct the context.
    context = tools.add_base_context({
        "title": title,
        "color": TableColor.table_colors.get(id=1),
        "form": form,
    })

    return render(request, 'color/color.html', context)
