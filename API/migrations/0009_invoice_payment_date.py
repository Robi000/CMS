# Generated by Django 5.1.4 on 2024-12-16 13:23

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('API', '0008_invoice_created_by_invoice_payment_accepted_by'),
    ]

    operations = [
        migrations.AddField(
            model_name='invoice',
            name='payment_date',
            field=models.DateField(null=True),
        ),
    ]
