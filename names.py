import random
from datetime import datetime, timedelta, date
from django.utils.timezone import now
from API.models import Association, CustomUser, Household, HouseholdMember, FinancialSummary, Invoice, FinancialTransaction, Event, EventAttendance, Project, ProjectProgress


def main():

    # Create 5 Associations with Financial Summary
    associations = Association.objects.all()

    households = list(Household.objects.all())
    households = random.sample(households, 20)

    # Create random invoices for each household (20-50 invoices)
    for household in households:
        num_invoices = random.randint(1, 3)
        for _ in range(num_invoices):
            invoice = Invoice.objects.create(
                household=household,
                amount=random.uniform(50.0, 500.0),
                description=f"Invoice for household {
                    household.apartment_number}, building {household.building_no}",
                due_date=date.today() + timedelta(days=random.randint(1, 90)),
                is_paid=random.choice([True, False]),
                penalty=random.uniform(5.0, 50.0)
            )

    # Create financial transactions (2-5 expenses for each association)
    for association in associations:
        num_transactions = random.randint(2, 5)
        for _ in range(num_transactions):
            FinancialTransaction.objects.create(
                type='expense',
                amount=random.uniform(10.0, 200.0),
                reason=f"Expense for association {association.place}",
                date=date.today(),
                association=association,
                accessed_by="admin"
            )

    # Create 2-3 events for each association

    for association in associations:
        num_events = random.randint(2, 3)
        for _ in range(num_events):
            event = Event.objects.create(
                name=f"Event {random.randint(1, 100)}",
                date=date.today() + timedelta(days=random.randint(1, 30)),
                start_time=datetime.now().time(),
                end_time=(datetime.now() +
                          timedelta(hours=random.randint(1, 5))).time(),
                association=association,
                penalty_price=random.randint(50, 500)
            )
            event.create_attendance_records()

    # Create 3-5 projects
    projects = []
    for _ in range(random.randint(3, 5)):
        project = Project.objects.create(
            name=f"Project {random.randint(1, 100)}",
            description="Project description",
            start_date=date.today(),
            end_date=date.today() + timedelta(days=random.randint(30, 365)),
            association=random.choice(associations)
        )
        projects.append(project)

    # Create progress updates for projects (each project can have multiple progress updates)
    for project in projects:
        num_updates = random.randint(1, 5)
        for _ in range(num_updates):
            ProjectProgress.objects.create(
                project=project,
                description="Progress update",
                timestamp=now(),
                updated_by="admin"
            )

    print("Database populated with dummy data successfully!")
