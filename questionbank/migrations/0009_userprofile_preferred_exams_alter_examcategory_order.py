# Generated by Django 5.1.6 on 2025-06-28 19:39

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questionbank", "0008_exam_duration_minutes_topic_image_examsyllabus"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="preferred_exams",
            field=models.ManyToManyField(
                blank=True, related_name="followers", to="questionbank.exam"
            ),
        ),
        migrations.AlterField(
            model_name="examcategory",
            name="order",
            field=models.PositiveIntegerField(default=0),
        ),
    ]
