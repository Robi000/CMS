from .serializers import ProjectSerializer, ProjectProgressSerializer
from .models import Project, ProjectProgress
from django.db.models import Sum
import uuid
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
    permission_classes = [IsAuthenticated]
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
        # Temporary: Remove in production
        Association = self.request.user.association  # Temporary: Remove in production
        existing_household = api_model.Household.objects.filter(
            Association=Association,
            building_no=request.data.get('building_no'),
            apartment_number=request.data.get('apartment_number')
        ).exists()

        if existing_household:
            raise serializers.ValidationError(
                {"error": "A household with the same association, building number, and apartment number already exists."}
            )

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
    permission_classes = [IsAuthenticated]
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
    """
    API view for retrieving, updating, and deleting a household member.

    Methods:
        - GET: Retrieve a household member's details.
        - PUT/PATCH: Update specific fields of a household member.
        - DELETE: Remove a household member from the database.

    Attributes:
        queryset: All `HouseholdMember` objects.
        serializer_class: Serializer class for `HouseholdMember`.
        permission_classes: Specifies the permission required for accessing this API.
        look_up_field: Field used to identify a household member based on the association.

    Custom Methods:
        - update: Updates only the provided fields of the household member.
    """
    queryset = api_model.HouseholdMember.objects.all()
    serializer_class = api_serializers.HouseholdMemberSerializer
    permission_classes = [AllowAny]
    look_up_field = "household__Association"

    def update(self, request, *args, **kwargs):
        """
        Updates specific fields of a household member.

        Args:
            request: The HTTP PUT or PATCH request containing updated data.
            *args: Additional positional arguments.
            **kwargs: Additional keyword arguments.

        Returns:
            Response: A JSON response containing the updated household member data.
        """
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
    """
    API view for retrieving financial summary data.

    Methods:
        - GET: Retrieve financial summary details for an association.

    Attributes:
        queryset: All `FinancialSummary` objects.
        serializer_class: Serializer class for `FinancialSummary`.
        permission_classes: Specifies the permission required for accessing this API.
        look_up_field: Field used to identify a financial summary based on the association.

    Custom Methods:
        - get_object: Retrieves a financial summary for a given association.
    """

    queryset = api_model.FinancialSummary.objects.all()
    serializer_class = api_serializers.FinancialSummarySerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def get_object(self):
        """
        Retrieves a single financial summary object for the authenticated user.

        Returns:
            FinancialSummary: The financial summary object.

        Raises:
            NotFound: If no financial summary is found.
        """
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
    """
    API view for listing and creating invoices.

    Methods:
        - GET: Retrieve a list of invoices with optional filtering.
        - POST: Create multiple invoices for households.

    Attributes:
        queryset: All `Invoice` objects.
        serializer_class: Serializer class for `Invoice`.
        permission_classes: Specifies the permission required for accessing this API.
        look_up_field: Field used to identify invoices based on the association.

    Custom Methods:
        - list: Retrieves invoices with optional filtering and a custom response.
        - create: Creates multiple invoices for specified households or an association.
    """
    queryset = api_model.Invoice.objects.all()
    serializer_class = api_serializers.InvoiceSerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"

    def list(self, request, *args, **kwargs):
        """
        Retrieves and returns a list of invoices with optional filtering.

        Args:
            request: The HTTP GET request.

        Returns:
            Response: A JSON response containing the invoices and metadata.
        """
        queryset = self.get_queryset()
        group_list = list(queryset.values_list('group', flat=True).distinct())

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

        if request.data.get("from-date"):
            try:
                print(" checked hello ")
                # Parse the from-date from the request
                from_date = datetime.strptime(
                    request.data.get("from-date"), "%Y-%m-%d").date()

                # Filter the queryset to include records with a date >= from_date
                queryset = queryset.filter(issued_date__gte=from_date)
            except ValueError:
                return Response({"error": "Invalid 'from-date' format. Use 'YYYY-MM-DD'."}, status=400)
        if request.data.get("to-date"):
            print("checked")
            try:
                to_date = datetime.strptime(
                    request.data.get("to-date"), "%Y-%m-%d").date()
                queryset = queryset.filter(issued_date__lte=to_date)
            except ValueError:
                return Response({"error": "Invalid 'to-date' format. Use 'YYYY-MM-DD'."}, status=400)

        if request.data.get("from-date_p"):
            try:
                # Parse the from-date from the request
                from_date = datetime.strptime(
                    request.data.get("from-date"), "%Y-%m-%d").date()

                # Filter the queryset to include records with a date >= from_date
                queryset = queryset.filter(payment_date__gte=from_date)
            except ValueError:
                return Response({"error": "Invalid 'from-date' format. Use 'YYYY-MM-DD'."}, status=400)
        if request.data.get("to-date_p"):
            try:
                to_date = datetime.strptime(
                    request.data.get("to-date"), "%Y-%m-%d").date()
                queryset = queryset.filter(payment_date__lte=to_date)
            except ValueError:
                return Response({"error": "Invalid 'to-date' format. Use 'YYYY-MM-DD'."}, status=400)

        for invoice in queryset:
            invoice.calculate_penalty()

        search_term = self.request.GET.get('group', None)
        if search_term:
            queryset = queryset.filter(group=search_term)
        print(len(queryset))
        serializer = self.get_serializer(queryset, many=True)
        return Response({
            'custom_message': "This is a custom message",
            "group_list": group_list,
            'data': serializer.data
        }, status=status.HTTP_200_OK)

    def create(self, request, *args, **kwargs):
        """
        Creates invoices for households or an entire association.

        Args:
            request: The HTTP POST request containing invoice data.

        Returns:
            Response: A JSON response containing the created invoice data.
        """
        homes = request.data.get('homes')
        # ! homes is "ALL" then extract user , then assossiation , then create for all homes in assossiation
        data = {
            "amount": request.data.get('amount'),
            "description": request.data.get('description'),
            "due_date": request.data.get('due_date'),
            "created_by": request.data.get('created_by'),
            "group": str(uuid.uuid4()).replace('-', '')[:7]
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

        group = uuid.uuid4

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


class InvoiceRetrieveAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.RetrieveAPIView):
    """
    API view for retrieving a single invoice.

    Methods:
        - GET: Retrieve details of a specific invoice.

    Attributes:
        queryset: All `Invoice` objects.
        serializer_class: Serializer class for `Invoice`.
        permission_classes: Specifies the permission required for accessing this API.
        look_up_field: Field used to identify invoices based on the association.
    """

    queryset = api_model.Invoice.objects.all()
    serializer_class = api_serializers.InvoiceSerializer
    permission_classes = [AllowAny]
    look_up_field = "Association"


class InvoiceUpdateDelete(APIView):
    """
    API view for updating or deleting invoices.

    Methods:
        - PUT: Marks invoices or groups of invoices as paid.
        - DELETE: Deletes unpaid invoices or groups of invoices.

    Custom Behavior:
        - Handles group-based operations for invoices.

    Custom Methods:
        - put: Updates payment status for individual or grouped invoices.
        - delete: Deletes unpaid invoices individually or in a group."""

    def put(self, request, *args, **kwargs):
        """
        Marks invoices or groups of invoices as paid.

        Args:
            request: The HTTP PUT request containing invoice IDs or a group identifier.

        Returns:
            Response: A JSON response indicating the success of the operation, 
                      along with the updated amount and count.
        """

        # ! handle payment accpeted by.. set the user name here

        user = request.user
        user_name = user.first_name + " " + user.last_name

        if request.data.get("invoices"):
            amount = 0
            updated = 0
            for id in request.data.get("invoices"):
                try:
                    obj = api_model.Invoice.objects.get(id=id)
                    if not (obj.is_paid):
                        amount += obj.amount + obj.penalty
                        obj.is_paid = True
                        obj.payment_date = date.today()
                        obj.payment_accepted_by = user_name
                        obj.save()
                        updated += 1

                except:
                    print("passed")
            if amount == 0 and updated == 0:
                return Response({"error": "something went wrong:"})
            return Response({"message": f"successfully paid {updated} invoices", "updated": updated, "paid_amount": amount})

        elif request.data.get("group"):
            amount = 0
            updated = 0
            qs = api_model.Invoice.objects.filter(
                group=request.data.get("group"))
            for obj in qs:
                try:
                    if not (obj.is_paid):
                        amount += obj.amount + obj.penalty
                        obj.is_paid = True
                        obj.save()
                        updated += 1
                except:
                    print("passed 2")
            if amount == 0 and updated == 0:
                return Response({"error": "something went wrong:"})
            return Response({"message": f"successfully paid {updated} invoices", "updated": updated, "paid_amount": amount})
        print("hello")

        if not request.data.get("invoices") and not request.data.get("group"):
            return Response({"error": "No invoices or group provided"})

    def delete(self, request, *args, **kwargs):
        """
        Deletes unpaid invoices individually or in a group.

        Args:
            request: The HTTP DELETE request containing invoice IDs or a group identifier.

        Returns:
            Response: A JSON response indicating the success of the operation, 
                      along with the deleted amount and count.
        """
        if request.data.get("invoices"):
            count = 0
            amount = 0
            for id in request.data.get("invoices"):
                try:
                    obj = api_model.Invoice.objects.get(id=id)
                    obj.calculate_penalty()
                    if not (obj.is_paid):
                        amount += obj.amount + obj.penalty
                        obj.delete()
                        count += 1
                except:
                    print("passed")
            if amount == 0 and count == 0:
                return Response({"error": "something went wrong:"})
            return Response({"message": f"successfully deleted {count} invoices", "deleted": count, "deleted_amount": amount})
        elif request.data.get("group"):
            amount = 0
            count = 0
            qs = api_model.Invoice.objects.filter(
                group=request.data.get("group"))
            for obj in qs:
                try:
                    if not (obj.is_paid):
                        amount += obj.amount + obj.penalty
                        obj.delete()
                        count += 1
                except:
                    print("passed 2")
            if amount == 0 and count == 0:
                return Response({"error": "something went wrong:"})
            return Response({"message": f"successfully deleted {count} invoices", "deleted": count, "deleted_amount": amount})

        if not request.data.get("invoices") and not request.data.get("group"):
            return Response({"error": "No invoices or group provided"})


class InvoiceHandleHouseHold(APIView):
    """
    API view for handling invoices related to a specific household.

    Methods:
        - GET: Retrieve details about a household's invoices (paid and unpaid).
        - POST: Mark all unpaid invoices of a household as paid.
        - DELETE: Delete all unpaid invoices of a household.

    Attributes:
        permission_classes: List of permissions required for this API view.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk, *args, **kwargs):
        """
        Retrieve details of a household's invoices.

        Args:
            request: The HTTP GET request.
            pk: Primary key of the household.

        Returns:
            Response: A JSON response containing the household data, unpaid and paid invoices,
                      and the total amounts for each category.
        """
        household = api_model.Household.objects.filter(pk=pk)
        if household.exists():
            household = household[0]
            not_paid_invoice = api_model.Invoice.objects.filter(
                household=household).filter(is_paid=False)
            for obj in not_paid_invoice:
                obj.calculate_penalty()

            paid_invoice = api_model.Invoice.objects.filter(
                household=household).filter(is_paid=True)
            household = api_serializers.HouseholdSerializer(household).data
        else:
            return Response({
                "message": "something Went Wrong",
            })
        if not_paid_invoice.exists():
            not_paid = api_serializers.InvoiceHomeSerializer(
                not_paid_invoice, many=True).data
            not_paid_amount = not_paid_invoice.aggregate(Sum('amount'))[
                'amount__sum'] + paid_invoice.aggregate(Sum('penalty'))['penalty__sum']
        else:
            not_paid = []
            not_paid_amount = 0
        if paid_invoice.exists():
            paid = api_serializers.InvoiceHomeSerializer(
                paid_invoice, many=True).data
            paid_amount = paid_invoice.aggregate(Sum('amount'))[
                'amount__sum'] + paid_invoice.aggregate(Sum('penalty'))['penalty__sum']
        else:
            paid = []
            paid_amount = 0

        return Response({
            "household": household,
            "not_paid": not_paid,
            "paid": paid,
            "paid_amount": paid_amount,
            "not_paid_amount": not_paid_amount
        })

    def post(self, request, pk, *args, **kwargs):
        """
        Mark all unpaid invoices for a household as paid.

        Args:
            request: The HTTP POST request.
            pk: Primary key of the household.

        Returns:
            Response: A JSON response indicating the success of the payment operation,
                      including the total amount paid and the number of invoices updated.
        """

        user = request.user
        user_name = user.first_name + " " + user.last_name
        household = api_model.Household.objects.filter(pk=pk)
        if household.exists():
            household = household[0]
            not_paid_invoice = api_model.Invoice.objects.filter(
                household=household).filter(is_paid=False)
            amount = 0
            count = 0
            for obj in not_paid_invoice:
                obj.is_paid = True
                obj.payment_date = date.today()
                obj.payment_accepted_by = user_name
                amount += obj.amount + obj.penalty
                obj.save()
                count += 1
            return Response({
                "message": "payment successful",
                "amount": amount,
                "number_of_invoices": count
            })
        else:
            return Response({
                "message": "something Went Wrong",
            })

    def delete(self, request, pk, *args, **kwargs):
        """
        Delete all unpaid invoices for a household.

        Args:
            request: The HTTP DELETE request.
            pk: Primary key of the household.

        Returns:
            Response: A JSON response indicating the success of the deletion operation,
                      including the total amount cleared and the number of invoices deleted.
        """
        household = api_model.Household.objects.filter(pk=pk)
        if household.exists():
            household = household[0]
            not_paid_invoice = api_model.Invoice.objects.filter(
                household=household).filter(is_paid=False)
            amount = 0
            count = 0
            for obj in not_paid_invoice:
                if not obj.is_paid:
                    amount += obj.amount + obj.penalty
                    obj.delete()
                    count += 1
            if amount == 0 and count == 0:
                return Response({
                    "message": "error something went wrong"})
            return Response({
                "message": f"invoices cleard for {household}",
                "amount": amount,
                "number_of_invoices": count
            })
        else:
            return Response({
                "message": "something Went Wrong",
            })


# * -------------------------------------------------------------------------------------------------
# * ---------------------------------- FinancialTransaction  Views ----------------------------------
# * -------------------------------------------------------------------------------------------------


class FinancialTransactionListCreateAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.ListCreateAPIView):

    queryset = api_model.FinancialTransaction.objects.all()
    serializer_class = api_serializers.FinancialTransactionSerializer
    permission_classes = [IsAuthenticated]
    look_up_field = "association"

    def list(self, request, *args, **kwargs):

        qs = self.get_queryset()
        serializer = self.get_serializer()

        if request.data.get("type"):
            qs = qs.filter(type=request.data.get("type"))
        if request.data.get("from-date"):
            try:
                # Parse the from-date from the request
                from_date = datetime.strptime(
                    request.data.get("from-date"), "%Y-%m-%d").date()

                # Filter the queryset to include records with a date >= from_date
                qs = qs.filter(date__gte=from_date)
            except ValueError:
                return Response({"error": "Invalid 'from-date' format. Use 'YYYY-MM-DD'."}, status=400)
        if request.data.get("to-date"):
            try:
                to_date = datetime.strptime(
                    request.data.get("to-date"), "%Y-%m-%d").date()
                qs = qs.filter(date__lte=to_date)
            except ValueError:
                return Response({"error": "Invalid 'to-date' format. Use 'YYYY-MM-DD'."}, status=400)

        return Response({
            "amount": qs.count(),
            "data": api_serializers.FinancialTransactionSerializer(qs, many=True).data
        })

        return super().list(request, *args, **kwargs)

    def create(self, request, *args, **kwargs):
        # Retrieve the 'Association' from the request or another logic
        # association_id = request.data.get('association')
        # if not association_id:
        #     return Response({"error": "Association ID is required."}, status=status.HTTP_400_BAD_REQUEST)
        association_id = request.data.get('association')
        # Fetch the FinancialSummary object for the given Association
        # ! Grab the assosciation from the logged in user and also the user name

        user = request.user
        user_name = user.first_name + " " + user.last_name
        user_association = user.association

        financial_summary = api_model.FinancialSummary.objects.filter(
            Association__id=user_association.id).first()
        data = request.data

        data.update({"accessed_by": user_name,
                    "association": user_association.id})
        # Create a serializer instance with the context
        serializer = self.get_serializer(data=data, context={
            'financial_summary': financial_summary})
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)

        # Return the created financial transaction response
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)


class FinancialTransactionUpdate(APIView):
    def put(self, request, *args, **kwargs):
        if request.data.get("id"):
            finTxn = api_model.FinancialTransaction.objects.filter(
                id=request.data.get("id")).first()
        else:
            return Response({"error": "No id is provided'."}, status=400)

        if (request.data.get("type") and request.data.get("amount")) or request.data.get("reason"):
            print(finTxn.association, request.user.association)
            if finTxn and finTxn.association == request.user.association:
                # ! check the use is in that association first
                financial_summary = api_model.FinancialSummary.objects.filter(
                    Association=finTxn.association).first()
                if request.data.get("type") and request.data.get("amount"):
                    if finTxn.type == 'income':
                        financial_summary.deduct_expense(finTxn.amount)
                    elif finTxn.type == 'expense':
                        financial_summary.add_income(finTxn.amount)

                    finTxn.amount = request.data.get("amount")
                    finTxn.type = request.data.get("type")
                    finTxn.save()
                elif request.data.get("reason"):
                    finTxn.reason = request.data.get("reason")
                    finTxn.save(created_i=False)
                else:
                    return Response({"error": "Appropriate Infos are missing"}, status=400)

            else:
                return Response({"error": "No FINTXN have been found"}, status=400)
        else:
            return Response({"error": "Appropriate Infos are missing"}, status=400)
        serializer = api_serializers.FinancialTransactionSerializer(finTxn)
        return Response({"success": "changes are made", "data": serializer.data}, status=200)


# * -------------------------------------------------------------------------------------------------
# * ------------------------------------------ Event Views ------------------------------------------
# * -------------------------------------------------------------------------------------------------


class EventListCreateAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.ListCreateAPIView):

    queryset = api_model.Event.objects.all()
    serializer_class = api_serializers.EventSerializer
    permission_classes = [IsAuthenticated]
    look_up_field = "association"

    def list(self, request, *args, **kwargs):
        qs = self.get_queryset()
        print("*******" * 8)
        if request.data.get("from-date"):
            try:
                # Parse the from-date from the request
                from_date = datetime.strptime(
                    request.data.get("from-date"), "%Y-%m-%d").date()

                # Filter the queryset to include records with a date >= from_date
                qs = qs.filter(date__gte=from_date)
            except ValueError:
                return Response({"error": "Invalid 'from-date' format. Use 'YYYY-MM-DD'."}, status=400)
        if request.data.get("to-date"):
            try:
                to_date = datetime.strptime(
                    request.data.get("to-date"), "%Y-%m-%d").date()
                qs = qs.filter(date__lte=to_date)
            except ValueError:
                return Response({"error": "Invalid 'to-date' format. Use 'YYYY-MM-DD'."}, status=400)
        print(qs)
        seralizer = self.get_serializer(qs, many=True).data

        return Response({"data": seralizer})

    def create(self, request, *args, **kwargs):
        association_id = request.data.get('association')
        association = api_model.Association.objects.filter(
            id=association_id).first()
        # Check if the date is after the current date
        event_date = datetime.strptime(
            request.data.get('date'), "%Y-%m-%d").date()

        if event_date < date.today():
            return Response({"error": "The event date cannot be in the past."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        user_name = user.first_name + " " + user.last_name
        user_association = user.association
        # ! retrive the user and check if the user is in the association
        # ! grab the user from the logged in user and get the name of the user
        # ! retrive the association from the user
        event = api_model.Event.objects.create(
            association=user_association,
            name=request.data.get('name'),
            date=request.data.get('date'),
            created_by=user_name,
            penalty_price=request.data.get('penalty_price'),
        )
        event.create_attendance_records()
        seralizer = api_serializers.EventSerializer(event).data
        return Response({"data": seralizer})


class EventRetrieveDestroyAPIView(
        api_mixins.GetOnlySameAssociateData,
        generics.RetrieveDestroyAPIView):

    queryset = api_model.Event.objects.all()
    serializer_class = api_serializers.EventSerializer
    permission_classes = [IsAuthenticated]
    look_up_field = "association"

    def retrieve(self, request, *args, **kwargs):
        obj = self.get_object()
        eve_att = api_model.EventAttendance.objects.filter(event=obj)
        attended = api_serializers.EventAttendanceSerializer(
            eve_att.filter(attended=True), many=True).data
        absent = api_serializers.EventAttendanceSerializer(
            eve_att.filter(attended=False), many=True).data
        seralizer = self.get_serializer(obj).data
        return Response({"event": seralizer, "attended": attended, "absent": absent})

    def delete(self, request, *args, **kwargs):
        obj = self.get_object()
        if obj.date < date.today():
            return Response({"error": "The event date has passed."}, status=status.HTTP_400_BAD_REQUEST)
        return super().delete(request, *args, **kwargs)


# * -------------------------------------------------------------------------------------------------
# * ---------------------------------- EventAttendance Views ----------------------------------
# * -------------------------------------------------------------------------------------------------

class EventAttendanceUpdateAPIView(APIView):

    def put(self, request, *args, **kwargs):
        type = request.data.get("type")
        event_id = request.data.get("event_id")
        event_stat = request.data.get("event_stat")

        event = api_model.Event.objects.filter(id=event_id).first()
        if not event:
            return Response({"error": "Event not found"}, status=400)
        if type == "start" and not event.start_time:
            if not event.start_time:
                event.start_time = datetime.now()
                event.save()

        print(" 1 " * 8)
        if event_stat == "end":
            if not event.end_time:
                event.end_time = datetime.now()
                event.save()
        event_att_ids = request.data.get("event_att_ids")
        if type == "start":

            for id in event_att_ids:
                obj = api_model.EventAttendance.objects.filter(id=id).first()
                if obj:
                    obj.entry_time = datetime.now()

                    if obj.exit_time:
                        obj.exit_time = None
                    obj.save()

        elif type == "end":
            for id in event_att_ids:
                obj = api_model.EventAttendance.objects.filter(
                    id=id).first()
                if obj:
                    print(obj)
                    if not obj.exit_time:
                        obj.exit_time = datetime.now()
                    if obj.entry_time:
                        obj.attended = True
                    obj.save()

        eve_att = api_model.EventAttendance.objects.filter(event=event)

        attended = api_serializers.EventAttendanceSerializer(
            eve_att.filter(attended=True), many=True).data
        absent = api_serializers.EventAttendanceSerializer(
            eve_att.filter(attended=False), many=True).data
        event = api_model.Event.objects.filter(id=event_id).first()
        seralizer = api_serializers.EventSerializer(event).data

        return Response({"event": seralizer, "attended": attended, "absent": absent})


# * -------------------------------------------------------------------------------------------------
# * ---------------------------------- project and project progress Views ----------------------------------
# * -------------------------------------------------------------------------------------------------

# Generic views for Project

class ProjectListCreateView(
        api_mixins.GetOnlySameAssociateData,
        generics.ListCreateAPIView):

    # ! update create view so that the assossation is copid from the user assossiation
    queryset = api_model.Project.objects.all()
    serializer_class = api_serializers.ProjectSerializer
    look_up_field = "association"


class ProjectRetrieveUpdateDestroyView(
        api_mixins.GetOnlySameAssociateData,
        generics.RetrieveUpdateDestroyAPIView):
    queryset = api_model.Project.objects.all()
    serializer_class = api_serializers.ProjectSerializer
    look_up_field = "association"


# Generic views for ProjectProgress
class ProjectProgressCreateView(generics.CreateAPIView):
    queryset = api_model.ProjectProgress.objects.all()
    serializer_class = api_serializers.ProjectProgressSerializer


class ProjectProgressRetrieveUpdateDestroyView(generics.RetrieveUpdateDestroyAPIView):
    queryset = api_model.ProjectProgress.objects.all()
    serializer_class = api_serializers.ProjectProgressSerializer
