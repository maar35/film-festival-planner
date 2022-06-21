from django.contrib import admin

from exercises.models import Question, Choice

# Register the models.
admin.site.register(Question)
admin.site.register(Choice)
