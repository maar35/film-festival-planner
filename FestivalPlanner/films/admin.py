from django.contrib import admin

from films.models import Film, FilmFanFilmRating
from authentication.models import FilmFan

# Register the models.
admin.site.register(Film)
admin.site.register(FilmFan)
admin.site.register(FilmFanFilmRating)
