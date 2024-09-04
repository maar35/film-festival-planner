from django.urls import path

from loader import views

app_name = 'loader'
urlpatterns = [
    path('ratings', views.RatingsLoaderView.as_view(), name='ratings'),
    path('sections', views.SectionsLoaderView.as_view(), name='sections'),
    path('theaters', views.TheaterDataInterfaceView.as_view(), name='theaters'),
    path('new_screens', views.NewTheaterDataView.as_view(), name='new_screens'),
    path('list_action', views.SingleTemplateListView.as_view(), name='list_action'),
    path('film_backup', views.FilmDataBackupView.as_view(), name='film_backup'),
    path('<int:pk>/dump_data', views.SingleTemplateDumperView.as_view(), name='dump_data')
]
