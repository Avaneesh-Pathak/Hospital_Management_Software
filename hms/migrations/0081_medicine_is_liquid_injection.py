# Generated by Django 5.1.6 on 2025-04-10 15:16

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hms", "0080_nicumedicationrecord_dose_per_day_mg"),
    ]

    operations = [
        migrations.AddField(
            model_name="medicine",
            name="is_liquid_injection",
            field=models.BooleanField(
                default=False,
                help_text="Only for injections: Check if this is a ready-to-use liquid injection",
            ),
        ),
    ]
