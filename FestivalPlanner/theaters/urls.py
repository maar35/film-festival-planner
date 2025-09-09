from django.urls import path

from theaters import views

app_name = 'theaters'
urlpatterns = [
    path('theaters', views.TheatersView.as_view(), name='theaters'),
    path('<int:pk>/details', views.TheaterView.as_view(), name='details'),
]
