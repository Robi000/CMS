from django.urls import path
from API import views as api_views

urlpatterns = [
    path("household/", api_views.HouseholdListCreateAPIView.as_view()),
    path("household/<pk>/", api_views.HouseholdRetrieveUpdateDestroyAPIView.as_view()),
]
