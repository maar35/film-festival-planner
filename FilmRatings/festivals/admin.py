from django.contrib import admin

from festivals.models import Festival, FestivalBase

# Register the models.
admin.site.register(Festival)
admin.site.register(FestivalBase)