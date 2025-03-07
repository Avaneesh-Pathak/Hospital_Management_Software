# Generated by Django 5.1.2 on 2025-03-02 07:32

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        (
            "hms",
            "0024_rename_guarantor_address_patient_accompanying_person_address_and_more",
        ),
    ]

    operations = [
        migrations.CreateModel(
            name="NICUVitals",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                ("date", models.DateField(auto_now_add=True)),
                ("temperature", models.DecimalField(decimal_places=1, max_digits=4)),
                ("respiratory_rate", models.IntegerField()),
                ("pulse_rate", models.IntegerField()),
                ("cft", models.DecimalField(decimal_places=1, max_digits=3)),
                (
                    "skin_color",
                    models.CharField(
                        choices=[("pink", "Pink"), ("pallor", "Pallor")], max_length=10
                    ),
                ),
                ("seizure", models.BooleanField()),
                ("spo2", models.IntegerField()),
                (
                    "oxygen",
                    models.IntegerField(
                        help_text="Options: 1. Nasal Prong, 2. Hood, 3. Without O2"
                    ),
                ),
                ("retraction", models.BooleanField()),
                ("iv_fluids", models.IntegerField()),
                ("by_nasogastric", models.IntegerField()),
                ("oral", models.IntegerField()),
                ("breastfeeding", models.BooleanField()),
                (
                    "urine",
                    models.CharField(
                        choices=[("nil", "Nil"), ("ml", "ML")], max_length=10
                    ),
                ),
                ("stool", models.BooleanField()),
                ("ift", models.IntegerField(blank=True, null=True)),
                ("vomiting", models.BooleanField()),
                (
                    "ipd",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="nicu_vitals",
                        to="hms.ipd",
                    ),
                ),
            ],
        ),
    ]
