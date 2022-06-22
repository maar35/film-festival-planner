from django.urls import path

from festivals import views

app_name = 'festivals'
urlpatterns = [
    path('', views.IndexView.as_view(), name='index'),

    # Example: /festivals/5/
    path('<int:festival_id>/', views.detail, name='detail'),
]
