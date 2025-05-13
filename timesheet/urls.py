from django.urls import path
from .views.time_entry_view import TimesheetEntryView
from .views.time_overview_view import TimesheetOverviewView, TimesheetDailyView

app_name = 'timesheet'

urlpatterns = [
    path('day/<str:date>/<uuid:staff_id>/',
         TimesheetEntryView.as_view(),
         name='timesheet_entry'),
    path('overview/',
         TimesheetOverviewView.as_view(),
         name='timesheet_overview'),
    path('overview/<str:start_date>/',
         TimesheetOverviewView.as_view(),
         name='timesheet_overview_with_date'),
    path('daily/<str:date>/',
         TimesheetDailyView.as_view(),
         name='timesheet_daily_view'),
]
