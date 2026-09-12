from django.urls import path
from routes.views import HealthCheckView, RoutePlanView
app_name='routes'
urlpatterns=[path('health/',HealthCheckView.as_view(),name='health-check'),path('route/',RoutePlanView.as_view(),name='route-plan')]
