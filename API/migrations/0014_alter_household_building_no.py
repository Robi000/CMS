from django.db import migrations


def convert_building_no(apps, schema_editor):
    Household = apps.get_model('API', 'Household')
    for household in Household.objects.all():
        household.building_no = str(household.building_no)  # Convert to string
        household.save()


class Migration(migrations.Migration):
    dependencies = [
        # Replace with your actual previous migration
        ('API', '0013_event_created_by'),
    ]

    operations = [
        migrations.RunPython(convert_building_no),
    ]
