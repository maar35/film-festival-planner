from django.urls import path

from film_list import views

app_name = 'film_list'
urlpatterns = [

    # Give access to the active pages.
    path('', views.index, name='index'),

    # Set current film fan.
    path('film_fan/', views.film_fan, name='film_fan'),

    # Display ratings of all films by all fans.
    # Allows to access a detail page for a specific film.
    path('film_list/', views.film_list, name='film_list'),

    # Display ratings by fans of a specific film.
    # Example: /film_list/5/results/
    path('<int:pk>/results/', views.ResultsView.as_view(), name='results'),

    # Allow the current user to rate a specific film.
    # Example: /film_ist/5/rating/
    path('<int:film_pk>/rating/', views.rating, name='rating'),

    # Allow an admin user to save the ratings.
    # Example: /film_list/5/save/
    path('<int:pk>/save/', views.SaveView.as_view(), name='save'),
]
