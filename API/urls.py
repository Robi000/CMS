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


    path("invoice/process/",
         api_views.InvoiceUpdateDelete.as_view()),

    path("invoice/detail/<pk>/",
         api_views.InvoiceRetrieveAPIView.as_view()),

    path("invoice/house/<pk>/",
         api_views.InvoiceHandleHouseHold.as_view()),


    # *  ---------------------- FinancialTransaction pathes ----------------------

    path("FinTxn/",
         api_views.FinancialTransactionListCreateAPIView.as_view()),
    path("FinTxn/update/",
         api_views.FinancialTransactionUpdate.as_view()),

    # *  ---------------------------- Event pathes --------------------------

    path("event/", api_views.EventListCreateAPIView.as_view()),
    path("event/attendance/", api_views.EventAttendanceUpdateAPIView.as_view()),
    path("event/retrive/<pk>/", api_views.EventRetrieveDestroyAPIView.as_view()),


    path('projects/', api_views.ProjectListCreateView.as_view(),
         name='project-list-create'),
    path('projects/<int:pk>/',
         api_views.ProjectRetrieveUpdateDestroyView.as_view(), name='project-detail'),

    # URLs for ProjectProgress
    path('progress/', api_views.ProjectProgressCreateView.as_view(),
         name='progress-list-create'),
    path('progress/<int:pk>/',
         api_views.ProjectProgressRetrieveUpdateDestroyView.as_view(), name='progress-detail'),

]
