# Generated by Django 5.1.6 on 2025-03-13 15:34

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hms", "0046_nicumedicationrecord_dose_frequency_and_more"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="ipd",
            name="transferred_to_hospital",
        ),
        migrations.RemoveField(
            model_name="nicumedicationrecord",
            name="calculated_dose",
        ),
        migrations.RemoveField(
            model_name="nicumedicationrecord",
            name="dilution_volume",
        ),
        migrations.RemoveField(
            model_name="nicumedicationrecord",
            name="other_frequency",
        ),
        migrations.AddField(
            model_name="medicine",
            name="concentration",
            field=models.FloatField(
                blank=True,
                help_text="Concentration (mg/mL for liquids, mg per tablet for solids)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="medicine",
            name="dose_unit",
            field=models.CharField(
                default="mg",
                help_text="Unit for dosage (mg, mL, drops, IU, etc.)",
                max_length=20,
            ),
        ),
        migrations.AddField(
            model_name="medicine",
            name="strength",
            field=models.CharField(
                blank=True,
                help_text="Strength of medicine (e.g., 500 mg, 125 mg/5mL)",
                max_length=50,
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="nicumedicationrecord",
            name="calculated_dose_per_day",
            field=models.FloatField(
                editable=False, help_text="Calculated total daily dose (mg)", null=True
            ),
        ),
        migrations.AddField(
            model_name="nicumedicationrecord",
            name="calculated_dose_per_dose",
            field=models.FloatField(
                editable=False,
                help_text="Calculated dose per administration (mg)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="nicumedicationrecord",
            name="calculated_volume_per_day",
            field=models.FloatField(
                editable=False,
                help_text="Total volume to be given per day (mL)",
                null=True,
            ),
        ),
        migrations.AddField(
            model_name="nicumedicationrecord",
            name="calculated_volume_per_dose",
            field=models.FloatField(
                editable=False, help_text="Volume per administration (mL)", null=True
            ),
        ),
        migrations.AlterField(
            model_name="diluent",
            name="standard_volume_per_kg",
            field=models.FloatField(
                blank=True,
                help_text="Standard diluent volume per kg (mL/kg)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="nicumedicationrecord",
            name="calculated_diluent_volume",
            field=models.FloatField(
                blank=True,
                editable=False,
                help_text="Calculated diluent volume (mL)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="nicumedicationrecord",
            name="calculated_infusion_rate",
            field=models.FloatField(
                blank=True,
                editable=False,
                help_text="Calculated infusion rate (mL/hr)",
                null=True,
            ),
        ),
        migrations.AlterField(
            model_name="nicumedicationrecord",
            name="dose_frequency",
            field=models.CharField(
                choices=[
                    ("OD", "Once a day (OD)"),
                    ("BD", "Twice a day (BD)"),
                    ("TDS", "Three times a day (TDS)"),
                    ("QID", "Four times a day (QID)"),
                    ("SOS", "As needed (SOS)"),
                    ("STAT", "Immediately (STAT)"),
                    ("OTHER", "Other"),
                ],
                default="OD",
                max_length=10,
            ),
        ),
        migrations.AlterField(
            model_name="nicumedicationrecord",
            name="duration",
            field=models.FloatField(
                blank=True, help_text="Duration of administration (hours)", null=True
            ),
        ),
    ]
