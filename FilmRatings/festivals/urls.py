from django.urls import path

from festivals import views

app_name = 'festivals'
urlpatterns = [
    # Index path.
    path('', views.IndexView.as_view(), name='index'),

    # Details path.
    # Example: /festivals/5/
    path('<int:festival_id>/', views.detail, name='detail'),

    # Test path.
    path('test_default_festival', views.test_default_festival, name='test_default_festival')
]
