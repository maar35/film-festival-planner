from django.urls import path
from festivals import views

app_name = 'festivals'
urlpatterns = [
    path('', views.IndexView.as_view(), name='festival_index'),

    # Example: /festivals/5/
    path('<int:pk>/', views.DetailView.as_view(), name='detail_page'),
    # path('<int:id>/', views.detail, name='detail_page',)
]
