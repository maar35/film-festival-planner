from django.urls import path
from django.contrib.auth.views import LogoutView

from authentication import views

app_name = 'authentication'
urlpatterns = [

    # User login/logout paths.
    path('login/', views.FilmsLoginView.as_view(), name='login'),
    path('logout/', LogoutView.as_view(), name='logout'),

    # Logout redirect path.
    path('logged_out/', views.logout, name='logged_out'),
]