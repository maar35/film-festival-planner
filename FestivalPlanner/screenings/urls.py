from django.urls import path

from . import views

app_name = 'screenings'
urlpatterns = [
    path('day_schema/', views.DaySchemaView.as_view(), name='day_schema'),
    path('<int:pk>/details/', views.ScreeningDetailView.as_view(), name='details'),
    path('planner/', views.PlannerView.as_view(), name='planner'),
    path('calendar/', views.ScreeningCalendarView.as_view(), name='calendar'),
    path('warnings/', views.ScreeningWarningsView.as_view(), name='warnings'),
]
