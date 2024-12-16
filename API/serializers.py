from datetime import date, datetime
from rest_framework import serializers
from API import models as api_model
from django.shortcuts import render
from django.http import JsonResponse
from decimal import Decimal


class HouseholdSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_model.Household
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(HouseholdSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1

    def update(self, instance, validated_data):
        # Allow only specific fields to be updated
        allowed_fields = ["head_of_household", "contact_number",
                          "is_rented", "is_empty_daytime", "documents"]
        for field in allowed_fields:
            if field in validated_data:
                setattr(instance, field, validated_data[field])
        instance.save()
        return instance


class HouseholdMemberSerializer(serializers.ModelSerializer):
    class Meta:
        model = api_model.HouseholdMember
        fields = "__all__"

    def __init__(self, *args, **kwargs):
        super(HouseholdMemberSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1


class FinancialSummarySerializer(serializers.ModelSerializer):
    add_income = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, write_only=True
    )
    deduct_expense = serializers.DecimalField(
        max_digits=15, decimal_places=2, required=False, write_only=True
    )

    class Meta:
        model = api_model.FinancialSummary
        fields = ['id', 'total_balance', 'Association',
                  'add_income', 'deduct_expense']
        read_only_fields = ['id', 'total_balance']

    def __init__(self, *args, **kwargs):
        super(FinancialSummarySerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1

    def validate_add_income(self, value):
        """Validate the income amount is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Income amount must be positive.")
        return value

    def validate_deduct_expense(self, value):
        """Validate the expense amount is positive and within the balance."""
        instance = self.instance
        if value <= 0:
            raise serializers.ValidationError(
                "Expense amount must be positive.")
        if instance and value > instance.total_balance:
            raise serializers.ValidationError(
                "Insufficient balance for this expense.")
        return value

    def update(self, instance, validated_data):
        """Handle adding income or deducting expense."""
        if 'add_income' in validated_data:
            instance.add_income(validated_data.pop('add_income'))
        if 'deduct_expense' in validated_data:
            instance.deduct_expense(validated_data.pop('deduct_expense'))
        return super().update(instance, validated_data)


class InvoiceSerializer(serializers.ModelSerializer):
    # Nested household information
    household_name = serializers.CharField(
        source="household.head_of_household", read_only=True)
    due_date = serializers.DateField(format="%Y-%m-%d")
    # Custom fields for displaying status
    status = serializers.SerializerMethodField()

    class Meta:
        model = api_model.Invoice
        fields = (
            'id',
            'household',
            'household_name',
            'amount',
            'description',
            'due_date',
            'is_paid',
            'issued_date',
            'penalty',
            'created_by',
            'payment_accepted_by',
            "payment_date",
            'status',
        )
        read_only_fields = ('penalty', 'issued_date', 'status')

    def __init__(self, *args, **kwargs):
        super(InvoiceSerializer, self).__init__(*args, **kwargs)
        request = self.context.get('request')
        if request and request.method == 'POST':
            self.Meta.depth = 0
        else:
            self.Meta.depth = 1

    def get_status(self, obj):
        """Determine invoice status."""
        if obj.is_paid:
            return "Paid"
        elif date.today() > obj.due_date:
            return "Overdue"
        return "Pending"

    def validate_amount(self, value):
        """Ensure the amount is positive."""
        if value <= 0:
            raise serializers.ValidationError(
                "Invoice amount must be greater than zero.")
        return value

    def validate_created_by(self, value):
        """Ensure the creator's name is provided."""
        if not value.strip():
            raise serializers.ValidationError(
                "Created by field cannot be empty.")
        return value

    def validate(self, attrs):
        """Perform additional validations."""
        if attrs.get('is_paid') and attrs.get('penalty') > 0:
            raise serializers.ValidationError(
                "An invoice marked as paid should not have a penalty."
            )
        return attrs

    def validate_due_date(self, value):
        """Ensure `due_date` is a valid `date` object and is in the future."""
        if isinstance(value, datetime):  # Convert to date if necessary
            value = value.date()
        elif not isinstance(value, date):
            raise serializers.ValidationError(
                "Invalid `due_date`. Expected a `date` object."
            )
        if value < date.today():
            raise serializers.ValidationError(
                "Due date cannot be in the past.")
        return value

    def create(self, validated_data):
        """Handle custom logic during creation."""
        instance = super().create(validated_data)  # Calculate penalty before saving
        instance.save()
        return instance

    def update(self, instance, validated_data):
        """Handle custom logic during update."""
        is_paid_previous = instance.is_paid
        instance = super().update(instance, validated_data)

        # Recalculate penalty if invoice is updated
        instance.calculate_penalty()
        instance.save()

        # Handle financial summary updates only if payment status changes
        if not is_paid_previous and instance.is_paid:
            from .models import FinancialSummary  # Import here to avoid circular imports
            financial_summary = FinancialSummary.objects.filter(
                Association=instance.household.Association).first()
            if financial_summary:
                financial_summary.add_income(
                    instance.amount + instance.penalty)

        return instance
