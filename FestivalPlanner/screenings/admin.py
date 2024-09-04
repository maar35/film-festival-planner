from django.contrib import admin

from screenings.models import Screening, Attendance

# Register the models.
admin.site.register(Screening)
admin.site.register(Attendance)
