from django.core.management.base import BaseCommand
from datetime import datetime, timedelta
from django.utils.timezone import now
from API.models import Association, CustomUser, Household, HouseholdMember, Invoice, Event, EventAttendance, Project, ProjectProgress, FinancialTransaction
import random


class Command(BaseCommand):
    help = 'Populates the database with dummy data for all models.'

    def handle(self, *args, **kwargs):
        # Create dummy associations
        associations = []
        for i in range(1, 6):
            association = Association.objects.create(
                place=f"Association {i}",
                building_number_start=random.randint(1, 100),
                building_number_end=random.randint(101, 200)
            )
            associations.append(association)

        # Create dummy users
        user1 = CustomUser.objects.create_user(
            username='admin_user',
            password='password123',
            role='admin',
            association=associations[0]
        )

        user2 = CustomUser.objects.create_user(
            username='committee_user',
            password='password123',
            role='committee',
            association=associations[1]
        )

        # Create dummy households
        households = []
        for i in range(1, 11):
            household = Household.objects.create(
                association=associations[i % len(associations)],
                apartment_number=f"A{i:02d}",
                building_no=i,
                head_of_household=f"Head {i}",
                contact_number=f"123-456-789{i}",
                email=f"household{i}@example.com",
                is_rented=random.choice([True, False]),
                is_empty_daytime=random.choice([True, False])
            )
            households.append(household)

        # Create dummy household members
        roles = ['head', 'spouse', 'child',
                 'relative', 'house keeper', 'other']
        for i, household in enumerate(households):
            HouseholdMember.objects.create(
                household=household,
                name=f"Member {i}",
                age=random.randint(1, 80),
                sex=random.choice(['male', 'female', 'other']),
                role=random.choice(roles),
                occupation=f"Occupation {i}",
                contact_number=f"123-456-789{i}"
            )

        # Create dummy invoices
        for household in households:
            Invoice.objects.create(
                household=household,
                amount=random.uniform(100, 1000),
                description=f"Invoice for {household}",
                due_date=now().date() + timedelta(days=30),
                is_paid=random.choice([True, False]),
                penalty=0  # Default value
            )

        # Create dummy events
        events = []
        for i in range(1, 4):
            event = Event.objects.create(
                name=f"Event {i}",
                date=now().date() + timedelta(days=i * 10),
                start_time=datetime.now().time(),
                end_time=datetime.now().time(),
                association=associations[i % len(associations)],
                penalty_price=random.randint(100, 500)
            )
            events.append(event)
            event.create_attendance_records()

        # Create dummy project and progress
        for i in range(1, 3):
            project = Project.objects.create(
                name=f"Project {i}",
                description=f"Description for project {i}",
                start_date=now().date(),
                end_date=now().date() + timedelta(days=100),
                association=associations[i % len(associations)]
            )
            ProjectProgress.objects.create(
                project=project,
                description=f"Progress update for project {i}",
                timestamp=now(),
                updated_by=f"User {i}"
            )

        # Create dummy financial transactions
        for association in associations:
            FinancialTransaction.objects.create(
                type=random.choice(['income', 'expense']),
                amount=random.uniform(500, 5000),
                reason=f"Transaction for {association.place}",
                date=now().date(),
                association=association
            )

        self.stdout.write(self.style.SUCCESS(
            'Successfully populated the database with dummy data.'))
