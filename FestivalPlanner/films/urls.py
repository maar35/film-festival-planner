from django.urls import path

from films import views

app_name = 'films'
urlpatterns = [

    # Give access to the active pages.
    path('', views.IndexView.as_view(), name='index'),

    # Set current film fan.
    path('film_fan/', views.film_fan, name='film_fan'),

    # Display ratings by fans of a specific film.
    # Example: /films/5/results/
    path('<int:pk>/details/', views.FilmDetailView.as_view(), name='details'),

    # Display ratings of all films by all fans.
    path('films/', views.FilmsView.as_view(), name='films'),

    # Allow a logged in fan to enter votes.
    path('votes/', views.VotesView.as_view(), name='votes'),

    # Display statistics of reviewers.
    path('reviewers/', views.ReviewersView.as_view(), name='reviewers')
]
