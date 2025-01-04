from django.dispatch import receiver
from django.db.models.signals import post_save
import uuid
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
    building_numbers = models.CharField(max_length=100)

    def __str__(self):
        return f"{self.place} - {self.building_numbers}"


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
    return f"media/documents/{custom_name}"


class Household(models.Model):
    Association = models.ForeignKey(Association,  on_delete=models.CASCADE)
    apartment_number = models.CharField(max_length=10)
    building_no = models.CharField(max_length=100)
    head_of_household = models.CharField(max_length=100)
    contact_number = models.CharField(max_length=15)
    email = models.EmailField(blank=True, null=True)
    is_rented = models.BooleanField(default=False)
    is_empty_daytime = models.BooleanField(default=False)
    documents = models.FileField(
        upload_to=household_document_path, blank=True, null=True)

    def __str__(self):
        return f"Apt {self.apartment_number}, Building {self.building_no} {self.head_of_household}"


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
    current_member = models.BooleanField(default=True)

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
        print("expence deducted")
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


@receiver(post_save, sender=Association)
def create_financial_summary(sender, instance, created, **kwargs):
    if created:
        FinancialSummary.objects.create(Association=instance)


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
    created_by = models.CharField(max_length=100, default="")
    payment_accepted_by = models.CharField(max_length=100, default="")
    payment_date = models.DateField(null=True)
    group = models.CharField(max_length=100, default=uuid.uuid4)

    def calculate_penalty(self):
        """Calculate the penalty based on overdue duration."""
        if not self.is_paid and date.today() > self.due_date:
            overdue_days = (date.today() - self.due_date).days
            base_penalty = 0

            if overdue_days <= 10:
                base_penalty = self.amount * Decimal(0.02 * overdue_days)
            elif 10 < overdue_days <= 30:
                base_penalty = (
                    # 2% for the first 10 days
                    self.amount * Decimal(0.02 * 10) +
                    # 4% for the remaining days
                    self.amount * Decimal(0.04 * (overdue_days - 10))
                )
            else:
                base_penalty = (
                    # 2% for the first 10 days
                    self.amount * Decimal(0.02 * 10) +
                    # 4% for the next 20 days
                    self.amount * Decimal(0.04 * 20) +
                    # 5% for days above 30
                    self.amount * Decimal(0.05 * (overdue_days - 30))
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
    date = models.DateTimeField(auto_now_add=True)
    association = models.ForeignKey(
        Association, on_delete=models.CASCADE, related_name="transactions")
    accessed_by = models.CharField(max_length=50, null=True)

    def save(self, created_i=True, *args, **kwargs):
        """Override save to adjust financial summary when transaction is saved."""
        super().save(*args, **kwargs)

        # Update financial summary based on transaction type
        # Assume a single record for simplicity
        financial_summary = FinancialSummary.objects.filter(
            Association=self.association).first()
        print(financial_summary, self.association)
        if financial_summary and created_i:
            if self.type == 'income':
                financial_summary.add_income(self.amount)
            elif self.type == 'expense':
                financial_summary.deduct_expense(self.amount)

    def delete(self, *args, **kwargs):
        """Override delete to adjust financial summary when transaction is deleted."""
        financial_summary = FinancialSummary.objects.filter(
            Association=self.association).first()

        if financial_summary:
            if self.type == 'income':
                financial_summary.deduct_income(self.amount)
            elif self.type == 'expense':
                financial_summary.add_expense(self.amount)

        # Call the parent delete method
        super().delete(*args, **kwargs)

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
    created_by = models.CharField(max_length=50, default="")
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

    def calculate_penalty_and_generate_invoices(self, created_by=""):
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
                    created_by=created_by,
                    description=f"Penalty for event {self.name}",
                    # Assume payment due 7 days after the event
                    due_date=self.date + timedelta(days=14),
                    issued_date=now()
                )

    def delete(self, *args, **kwargs):
        """Override delete to delete associated attendance records."""
        eventattendance = EventAttendance.objects.filter(event=self)
        for attendance in eventattendance:
            attendance.delete()
        super().delete(*args, **kwargs)

        # Round the total penalty to the nearest 25 (only if needed)


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

        late_minutes = 0
        early_exit_minutes = 0

        if not self.attended:
            penalty = self.event.penalty_price  # Full penalty for absence
        elif (not self.entry_time and self.exit_time) or (not self.exit_time and self.entry_time):
            penalty = self.event.penalty_price / 2  # Half penalty for partial attendance

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
        self.late_minutes = late_minutes + early_exit_minutes
        self.save()
        return penalty

    def __str__(self):
        return f"{self.id} {self.household} - {self.event}"


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
