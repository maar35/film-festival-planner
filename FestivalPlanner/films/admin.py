from django.contrib import admin

from films.models import Film, FilmFan, FilmFanFilmRating

# Register the models.
admin.site.register(Film)
admin.site.register(FilmFan)
admin.site.register(FilmFanFilmRating)
