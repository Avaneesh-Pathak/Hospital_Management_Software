# Generated by Django 5.1.2 on 2025-03-02 09:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("hms", "0027_alter_nicuvitals_temperature"),
    ]

    operations = [
        migrations.AlterField(
            model_name="nicuvitals",
            name="breastfeeding",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="by_nasogastric",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="cft",
            field=models.DecimalField(
                blank=True, decimal_places=1, max_digits=3, null=True
            ),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="iv_fluids",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="oral",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="pulse_rate",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="respiratory_rate",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="retraction",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="seizure",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="spo2",
            field=models.IntegerField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="stool",
            field=models.BooleanField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name="nicuvitals",
            name="vomiting",
            field=models.BooleanField(blank=True, null=True),
        ),
    ]
