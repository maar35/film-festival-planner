from django.urls import path

from loader import views

app_name = 'loader'
urlpatterns = [
    path('ratings', views.load_ratings, name='ratings'),
]
