"""FilmRatings URL Configuration

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/3.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""

from django.conf.urls import include
from django.contrib import admin
from django.urls import path

# from django.contrib import admin

urlpatterns = [
    path('admin/', admin.site.urls, name='admin'),
    path('authentication/', include('authentication.urls')),
    path('film_list/', include('film_list.urls')),
    path('festivals/', include('festivals.urls')),
    path('loader/', include('loader.urls')),
    path('sections/', include('sections.urls')),
    path('theaters/', include('theaters.urls')),
    path('exercises/', include('exercises.urls')),
]

admin.autodiscover()

# urlpatterns = [path(None, r'^admin/', include(admin.site.urls))]
