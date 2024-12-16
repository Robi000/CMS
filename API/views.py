from rest_framework.exceptions import NotFound
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
from datetime import date, datetime
from rest_framework import serializers


# * -------------------------------------------------------------------------------------------------
# * ---------------------------------------- Household Views ----------------------------------------
# * -------------------------------------------------------------------------------------------------


class HouseholdListCreateAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.ListCreateAPIView):
    """
    API View to handle listing and creation of Household instances.

    Features:
        - Retrieve a list of `Household` instances, optionally filtered by a search term.
        - Create a new `Household` instance, associating it with a specific `Association`.

    Mixins:
        - `api_mixins.GetOnlySameAssociateData`: Restricts data access to only the associated user's data.

    HTTP Methods:
        - GET: List households, filtered by query parameters (e.g., search).
        - POST: Create a new household.

    Attributes:
        queryset (QuerySet): Default queryset for Household instances.
        serializer_class (Serializer): Serializer for serializing and deserializing `Household` data.
        permission_classes (list): List of permission classes applied to the view.
        look_up_field (str): Field used for lookup in the API.
    """

    queryset = api_model.Household.objects.all()
    serializer_class = api_serializers.HouseholdSerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def list(self, request, *args, **kwargs):
        """
        Retrieve and return a list of households with a custom message wrapper.

        Overrides the default list method to include a custom message in the response,
        while still utilizing the base queryset filtering.

        Args:
            request: The HTTP GET request.

        Returns:
            Response: A JSON response containing a custom message and serialized data.
        """
        queryset = self.get_queryset()

        search_term = self.request.GET.get('search', None)
        print(type(search_term), search_term)

        if search_term:
            queryset = queryset.filter(
                Q(contact_number__icontains=search_term) |
                Q(head_of_household__icontains=search_term)
            )

        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'custom_message': "This is a custom message",
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """
        Create a new Household instance.

        Retrieves the necessary fields from the request data, associates the household
        with an `Association`, and creates a new record in the database. This method
        also sets the Association dynamically in the future (commented in code).

        Args:
            request: The HTTP POST request containing household data.

        Returns:
            Response: A JSON response with the serialized new household data and a 201 status.
        """
        Association = request.data.get(
            'Association')  # Temporary: Remove in production
        Association = api_model.Association.objects.get(
            id=Association)  # Temporary: Remove in production

        # ! In production, grab the user's association instance and check if the inserted building no is inside the user assossication number
        # Association = self.request.user.association
        # if request.data.get('building_no') in Association.building_numbers

        new_household = api_model.Household.objects.create(
            Association=Association,
            apartment_number=request.data.get('apartment_number'),
            building_no=request.data.get('building_no'),
            head_of_household=request.data.get('head_of_household'),
            contact_number=request.data.get('contact_number'),
            email=request.data.get('email'),
            is_rented=request.data.get('is_rented'),
            is_empty_daytime=request.data.get('is_empty_daytime'),
            documents=request.data.get('documents'),
        )

        serializer = self.get_serializer_class()(
            new_household, context={'request': request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class HouseholdRetrieveUpdateDestroyAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.RetrieveUpdateDestroyAPIView):
    """
    API View for retrieving, updating, and deleting a specific Household instance.

    Features:
        - Retrieve a household along with its associated current and old members.
        - Update a household's data with field restrictions.
        - Delete a household instance.

    Mixins:
        - `api_mixins.GetOnlySameAssociateData`: Restricts data access to only the associated user's data.

    HTTP Methods:
        - GET: Retrieve details of a specific household and its members.
        - PUT/PATCH: Update specific fields of a household.
        - DELETE: Delete a household instance.

    Attributes:
        queryset (QuerySet): Default queryset for Household instances.
        serializer_class (Serializer): Serializer for serializing and deserializing `Household` data.
        permission_classes (list): List of permission classes applied to the view.
        look_up_field (str): Field used for lookup in the API.
    """

    queryset = api_model.Household.objects.all()
    serializer_class = api_serializers.HouseholdSerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def retrieve(self, request, *args, **kwargs):
        """
        Retrieve a specific household instance and its members.

        Extends the default `retrieve` method to include additional data about the household's
        members. It separates members into `current_members` and `old_members` based on the
        `current_member` flag.

        Args:
            request: The HTTP GET request.

        Returns:
            Response: A JSON response containing serialized household data along with
            current and old household members.
        """
        instance = self.get_object()
        serializer = self.get_serializer(instance)
        data = serializer.data

        house_members = api_model.HouseholdMember.objects.filter(
            household=instance)

        current_members = api_serializers.HouseholdMemberSerializer(
            house_members.filter(current_member=True), many=True
        )
        old_members = api_serializers.HouseholdMemberSerializer(
            house_members.filter(current_member=False), many=True
        )

        data['current_members'] = current_members.data
        data['old_members'] = old_members.data

        return Response(data)

    def update(self, request, *args, **kwargs):
        """
        Update specific fields of a household instance.

        Restricts updates to a predefined set of fields (`allowed_fields`) to ensure only
        intended modifications can be made. The method uses partial updates by default.

        Args:
            request: The HTTP PUT/PATCH request containing fields to update.

        Returns:
            Response: A JSON response with the updated household data and a 200 status.
        """
        allowed_fields = ["head_of_household", "contact_number",
                          "is_rented", "is_empty_daytime", "documents"]
        filtered_data = {key: value for key,
                         value in request.data.items() if key in allowed_fields}

        instance = self.get_object()
        serializer = self.get_serializer(
            instance, data=filtered_data, partial=True)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)

        return Response({"message": "Updated successfully", "data": serializer.data}, status=status.HTTP_200_OK)

    def perform_update(self, serializer):
        """
        Save the updates made to a household instance.

        This method is called internally by the `update` method to finalize the update
        process and persist changes to the database.

        Args:
            serializer (Serializer): The serializer instance with validated data.
        """
        serializer.save()


class HouseholdLeaveProtocol(APIView):

    def get(self, request, pk):

        house_hold = api_model.Household.objects.get(pk=pk)

        house_members = api_model.HouseholdMember.objects.filter(
            household=house_hold).filter(current_member=True)
        print(house_hold, "\n\n\n\n", house_members)

        house_hold = api_serializers.HouseholdSerializer(house_hold).data
        house_members = api_serializers.HouseholdMemberSerializer(
            house_members, many=True).data

        return Response({"house_hold": house_hold, "house_members": house_members})

    def post(self, request, pk):
        house_hold = api_model.Household.objects.get(pk=pk)

        house_members = api_model.HouseholdMember.objects.filter(
            household=house_hold).filter(current_member=True)

        for member in house_members:
            member.current_member = False
            member.save()

        house_hold = api_serializers.HouseholdSerializer(house_hold).data
        house_members = api_serializers.HouseholdMemberSerializer(
            house_members, many=True).data

        return Response({"message": "succussfuly updated", "data": {"house_hold": house_hold, "house_members": house_members}})


# * -------------------------------------------------------------------------------------------------
# * ------------------------------------- HouseholdMember Views -------------------------------------
# * -------------------------------------------------------------------------------------------------


class HouseholdMemberListCreateAPIView(
        api_mixins.GetOnlyUserHouseholdMemberData,
        generics.ListCreateAPIView):

    queryset = api_model.HouseholdMember.objects.all()
    serializer_class = api_serializers.HouseholdMemberSerializer
    permission_classes = [AllowAny]
    look_up_field = "household__Association"

    def list(self, request, *args, **kwargs):
        """
        Retrieve and return a list of HouseholdMember with a custom message wrapper.

        Overrides the default list method to include a custom message in the response,
        while still utilizing the base queryset filtering.

        Args:
            request: The HTTP GET request.

        Returns:
            Response: A JSON response containing a custom message and serialized data.
        """
        queryset = self.get_queryset()

        search_term = self.request.GET.get('search', None)
        print(type(search_term), search_term)

        if search_term:
            queryset = queryset.filter(
                Q(contact_number__icontains=search_term) |
                Q(name__icontains=search_term)
            ).order_by('-current_member', 'name')

        serializer = self.get_serializer(queryset, many=True)

        return Response({
            'custom_message': "This is a custom message",
            'data': serializer.data
        }, status=status.HTTP_200_OK)


class HouseholdMemberRetrieveUpdateDestroyAPIView(
        api_mixins.GetOnlyUserHouseholdMemberData,
        generics.RetrieveUpdateDestroyAPIView):

    queryset = api_model.HouseholdMember.objects.all()
    serializer_class = api_serializers.HouseholdMemberSerializer
    permission_classes = [AllowAny]
    look_up_field = "household__Association"

    def update(self, request, *args, **kwargs):
        object = self.get_object()
        data = {
            key: value for key, value in {
                'name': request.data.get('name'),
                'age': request.data.get('age'),
                'sex': request.data.get('sex'),
                'role': request.data.get('role'),
                'occupation': request.data.get('occupation'),
                'contact_number': request.data.get('contact_number'),
                'current_member': request.data.get('current_member'),
            }.items() if value is not None
        }

        for key, value in data.items():
            setattr(object, key, value)

        # Save the updated object
        object.save()
        serailizer = self.get_serializer(object)

        return Response(serailizer.data, status=status.HTTP_200_OK)


# * -------------------------------------------------------------------------------------------------
# * ------------------------------------- FinancialSummary Views -------------------------------------
# * -------------------------------------------------------------------------------------------------


class FinancialSummaryRetrieveAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.RetrieveAPIView):

    queryset = api_model.FinancialSummary.objects.all()
    serializer_class = api_serializers.FinancialSummarySerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def get_object(self):
        try:
            # Association = self.request.user.association
            # obj = api_model.FinancialSummary.objects.get(Association=Association)
            # ! please uncomment the above when the authentiion is setupeed
            obj = api_model.FinancialSummary.objects.first()  # ! and remove this
        except api_model.FinancialSummary.DoesNotExist:
            raise NotFound("Object not found")

        return obj


# * -------------------------------------------------------------------------------------------------
# * ----------------------------------------- Invoice  Views ----------------------------------------
# * -------------------------------------------------------------------------------------------------


class InvoiceListAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.ListCreateAPIView):

    queryset = api_model.Invoice.objects.all()
    serializer_class = api_serializers.InvoiceSerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def list(self, request, *args, **kwargs):
        """
        Retrieve and return a list of households with a custom message wrapper.

        Overrides the default list method to include a custom message in the response,
        while still utilizing the base queryset filtering.

        Args:
            request: The HTTP GET request.

        Returns:
            Response: A JSON response containing a custom message and serialized data.
        """
        queryset = self.get_queryset()

        search_term = self.request.GET.get('status', None)
        print(type(search_term), search_term)

        if search_term:
            search_term = True if search_term == "paid" else False
            queryset = queryset.filter(is_paid=search_term)

        search_term = self.request.GET.get('owner', None)
        print(search_term, "**"*8)
        if search_term:
            queryset = queryset.filter(
                household__head_of_household__icontains=search_term)

        search_term = self.request.GET.get('due', None)
        if search_term:
            queryset = queryset.filter(
                due_date__lt=date.today())

        for invoice in queryset:
            invoice.calculate_penalty()

        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'custom_message': "This is a custom message",
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        homes = request.data.get('homes')

        data = {
            "amount": request.data.get('amount'),
            "description": request.data.get('description'),
            "due_date": request.data.get('due_date'),
            "created_by": request.data.get('created_by'),
        }

        if 'due_date' in data:
            if isinstance(data['due_date'], str):
                data['due_date'] = datetime.strptime(
                    data['due_date'], "%Y-%m-%d").date()
            elif isinstance(data['due_date'], datetime):
                data['due_date'] = data['due_date'].date()
        if data['due_date'] < date.today():
            raise serializers.ValidationError(
                {"due_date": "The 'due_date' cannot be in the past."})
        created_invoices = []  # To store created invoice objects

        for home in homes:
            data.update(
                {"household": api_model.Household.objects.get(pk=home)})
            print(f"i was here {home}")
            invoice = api_model.Invoice.objects.create(**data)
            print(f"i was here {home}")
            created_invoices.append(invoice.id)

        data = []
        for x in created_invoices:
            data.append(api_model.Invoice.objects.get(id=x))

        data = api_serializers.InvoiceSerializer(data, many=True).data

        return Response({
            # Serialized data of created invoices
            'custom_message': "Invoices created successfully",
            "instances": data
        }, status=status.HTTP_201_CREATED)
        # return super().create(request, *args, **kwargs)
