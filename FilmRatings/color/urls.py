from django.urls import path
from color import views

app_name = 'color'
urlpatterns = [
    path('html_color_index', views.html_color_index, name='html_color_index'),
    path('color/', views.color, name='color'),
    path('<int:color_id>/details/', views.details, name='details'),
    path('thanks/', views.thanks, name='thanks'),
    path('<int:color_id>/vote/', views.vote, name='vote'),
    path('<int:color_id>/results/', views.results, name='results'),
]