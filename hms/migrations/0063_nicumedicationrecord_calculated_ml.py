# Generated by Django 5.1.6 on 2025-03-31 07:22

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hms", "0062_nicumedicationrecord_frequency_of_dose_given"),
    ]

    operations = [
        migrations.AddField(
            model_name="nicumedicationrecord",
            name="calculated_ml",
            field=models.IntegerField(editable=False, null=True),
        ),
    ]
