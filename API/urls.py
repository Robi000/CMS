from django.urls import path
from API import views as api_views

urlpatterns = [
    # *  ---------------------- household pathes ----------------------

    path("household/", api_views.HouseholdListCreateAPIView.as_view()),
    path("household/<pk>/", api_views.HouseholdRetrieveUpdateDestroyAPIView.as_view()),
    path("household/leave/<pk>/", api_views.HouseholdLeaveProtocol.as_view()),

    # *  ---------------------- householdmember pathes ----------------------

    path("householdmember/", api_views.HouseholdMemberListCreateAPIView.as_view()),
    path("householdmember/<pk>/",
         api_views.HouseholdMemberRetrieveUpdateDestroyAPIView.as_view()),




    # *  ---------------------- householdmember pathes ----------------------
    path("FinancialSummary/",
         api_views.FinancialSummaryRetrieveAPIView.as_view()),


    # *  ---------------------- Invoice pathes ----------------------
    path("invoice/",
         api_views.InvoiceListAPIView.as_view()),

]
