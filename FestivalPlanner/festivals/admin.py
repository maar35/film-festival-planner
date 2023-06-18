from django.contrib import admin

from festivals.models import Festival, FestivalBase

admin.site.register(Festival)
admin.site.register(FestivalBase)
