from decimal import Decimal
from datetime import date, timedelta
from datetime import datetime
import os
from django.db import models
from django.contrib.auth.models import AbstractUser
from django.utils.timezone import now


# Association Model
class Association(models.Model):
    place = models.CharField(max_length=100, unique=True)
    building_number_start = models.IntegerField()
    building_number_end = models.IntegerField()

    def __str__(self):
        return f"{self.place} - {self.building_number_start} to {self.building_number_end}"


class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Admin'),
        ('committee', 'Committee'),
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, null=True)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="users", null=True)

    # Adding related_name to resolve conflicts
    groups = models.ManyToManyField(
        'auth.Group',
        related_name='customuser_set',  # Change related name here
        blank=True
    )
    user_permissions = models.ManyToManyField(
        'auth.Permission',
        related_name='customuser_set',  # Change related name here
        blank=True
    )

    def __str__(self):
        return f"{self.username} ({self.role})"


# Household Model


def household_document_path(instance, filename):
    # Extract the file extension
    extension = os.path.splitext(filename)[1]
    # Get the current timestamp
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    # Build the custom filename
    custom_name = f"{instance.building_no}_{instance.apartment_number}_{
        instance.head_of_household}_{timestamp}{extension}"
    # Return the custom path
    return f"documents/{custom_name}"


class Household(models.Model):
    Association = models.ForeignKey(Association,  on_delete=models.CASCADE)
    apartment_number = models.CharField(max_length=10)
    building_no = models.PositiveIntegerField()
    head_of_household = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    is_rented = models.BooleanField(default=False)
    is_empty_daytime = models.BooleanField(default=False)
    documents = models.FileField(
        upload_to=household_document_path, blank=True, null=True)

    def __str__(self):
        return f"Apt {self.apartment_number}, Building {self.building_no}"


class HouseholdMember(models.Model):
    ROLE_CHOICES = (
        ('head', 'Head of Household'),
        ('spouse', 'Spouse'),
        ('child', 'Child'),
        ('relative', 'Relative'),
        ('house keeper', 'House Keeper'),
        ('other', 'Other'),
    )
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="members")
    name = models.CharField(max_length=100)
    age = models.PositiveIntegerField()
    sex = models.CharField(max_length=10, choices=(
        ('male', 'Male'), ('female', 'Female'), ('other', 'Other')))
    role = models.CharField(max_length=20, choices=ROLE_CHOICES)
    occupation = models.CharField(max_length=100, blank=True, null=True)
    contact_number = models.CharField(max_length=15, blank=True, null=True)

    def __str__(self):
        return f"{self.name} ({self.role}) - Apt {self.household.apartment_number}, Building {self.household.building_no}"


# Invoice Model


class FinancialSummary(models.Model):
    total_balance = models.DecimalField(
        max_digits=15, decimal_places=2, default=0.00)
    Association = models.ForeignKey(
        Association,  on_delete=models.CASCADE)

    def add_income(self, amount):
        """Add income to the total balance."""
        if not isinstance(amount, Decimal):
            amount = Decimal(amount)
        if amount > 0:
            self.total_balance += amount
            self.save()

    def deduct_expense(self, amount):
        if not isinstance(amount, Decimal):
            amount = Decimal(amount)
        # Deduct expense from the total balance.
        if amount > 0 and amount <= self.total_balance:

            self.total_balance -= amount
            self.save()
        elif amount > self.total_balance:
            raise ValueError("Insufficient balance for this expense")

    def __str__(self):
        return f"Total Balance: {self.total_balance}"


class Invoice(models.Model):
    household = models.ForeignKey(
        Household, on_delete=models.CASCADE, related_name="invoices"
    )
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    description = models.TextField()
    due_date = models.DateField()
    is_paid = models.BooleanField(default=False)
    issued_date = models.DateField(default=now)
    penalty = models.DecimalField(max_digits=10, decimal_places=2, default=0)

    def calculate_penalty(self):
        """Calculate the penalty based on overdue duration."""
        if not self.is_paid and date.today() > self.due_date:
            overdue_days = (date.today() - self.due_date).days
            base_penalty = 0

            if overdue_days <= 10:
                base_penalty = self.amount * 0.02 * overdue_days
            elif 10 < overdue_days <= 30:
                base_penalty = (
                    self.amount * 0.02 * 10 +  # 2% for the first 10 days
                    # 4% for the remaining days
                    self.amount * 0.04 * (overdue_days - 10)
                )
            else:
                base_penalty = (
                    self.amount * 0.02 * 10 +  # 2% for the first 10 days
                    self.amount * 0.04 * 20 +  # 4% for the next 20 days
                    # 5% for days above 30
                    self.amount * 0.05 * (overdue_days - 30)
                )

            self.penalty = round(base_penalty, 2)
        else:
            self.penalty = 0
        return self.penalty

    def save(self, *args, **kwargs):
        """Override save to calculate penalty before saving."""
        self.calculate_penalty()
        super().save(*args, **kwargs)

        # Update financial summary when invoice is paid
        if self.is_paid:
            # Assume a single record for simplicity
            financial_summary = FinancialSummary.objects.filter(
                Association=self.household.Association).first()
            if financial_summary:
                financial_summary.add_income(self.amount + self.penalty)

    def __str__(self):
        return f"Invoice {self.id} for {self.household}"


class FinancialTransaction(models.Model):
    TRANSACTION_TYPES = (
        ('income', 'Income'),
        ('expense', 'Expense'),
    )
    type = models.CharField(max_length=10, choices=TRANSACTION_TYPES)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    reason = models.TextField()
    date = models.DateField(default=now)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="transactions")
    accessed_by = models.CharField(max_length=50, null=True)

    def save(self, *args, **kwargs):
        """Override save to adjust financial summary when transaction is saved."""
        super().save(*args, **kwargs)

        # Update financial summary based on transaction type
        # Assume a single record for simplicity
        financial_summary = FinancialSummary.objects.filter(
            Association=self.association).first()
        if financial_summary:
            if self.type == 'income':
                pass
            elif self.type == 'expense':
                financial_summary.deduct_expense(self.amount)

    def __str__(self):
        return f"{self.type.capitalize()} - {self.amount}"


# Event Model
class Event(models.Model):
    name = models.CharField(max_length=200)
    date = models.DateField()
    start_time = models.TimeField(null=True)
    end_time = models.TimeField(null=True)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="events"
    )
    attendees = models.ManyToManyField(Household, through="EventAttendance")
    penalty_price = models.PositiveIntegerField(
        default=0)  # Total penalty price for this event

    def __str__(self):
        return self.name

    def create_attendance_records(self):
        """Create EventAttendance records for all households in the associated association."""
        households = Household.objects.filter(Association=self.association)
        for household in households:
            EventAttendance.objects.create(
                household=household,
                event=self,
                attended=False,
                late_minutes=0,
                entry_time=None,
                exit_time=None,
                penalty_amount=0  # Initial penalty amount is set to 0
            )

    def calculate_penalty_and_generate_invoices(self):
        """Calculate and set penalties for all attendees and create invoices for applicable penalties."""
        for attendance in EventAttendance.objects.filter(event=self):
            penalty = attendance.calculate_penalty(
                self.start_time, self.end_time)
            if penalty > 0:
                # Save the penalty amount on the EventAttendance record
                attendance.penalty_amount = penalty
                attendance.save()

                # Create an invoice for penalties only if greater than 0
                Invoice.objects.create(
                    household=attendance.household,
                    amount=penalty,
                    description=f"Penalty for event {self.name}",
                    # Assume payment due 7 days after the event
                    due_date=self.date + timedelta(days=7),
                    issued_date=now()
                )

        # Round the total penalty to the nearest 25 (only if needed)
        self.penalty_price = round(self.penalty_price / 25) * 25
        self.save()


class EventAttendance(models.Model):
    household = models.ForeignKey(Household, on_delete=models.CASCADE)
    event = models.ForeignKey(Event, on_delete=models.CASCADE)
    attended = models.BooleanField(default=False)
    late_minutes = models.PositiveIntegerField(default=0)
    entry_time = models.DateTimeField(null=True, blank=True)
    exit_time = models.DateTimeField(null=True, blank=True)
    penalty_amount = models.DecimalField(
        max_digits=10, decimal_places=2, default=0.0)

    def calculate_penalty(self, event_start_time, event_end_time):
        """Calculate the penalty based on attendance and lateness."""
        penalty = 0
        event_duration = (datetime.combine(date.today(), event_end_time) - datetime.combine(
            date.today(), event_start_time)).total_seconds() / 60  # Minutes

        if not self.attended:
            penalty = self.event.penalty_price  # Full penalty for absence
        else:
            if self.entry_time and self.entry_time > datetime.combine(date.today(), event_start_time):
                late_minutes = (
                    self.entry_time - datetime.combine(date.today(), event_start_time)).total_seconds() / 60
                # Calculate late penalty as a percentage of total event time
                penalty = round((late_minutes / event_duration)
                                * self.event.penalty_price, 2)
            elif self.exit_time and self.exit_time < datetime.combine(date.today(), event_end_time):
                early_exit_minutes = (datetime.combine(
                    date.today(), event_end_time) - self.exit_time).total_seconds() / 60
                penalty += round((early_exit_minutes / event_duration)
                                 * self.event.penalty_price, 2)

        # Ensure the penalty is rounded to the nearest 25
        penalty = round(penalty / 25) * 25
        return penalty

    def __str__(self):
        return f"{self.household} - {self.event}"


# Project Model
class Project(models.Model):
    name = models.CharField(max_length=200)
    description = models.TextField()
    start_date = models.DateField()
    end_date = models.DateField(blank=True, null=True)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="projects")

    def __str__(self):
        return self.name


class ProjectProgress(models.Model):
    project = models.ForeignKey(
        Project, on_delete=models.CASCADE, related_name="progress_updates")
    description = models.TextField()
    timestamp = models.DateTimeField(default=now)
    # Optionally capture who added the progress update
    updated_by = models.CharField(max_length=100, blank=True, null=True)

    def __str__(self):
        return f"Progress for {self.project.name} at {self.timestamp}"

    class Meta:
        ordering = ['-timestamp']
