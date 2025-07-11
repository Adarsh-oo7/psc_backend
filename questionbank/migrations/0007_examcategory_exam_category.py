# Generated by Django 5.1.6 on 2025-06-17 12:09

import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questionbank", "0006_useranswer_delete_userprogress"),
    ]

    operations = [
        migrations.CreateModel(
            name="ExamCategory",
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
                ("name", models.CharField(max_length=100, unique=True)),
                ("description", models.TextField(blank=True)),
                (
                    "order",
                    models.PositiveIntegerField(
                        default=0,
                        help_text="Set display order, lower numbers show first.",
                    ),
                ),
            ],
            options={
                "verbose_name_plural": "Exam Categories",
                "ordering": ["order"],
            },
        ),
        migrations.AddField(
            model_name="exam",
            name="category",
            field=models.ForeignKey(
                blank=True,
                null=True,
                on_delete=django.db.models.deletion.SET_NULL,
                related_name="exams",
                to="questionbank.examcategory",
            ),
        ),
    ]
