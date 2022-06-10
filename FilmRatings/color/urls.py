from django.urls import path
from . import views

app_name = 'color'
urlpatterns = [
    path('color/', views.color, name='color'),
]