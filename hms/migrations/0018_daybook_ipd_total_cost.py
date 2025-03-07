# Generated by Django 5.1.2 on 2025-02-27 08:21

import django.utils.timezone
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hms", "0017_accountingrecord"),
    ]

    operations = [
        migrations.CreateModel(
            name="Daybook",
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
                ("date", models.DateField(default=django.utils.timezone.now)),
                ("description", models.CharField(max_length=255)),
                ("amount", models.DecimalField(decimal_places=2, max_digits=10)),
                (
                    "transaction_type",
                    models.CharField(
                        choices=[
                            ("income", "Income"),
                            ("expense", "Expense"),
                            ("deduction", "Deduction"),
                        ],
                        max_length=10,
                    ),
                ),
                (
                    "balance",
                    models.DecimalField(decimal_places=2, default=0, max_digits=10),
                ),
            ],
        ),
        migrations.AddField(
            model_name="ipd",
            name="total_cost",
            field=models.DecimalField(
                decimal_places=2, default=0.0, editable=False, max_digits=10
            ),
        ),
    ]
