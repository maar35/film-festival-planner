from django.urls import path

from loader import views

app_name = 'loader'
urlpatterns = [
    path('ratings', views.RatingsLoaderView.as_view(), name='ratings'),
    path('sections', views.SectionsLoaderView.as_view(), name='sections'),
    path('theaters', views.TheaterDataInterfaceView.as_view(), name='theaters'),
    path('new_screens', views.NewTheaterDataView.as_view(), name='new_screens'),
]
