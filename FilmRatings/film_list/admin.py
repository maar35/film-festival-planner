from django.contrib import admin

from film_list.models import Film, FilmFan, FilmFanFilmRating

# Register the models.
admin.site.register(Film)
admin.site.register(FilmFan)
admin.site.register(FilmFanFilmRating)
