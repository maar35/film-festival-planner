from django.urls import path

from . import views

app_name = 'screenings'
urlpatterns = [
    path('day_schema/', views.DaySchemaView.as_view(), name='day_schema'),
]