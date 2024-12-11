from django.contrib import admin
from django.utils.html import format_html
from .models import (
    Association,
    CustomUser,
    Household,
    HouseholdMember,
    Invoice,
    Event,
    EventAttendance,
    Project,
    ProjectProgress,
    FinancialTransaction,  FinancialSummary
)
from datetime import date


@admin.register(FinancialTransaction)
class FinancialTransactionAdmin(admin.ModelAdmin):
    list_display = ('type', 'amount', 'reason', 'date',
                    'association', 'accessed_by')
    list_filter = ('type', 'date', 'association')
    search_fields = ('reason', 'accessed_by')
    ordering = ('-date',)
    date_hierarchy = 'date'
    fieldsets = (
        (None, {
            'fields': ('type', 'amount', 'reason', 'date', 'association', 'accessed_by')
        }),
    )


@admin.register(FinancialSummary)
class FinancialSummaryAdmin(admin.ModelAdmin):
    list_display = ('id', 'total_balance')
    # Make the balance field read-only to prevent accidental edits
    readonly_fields = ('id', 'total_balance')
    search_fields = ('id',)
    ordering = ('-total_balance',)
    fieldsets = (
        (None, {
            'fields': ('id', 'total_balance')
        }),
    )


@admin.register(Association)
class AssociationAdmin(admin.ModelAdmin):
    list_display = ('place', 'building_number_start', 'building_number_end')
    search_fields = ('place',)
    list_filter = ('building_number_start', 'building_number_end')
    ordering = ('place',)


@admin.register(CustomUser)
class CustomUserAdmin(admin.ModelAdmin):
    list_display = ('username', 'email', 'role', 'association')
    list_filter = ('role', 'association')
    search_fields = ('username', 'email')
    ordering = ('username',)


class HouseholdMemberInline(admin.TabularInline):
    model = HouseholdMember
    extra = 1


@admin.register(Household)
class HouseholdAdmin(admin.ModelAdmin):
    list_display = (
        'apartment_number',
        'building_no',
        'head_of_household',
        'contact_number',
        'email',
        'is_rented',
        'is_empty_daytime',
    )
    list_filter = ('is_rented', 'is_empty_daytime', 'building_no')
    search_fields = ('apartment_number', 'building_no', 'head_of_household')
    inlines = [HouseholdMemberInline]


@admin.register(HouseholdMember)
class HouseholdMemberAdmin(admin.ModelAdmin):
    list_display = ('name', 'role', 'household', 'age', 'sex', 'occupation')
    list_filter = ('role', 'sex', 'household__building_no')
    search_fields = ('name', 'household__apartment_number',
                     'household__head_of_household')
    ordering = ('name',)


@admin.register(Invoice)
class InvoiceAdmin(admin.ModelAdmin):
    list_display = (
        'household',
        'amount',
        'due_date',
        'is_paid',
        'penalty',
        'issued_date',
        'overdue_status',
    )
    list_filter = ('is_paid', 'due_date', 'issued_date')
    search_fields = ('household__apartment_number', 'description')
    ordering = ('due_date',)
    actions = ['mark_as_paid']

    def overdue_status(self, obj):
        if obj.is_paid:
            return "Paid"
        elif obj.due_date < date.today():
            return f"Overdue by {(date.today() - obj.due_date).days} days"
        return "Due"

    overdue_status.short_description = "Overdue Status"

    def mark_as_paid(self, request, queryset):
        queryset.update(is_paid=True)
        self.message_user(
            request, "Selected invoices have been marked as paid.")
    mark_as_paid.short_description = "Mark selected invoices as Paid"


class EventAttendanceInline(admin.TabularInline):
    model = EventAttendance
    extra = 0


@admin.register(Event)
class EventAdmin(admin.ModelAdmin):
    list_display = ('name', 'date', 'start_time', 'end_time',
                    'association', 'penalty_price')
    list_filter = ('date', 'association')
    search_fields = ('name', 'association__place')
    inlines = [EventAttendanceInline]
    actions = ['generate_attendance_records', 'calculate_event_penalties']

    def generate_attendance_records(self, request, queryset):
        for event in queryset:
            event.create_attendance_records()
        self.message_user(
            request, "Attendance records generated for selected events.")
    generate_attendance_records.short_description = "Generate Attendance Records"

    def calculate_event_penalties(self, request, queryset):
        for event in queryset:
            event.calculate_penalty_and_generate_invoices()
        self.message_user(
            request, "Penalties calculated and invoices generated for selected events.")
    calculate_event_penalties.short_description = "Calculate Penalties and Generate Invoices"


@admin.register(EventAttendance)
class EventAttendanceAdmin(admin.ModelAdmin):
    list_display = (
        'household',
        'event',
        'attended',
        'late_minutes',
        'penalty_amount',
    )
    list_filter = ('attended', 'event__date', 'event__association')
    search_fields = ('household__apartment_number', 'event__name')


class ProjectProgressInline(admin.TabularInline):
    model = ProjectProgress
    extra = 1


@admin.register(Project)
class ProjectAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'association')
    list_filter = ('start_date', 'end_date', 'association')
    search_fields = ('name', 'description', 'association__place')
    inlines = [ProjectProgressInline]


@admin.register(ProjectProgress)
class ProjectProgressAdmin(admin.ModelAdmin):
    list_display = ('project', 'description', 'timestamp', 'updated_by')
    list_filter = ('project', 'timestamp')
    search_fields = ('project__name', 'description', 'updated_by')
    ordering = ('-timestamp',)
