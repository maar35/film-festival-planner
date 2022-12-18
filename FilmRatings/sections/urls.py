from django.urls import path

from sections import views

app_name = 'sections'
urlpatterns = [
    path('index', views.IndexView.as_view(), name='index')
]
