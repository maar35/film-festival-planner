from django.urls import path

from exercises import views

app_name = 'exercises'
urlpatterns = [

    path('index/', views.IndexView.as_view(), name='index'),

    path('<int:pk>/detail/', views.DetailView.as_view(), name='detail'),

    # Example: /exercises/5/vote/
    path('<int:question_id>/vote/', views.vote, name='vote'),

    # Example: /exercises/5/results/
    path('<int:pk>/results/', views.ResultsView.as_view(), name='results'),
]
