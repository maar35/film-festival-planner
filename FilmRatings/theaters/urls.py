from django.urls import path

from theaters import views

app_name = 'theaters'
urlpatterns = [
    path('theaters', views.IndexView.as_view(), name='theaters')
]
