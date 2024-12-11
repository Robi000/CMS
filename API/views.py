from rest_framework import status
from rest_framework.decorators import api_view, APIView
from rest_framework.response import Response
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework import generics
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.decorators import api_view, permission_classes
from rest_framework_simplejwt.tokens import RefreshToken
from django.http import JsonResponse
from API import models as api_model
from API import serializers as api_serializers
from API import mixins as api_mixins
from django.db.models import Q
# Create your views here.


class HouseholdListCreateAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.ListCreateAPIView):

    queryset = api_model.Household.objects.all()
    serializer_class = api_serializers.HouseholdSerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def get_queryset(self):
        """
        Overrides the default `get_queryset` method to filter results
        based on the `search` query parameter in GET requests.

        Returns:
            QuerySet: The filtered queryset based on the search term.
        """
        queryset = self.queryset.all()
        search_term = self.request.GET.get('search', None)
        print(type(search_term), search_term)

        if search_term:
            # Perform case-insensitive search across multiple fields
            # (Customize 'search_fields' as needed)
            # Replace with relevant fields
            queryset = queryset.filter(Q(contact_number__icontains=search_term) | Q(
                head_of_household__icontains=search_term))

        return queryset

    def list(self, request, *args, **kwargs):
        # Call the parent list method to get the filtered queryset
        queryset = self.get_queryset()
        serializer = self.get_serializer(queryset, many=True)

        # Wrap the original data with a custom message
        return Response({
            'custom_message': "This is a custom message",
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):

        Association = request.data.get('Association')  # ! remove this latter
        Association = api_model.Association.objects.get(
            id=Association)  # ! remove this latter

        # todo grab the user  assossiation instance and fill it there
        # Association = self.request.user.association

        apartment_number = request.data.get('apartment_number')
        building_no = request.data.get('building_no')
        head_of_household = request.data.get('head_of_household')
        contact_number = request.data.get('contact_number')
        email = request.data.get('email')
        is_rented = request.data.get('is_rented')
        is_empty_daytime = request.data.get('is_empty_daytime')
        documents = request.data.get('documents')

        new_household = api_model.Household.objects.create(
            Association=Association,
            apartment_number=apartment_number,
            building_no=building_no,
            head_of_household=head_of_household,
            contact_number=contact_number,
            email=email,
            is_rented=is_rented,
            is_empty_daytime=is_empty_daytime,
            documents=documents,
        )

        serializer_class = self.get_serializer_class()
        serializer = serializer_class(
            new_household, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HouseholdRetrieveUpdateDestroyAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.RetrieveUpdateDestroyAPIView):

    queryset = api_model.Household.objects.all()
    serializer_class = api_serializers.HouseholdSerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        house_members = api_model.HouseholdMember.objects.filter(
            household=instance)

        current_members = house_members.filter(current_member=True)
        old_members = house_members.filter(current_member=False)

        current_members = api_serializers.HouseholdMemberSerializer(
            current_members, many=True)
        old_members = api_serializers.HouseholdMemberSerializer(
            old_members, many=True)

        data['current_members'] = current_members.data
        data['old_members'] = old_members.data

        return Response(data)

    def update(self, request, *args, **kwargs):
        # Extract only allowed fields from the request data
        allowed_fields = ["head_of_household", "contact_number",
                          "is_rented", "is_empty_daytime", "documents"]
        filtered_data = {key: value for key,
                         value in request.data.items() if key in allowed_fields}

        # Pass the filtered data to the serializer
        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=filtered_data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        return Response({"message": "Updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        serializer.save()
