# Generated by Django 5.1.6 on 2025-06-14 08:03

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("questionbank", "0004_question_institute_topic_institute_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="userprofile",
            name="place",
            field=models.CharField(blank=True, max_length=100),
        ),
    ]
