from django.urls import path

from availabilities import views

app_name = 'availabilities'
urlpatterns = [
    path('list/', views.AvailabilityView.as_view(), name='list'),
]
