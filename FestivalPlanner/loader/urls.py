from django.urls import path

from loader import views

app_name = 'loader'
urlpatterns = [
    path('ratings', views.RatingsLoaderView.as_view(), name='ratings'),
    path('<int:pk>/save_ratings/', views.SaveRatingsView.as_view(), name='save_ratings'),
    path('sections', views.SectionsLoaderView.as_view(), name='sections'),
    path('theaters', views.TheaterDataInterfaceView.as_view(), name='theaters'),
    path('new_screens', views.NewTheaterDataView.as_view(), name='new_screens'),
    path('screenings', views.ScreeningsLoaderView.as_view(), name='screenings'),
    path('film_backup', views.FilmDataBackupView.as_view(), name='film_backup'),
]
